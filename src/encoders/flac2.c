#include "flac2.h"
#include "../common/md5.h"
#include "../common/flac_crc.h"
#include "../pcm.h"
#include <string.h>
#include <inttypes.h>
#include <math.h>
#include <float.h>

typedef enum {CONSTANT, VERBATIM, FIXED, LPC} subframe_type_t;

/*maximum 5 bit value + 1*/
#define MAX_QLP_COEFFS 32

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

/*******************************
 * private function signatures *
 *******************************/

static void
write_block_header(BitstreamWriter *output,
                   unsigned is_last,
                   unsigned block_type,
                   unsigned block_length);

/*writes the STREAMINFO block, not including the block header*/
static void
write_STREAMINFO(BitstreamWriter *output,
                 unsigned minimum_block_size,
                 unsigned maximum_block_size,
                 unsigned minimum_frame_size,
                 unsigned maximum_frame_size,
                 unsigned sample_rate,
                 unsigned channel_count,
                 unsigned bits_per_sample,
                 uint64_t total_samples,
                 uint8_t *md5sum);

static void
write_PADDING(BitstreamWriter *output,
              unsigned padding_size);

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int *pcm_data,
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames);

static void
encode_frame(const struct PCMReader *pcmreader,
             BitstreamWriter *output,
             const struct flac_encoding_options *options,
             const int *pcm_data,
             unsigned pcm_frames,
             unsigned frame_number);

static void
correlate_channels(unsigned pcm_frames,
                   const int left_channel[],
                   const int right_channel[],
                   int average_channel[],
                   int difference_channel[]);

static void
write_frame_header(BitstreamWriter *output,
                   unsigned sample_count,
                   unsigned sample_rate,
                   unsigned channels,
                   unsigned bits_per_sample,
                   unsigned frame_number,
                   unsigned channel_assignment);

static unsigned
encode_block_size(unsigned block_size);

static unsigned
encode_sample_rate(unsigned sample_rate);

static unsigned
encode_bits_per_sample(unsigned bits_per_sample);

static void
write_utf8(BitstreamWriter *output, unsigned value);

static void
encode_subframe(BitstreamWriter *output,
                const struct flac_encoding_options *options,
                unsigned sample_count,
                int samples[],
                unsigned bits_per_sample);

static void
write_subframe_header(BitstreamWriter *output,
                      subframe_type_t subframe_type,
                      unsigned predictor_order,
                      unsigned wasted_bps);

static void
encode_constant_subframe(BitstreamWriter *output,
                         unsigned sample_count,
                         int sample,
                         unsigned bits_per_sample,
                         unsigned wasted_bps);

static void
encode_verbatim_subframe(BitstreamWriter *output,
                         unsigned sample_count,
                         const int samples[],
                         unsigned bits_per_sample,
                         unsigned wasted_bps);

static void
encode_fixed_subframe(BitstreamWriter *output,
                      const struct flac_encoding_options *options,
                      unsigned sample_count,
                      const int samples[],
                      unsigned bits_per_sample,
                      unsigned wasted_bps);

static void
next_fixed_order(unsigned sample_count,
                 const int previous_order[],
                 int next_order[]);

static uint64_t
abs_sum(unsigned count, const int values[]);

/*calculates best LPC subframe and writes LPC subframe to disk*/
static void
encode_lpc_subframe(BitstreamWriter *output,
                    const struct flac_encoding_options *options,
                    unsigned sample_count,
                    const int samples[],
                    unsigned bits_per_sample,
                    unsigned wasted_bps);

/*writes actual LPC subframe to disk,
  not including the subframe header*/
static void
write_lpc_subframe(BitstreamWriter *output,
                   const struct flac_encoding_options *options,
                   unsigned sample_count,
                   const int samples[],
                   unsigned bits_per_sample,
                   unsigned predictor_order,
                   unsigned precision,
                   int shift,
                   const int coefficients[]);

static void
calculate_best_lpc_params(const struct flac_encoding_options *options,
                          unsigned sample_count,
                          const int samples[],
                          unsigned bits_per_sample,
                          unsigned *predictor_order,
                          unsigned *precision,
                          int *shift,
                          int coefficients[]);

static void
window_signal(unsigned sample_count,
              const int samples[],
              const double window[],
              double windowed_signal[]);

static void
compute_autocorrelation_values(unsigned sample_count,
                               const double windowed_signal[],
                               unsigned max_lpc_order,
                               double autocorrelated[]);

static void
compute_lp_coefficients(unsigned max_lpc_order,
                        const double autocorrelated[],
                        double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS],
                        double error[]);

static unsigned
estimate_best_lpc_order(unsigned bits_per_sample,
                        unsigned precision,
                        unsigned sample_count,
                        unsigned max_lpc_order,
                        const double error[]);

/*quantizes lp_coeff[lpc_order - 1][0..lpc_order - 1] LP coefficients
  to qlp_coeff[] which must have lpc_order values
  and returns the needed shift*/
static void
quantize_lp_coefficients(unsigned lpc_order,
                         double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS],
                         unsigned precision,
                         int qlp_coeff[],
                         int *shift);

static void
write_residual_block(BitstreamWriter *output,
                     const struct flac_encoding_options *options,
                     unsigned sample_count,
                     unsigned predictor_order,
                     const int residuals[]);

/*given a set of options and residuals,
  determines the best partition order
  and sets 2 ^ partition_order residuals
  to a maximum of 2 ^ max_residual_partition_order*/
static void
best_rice_parameters(const struct flac_encoding_options *options,
                     unsigned sample_count,
                     unsigned predictor_order,
                     const int residuals[],
                     unsigned *partition_order,
                     unsigned rice_parameters[]);

/*returns the highest available partition order
  to a maximum of max_partition_order*/
static unsigned
maximum_partition_order(unsigned sample_count,
                        unsigned predictor_order,
                        unsigned max_partition_order);

static struct flac_frame_size*
push_frame_size(struct flac_frame_size *head,
                unsigned byte_size,
                unsigned pcm_frames_size);

static void
reverse_frame_sizes(struct flac_frame_size **head);

static int
samples_identical(unsigned sample_count, const int *samples);

static unsigned
calculate_wasted_bps(unsigned sample_count, const int *samples);

static inline unsigned
ceil_div(unsigned n, unsigned d)
{
    return (n / d) + (n % d ? 1 : 0);
}

static void
tukey_window(double alpha, unsigned block_size, double *window);

/***********************************
 * public function implementations *
 ***********************************/

void
flacenc_init_options(struct flac_encoding_options *options)
{
    options->block_size = 4096;
    options->min_residual_partition_order = 0;
    options->max_residual_partition_order = 6;
    options->max_lpc_order = 12;
    options->exhaustive_model_search = 0;
    options->mid_side = 0;
    options->adaptive_mid_side = 0;

    options->use_verbatim = 1;
    options->use_constant = 1;
    options->use_fixed = 1;

    /*these are just placeholders*/
    options->qlp_coeff_precision = 12;
    options->max_rice_parameter = 14;
}

void
flacenc_display_options(const struct flac_encoding_options *options,
                        FILE *output)
{

    printf("block size              %u\n",
           options->block_size);
    printf("min partition order     %u\n",
           options->min_residual_partition_order);
    printf("max partition order     %u\n",
           options->max_residual_partition_order);
    printf("max LPC order           %u\n",
           options->max_lpc_order);
    printf("exhaustive model search %d\n",
           options->exhaustive_model_search);
    printf("mid side                %d\n",
           options->mid_side);
    printf("adaptive mid side       %d\n",
           options->adaptive_mid_side);
    printf("use VERBATIM subframes  %d\n",
           options->use_verbatim);
    printf("use CONSTANT subframes  %d\n",
           options->use_constant);
    printf("use FIXED subframes     %d\n",
           options->use_fixed);
}

struct flac_frame_size*
flacenc_encode_flac(struct PCMReader *pcmreader,
                    BitstreamWriter *output,
                    struct flac_encoding_options *options,
                    unsigned padding_size)
{
    const uint8_t signature[] = "fLaC";
    struct flac_frame_size *frame_sizes = NULL;
    bw_pos_t *streaminfo_start;
    unsigned minimum_frame_size = (1 << 24) - 1;
    unsigned maximum_frame_size = 0;
    uint64_t total_samples = 0;
    audiotools__MD5Context md5_context;
    uint8_t md5sum[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    int pcm_data[options->block_size * pcmreader->channels];
    unsigned pcm_frames_read;
    unsigned frame_number = 0;

    audiotools__MD5Init(&md5_context);

    /*set QLP coeff precision based on block size*/
    if (options->block_size <= 192) {
        options->qlp_coeff_precision = 7;
    } else if (options->block_size <= 384) {
        options->qlp_coeff_precision = 8;
    } else if (options->block_size <= 576) {
        options->qlp_coeff_precision = 9;
    } else if (options->block_size <= 1152) {
        options->qlp_coeff_precision = 10;
    } else if (options->block_size <= 2304) {
        options->qlp_coeff_precision = 11;
    } else if (options->block_size <= 4608) {
        options->qlp_coeff_precision = 12;
    } else {
        options->qlp_coeff_precision = 13;
    }

    /*set maximum Rice parameter based on bits-per-sample*/
    if (pcmreader->bits_per_sample <= 16) {
        options->max_rice_parameter = 15;
    } else {
        options->max_rice_parameter = 31;
    }

    /*generate Tukey window, if necessary*/
    if (options->max_lpc_order) {
        options->window = malloc(sizeof(double) * options->block_size);
        tukey_window(0.5, options->block_size, options->window);
    }

    /*write signature*/
    output->write_bytes(output, signature, 4);

    /*write initial STREAMINFO block*/
    write_block_header(output, padding_size ? 0 : 1, 0, 34);
    streaminfo_start = output->getpos(output);
    write_STREAMINFO(output,
                     options->block_size,
                     options->block_size,
                     minimum_frame_size,
                     maximum_frame_size,
                     pcmreader->sample_rate,
                     pcmreader->channels,
                     pcmreader->bits_per_sample,
                     total_samples,
                     md5sum);

    /*write PADDING block, if any*/
    if (padding_size) {
        write_block_header(output, 1, 1, padding_size);
        write_PADDING(output, padding_size);
    }

    /*write frames*/
    while ((pcm_frames_read =
            pcmreader->read(pcmreader, options->block_size, pcm_data)) > 0) {
        unsigned frame_size = 0;

        /*update running MD5 of stream*/
        update_md5sum(&md5_context,
                      pcm_data,
                      pcmreader->channels,
                      pcmreader->bits_per_sample,
                      pcm_frames_read);

        /*encode frame itself*/
        output->add_callback(output, (bs_callback_f)byte_counter, &frame_size);
        encode_frame(pcmreader,
                     output,
                     options,
                     pcm_data,
                     pcm_frames_read,
                     frame_number++);
        output->pop_callback(output, NULL);

        /*save total length of frame*/
        frame_sizes = push_frame_size(frame_sizes,
                                      frame_size,
                                      pcm_frames_read);
        if (frame_size < minimum_frame_size) {
            minimum_frame_size = frame_size;
        }
        if (frame_size > maximum_frame_size) {
            maximum_frame_size = frame_size;
        }
        total_samples += pcm_frames_read;
    }

    /*finalize MD5 sum*/
    audiotools__MD5Final(md5sum, &md5_context);

    /*rewrite initial STREAMINFO block*/
    output->setpos(output, streaminfo_start);
    write_STREAMINFO(output,
                     options->block_size,
                     options->block_size,
                     minimum_frame_size,
                     maximum_frame_size,
                     pcmreader->sample_rate,
                     pcmreader->channels,
                     pcmreader->bits_per_sample,
                     total_samples,
                     md5sum);
    streaminfo_start->del(streaminfo_start);

    /*delete window, if necessary*/
    free(options->window);

    /*return frame lengths for SEEKTABLE generation in proper order*/
    reverse_frame_sizes(&frame_sizes);
    return frame_sizes;
}

/************************************
 * private function implementations *
 ************************************/

static void
write_block_header(BitstreamWriter *output,
                   unsigned is_last,
                   unsigned block_type,
                   unsigned block_length)
{
    output->build(output, "1u 7u 24u", is_last, block_type, block_length);
}

static void
write_STREAMINFO(BitstreamWriter *output,
                 unsigned minimum_block_size,
                 unsigned maximum_block_size,
                 unsigned minimum_frame_size,
                 unsigned maximum_frame_size,
                 unsigned sample_rate,
                 unsigned channel_count,
                 unsigned bits_per_sample,
                 uint64_t total_samples,
                 uint8_t *md5sum)
{
    output->build(output,
                  "16u 16u 24u 24u 20u 3u 5u 36U 16b",
                  minimum_block_size,
                  maximum_block_size,
                  minimum_frame_size,
                  maximum_frame_size,
                  sample_rate,
                  channel_count - 1,
                  bits_per_sample - 1,
                  total_samples,
                  md5sum);
}

static void
write_PADDING(BitstreamWriter *output,
              unsigned padding_size)
{
    for (; padding_size; padding_size--) {
        output->write(output, 8, 0);
    }
}

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int *pcm_data,
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames)
{
    const unsigned bytes_per_sample = bits_per_sample / 8;
    unsigned total_samples = pcm_frames * channels;
    const unsigned buffer_size = total_samples * bytes_per_sample;
    unsigned char buffer[buffer_size];
    unsigned char *output_buffer = buffer;
    void (*converter)(int, unsigned char *) =
        FrameList_get_int_to_char_converter(bits_per_sample, 0, 1);

    for (; total_samples; total_samples--) {
        converter(*pcm_data, output_buffer);
        pcm_data += 1;
        output_buffer += bytes_per_sample;
    }

    audiotools__MD5Update(md5sum, buffer, buffer_size);
}

static void
encode_frame(const struct PCMReader *pcmreader,
             BitstreamWriter *output,
             const struct flac_encoding_options *options,
             const int *pcm_data,
             unsigned pcm_frames,
             unsigned frame_number)
{
    unsigned c;
    uint16_t crc16 = 0;

    output->add_callback(output, (bs_callback_f)flac_crc16, &crc16);

    if ((pcmreader->channels == 2) &&
        (options->mid_side || options->adaptive_mid_side)) {
        /*attempt different assignments if stereo and mid-side requested*/
        int left_channel[pcm_frames];
        int right_channel[pcm_frames];
        int average_channel[pcm_frames];
        int difference_channel[pcm_frames];

        BitstreamRecorder *left_subframe =
            bw_open_recorder(BS_BIG_ENDIAN);
        BitstreamRecorder *right_subframe =
            bw_open_recorder(BS_BIG_ENDIAN);
        BitstreamRecorder *average_subframe =
            bw_open_recorder(BS_BIG_ENDIAN);
        BitstreamRecorder *difference_subframe =
            bw_open_recorder(BS_BIG_ENDIAN);

        unsigned independent;
        unsigned left_side;
        unsigned side_right;
        unsigned mid_side;

        get_channel_data(pcm_data, 0, 2, pcm_frames, left_channel);
        get_channel_data(pcm_data, 1, 2, pcm_frames, right_channel);

        correlate_channels(pcm_frames,
                           left_channel,
                           right_channel,
                           average_channel,
                           difference_channel);

        encode_subframe((BitstreamWriter*)left_subframe,
                        options,
                        pcm_frames,
                        left_channel,
                        pcmreader->bits_per_sample);

        encode_subframe((BitstreamWriter*)right_subframe,
                        options,
                        pcm_frames,
                        right_channel,
                        pcmreader->bits_per_sample);

        encode_subframe((BitstreamWriter*)average_subframe,
                        options,
                        pcm_frames,
                        average_channel,
                        pcmreader->bits_per_sample);

        encode_subframe((BitstreamWriter*)difference_subframe,
                        options,
                        pcm_frames,
                        difference_channel,
                        pcmreader->bits_per_sample + 1);

        independent = left_subframe->bits_written(left_subframe) +
                      right_subframe->bits_written(right_subframe);

        left_side = left_subframe->bits_written(left_subframe) +
                    difference_subframe->bits_written(difference_subframe);

        side_right = difference_subframe->bits_written(difference_subframe) +
                     right_subframe->bits_written(right_subframe);

        mid_side = average_subframe->bits_written(average_subframe) +
                   difference_subframe->bits_written(difference_subframe);

        if ((independent < left_side) &&
            (independent < side_right) &&
            (independent < mid_side)) {
            /*write subframes independently*/
            write_frame_header(output,
                               pcm_frames,
                               pcmreader->sample_rate,
                               pcmreader->channels,
                               pcmreader->bits_per_sample,
                               frame_number,
                               1);
            left_subframe->copy(left_subframe, output);
            right_subframe->copy(right_subframe, output);
        } else if ((left_side < side_right) && (left_side < mid_side)) {
            /*write subframes using left-side order*/
            write_frame_header(output,
                               pcm_frames,
                               pcmreader->sample_rate,
                               pcmreader->channels,
                               pcmreader->bits_per_sample,
                               frame_number,
                               8);
            left_subframe->copy(left_subframe, output);
            difference_subframe->copy(difference_subframe, output);
        } else if (side_right < mid_side) {
            /*write subframes using side-right order*/
            write_frame_header(output,
                               pcm_frames,
                               pcmreader->sample_rate,
                               pcmreader->channels,
                               pcmreader->bits_per_sample,
                               frame_number,
                               9);
            difference_subframe->copy(difference_subframe, output);
            right_subframe->copy(right_subframe, output);
        } else {
            /*write subframes using mid-side order*/
            write_frame_header(output,
                               pcm_frames,
                               pcmreader->sample_rate,
                               pcmreader->channels,
                               pcmreader->bits_per_sample,
                               frame_number,
                               10);
            average_subframe->copy(average_subframe, output);
            difference_subframe->copy(difference_subframe, output);
        }

        left_subframe->close(left_subframe);
        right_subframe->close(right_subframe);
        average_subframe->close(average_subframe);
        difference_subframe->close(difference_subframe);
    } else {
        /*store channels independently*/

        unsigned channel_assignment = pcmreader->channels - 1;

        write_frame_header(output,
                           pcm_frames,
                           pcmreader->sample_rate,
                           pcmreader->channels,
                           pcmreader->bits_per_sample,
                           frame_number,
                           channel_assignment);

        /*write 1 subframe per channel*/
        for (c = 0; c < pcmreader->channels; c++) {
            int channel_data[pcm_frames];

            get_channel_data(pcm_data, c, pcmreader->channels,
                             pcm_frames, channel_data);

            encode_subframe(output,
                            options,
                            pcm_frames,
                            channel_data,
                            pcmreader->bits_per_sample);
        }
    }

    output->byte_align(output);

    /*write calculated CRC-16*/
    output->pop_callback(output, NULL);
    output->write(output, 16, crc16);
}

static void
correlate_channels(unsigned pcm_frames,
                   const int left_channel[],
                   const int right_channel[],
                   int average_channel[],
                   int difference_channel[])
{
    unsigned i;
    for (i = 0; i < pcm_frames; i++) {
        /*floor division, implemented as right shift*/
        average_channel[i] = (left_channel[i] + right_channel[i]) >> 1;
        difference_channel[i] = left_channel[i] - right_channel[i];
    }
}

static void
write_frame_header(BitstreamWriter *output,
                   unsigned sample_count,
                   unsigned sample_rate,
                   unsigned channels,
                   unsigned bits_per_sample,
                   unsigned frame_number,
                   unsigned channel_assignment)
{
    uint8_t crc8 = 0;
    const unsigned encoded_block_size = encode_block_size(sample_count);
    const unsigned encoded_sample_rate = encode_sample_rate(sample_rate);
    const unsigned encoded_bps = encode_bits_per_sample(bits_per_sample);

    output->add_callback(output, (bs_callback_f)flac_crc8, &crc8);

    output->build(output,
                  "14u 1u 1u 4u 4u 4u 3u 1u",
                  0x3FFE,
                  0,
                  0,
                  encoded_block_size,
                  encoded_sample_rate,
                  channel_assignment,
                  encoded_bps,
                  0);

    write_utf8(output, frame_number);

    if (encoded_block_size == 6) {
        output->write(output, 8, sample_count - 1);
    } else if (encoded_block_size == 7) {
        output->write(output, 16, sample_count - 1);
    }

    if (encoded_sample_rate == 12) {
        output->write(output, 8, sample_rate / 1000);
    } else if (encoded_sample_rate == 13) {
        output->write(output, 16, sample_rate);
    } else if (encoded_sample_rate == 14) {
        output->write(output, 16, sample_rate / 10);
    }

    output->pop_callback(output, NULL);
    output->write(output, 8, crc8);
}

static unsigned
encode_block_size(unsigned block_size)
{
    switch (block_size) {
    case 192:   return 1;
    case 576:   return 2;
    case 1152:  return 3;
    case 2304:  return 4;
    case 4608:  return 5;
    case 256:   return 8;
    case 512:   return 9;
    case 1024:  return 10;
    case 2048:  return 11;
    case 4096:  return 12;
    case 8192:  return 13;
    case 16384: return 14;
    case 32768: return 15;
    default:
            if (block_size <= (1 << 8)) {
                return 6;
            } else if (block_size <= (1 << 16)) {
                return 7;
            } else {
                return 0;
            }
    }
}

static unsigned
encode_sample_rate(unsigned sample_rate)
{
    switch (sample_rate) {
    case 88200:  return 1;
    case 176400: return 2;
    case 192000: return 3;
    case 8000: return 4;
    case 16000: return 5;
    case 22050: return 6;
    case 24000: return 7;
    case 32000: return 8;
    case 44100: return 9;
    case 48000: return 10;
    case 96000: return 11;
    default:
            if (((sample_rate % 1000) == 0) && (sample_rate <= 255000)) {
                return 12;
            } else if (((sample_rate % 10) == 0) && (sample_rate <= 655350)) {
                return 13;
            } else if (sample_rate < (1 << 16)) {
                return 14;
            } else {
                return 0;
            }
    }
}

static unsigned
encode_bits_per_sample(unsigned bits_per_sample)
{
    switch (bits_per_sample) {
    case 8: return 1;
    case 12: return 2;
    case 16: return 4;
    case 20: return 5;
    case 24: return 6;
    default: return 0;
    }
}

static void
write_utf8(BitstreamWriter *output, unsigned value)
{
    if (value <= 0x7F) {
        /*1 byte only*/
        output->write(output, 8, value);
    } else {
        unsigned int total_bytes = 0;
        int shift;

        /*more than 1 byte*/

        if (value <= 0x7FF) {
            total_bytes = 2;
        } else if (value <= 0xFFFF) {
            total_bytes = 3;
        } else if (value <= 0x1FFFFF) {
            total_bytes = 4;
        } else if (value <= 0x3FFFFFF) {
            total_bytes = 5;
        } else if (value <= 0x7FFFFFFF) {
            total_bytes = 6;
        }

        shift = (total_bytes - 1) * 6;
        /*send out the initial unary + leftover most-significant bits*/
        output->write_unary(output, 0, total_bytes);
        output->write(output, 7 - total_bytes, value >> shift);

        /*then send the least-significant bits,
          6 at a time with a unary 1 value appended*/
        for (shift -= 6; shift >= 0; shift -= 6) {
            output->write_unary(output, 0, 1);
            output->write(output, 6, (value >> shift) & 0x3F);
        }
    }
}

static void
encode_subframe(BitstreamWriter *output,
                const struct flac_encoding_options *options,
                unsigned sample_count,
                int samples[],
                unsigned bits_per_sample)
{
    if (options->use_constant && samples_identical(sample_count, samples)) {
        encode_constant_subframe(output,
                                 sample_count,
                                 samples[0],
                                 bits_per_sample,
                                 0);
    } else {
        const unsigned wasted_bps =
            calculate_wasted_bps(sample_count, samples);
        unsigned smallest_subframe_size = 0;
        BitstreamRecorder *fixed_subframe = NULL;
        BitstreamRecorder *lpc_subframe = NULL;

        /*remove wasted bits from least-signficant bits, if any*/
        if (wasted_bps) {
            unsigned i;
            for (i = 0; i < sample_count; i++) {
                samples[i] >>= wasted_bps;
            }
            bits_per_sample -= wasted_bps;
        }

        if (options->use_verbatim) {
            smallest_subframe_size =
                8 + wasted_bps +
                ((bits_per_sample - wasted_bps) * sample_count);
        }

        if (options->use_fixed) {
            fixed_subframe =
                bw_open_limited_recorder(BS_BIG_ENDIAN,
                                         ceil_div(smallest_subframe_size, 8));

            if (!setjmp(*bw_try((BitstreamWriter*)fixed_subframe))) {
                encode_fixed_subframe((BitstreamWriter*)fixed_subframe,
                                      options,
                                      sample_count,
                                      samples,
                                      bits_per_sample,
                                      wasted_bps);
                bw_etry((BitstreamWriter*)fixed_subframe);

                if (!smallest_subframe_size ||
                    (fixed_subframe->bits_written(fixed_subframe) <=
                     smallest_subframe_size)) {
                    smallest_subframe_size =
                        fixed_subframe->bits_written(fixed_subframe);
                } else {
                    /*FIXED subframe too large*/

                    /*this is a rare case when the FIXED subframe
                      isn't larger by some whole number of bytes*/
                    fixed_subframe->close(fixed_subframe);
                    fixed_subframe = NULL;
                }
            } else {
                /*FIXED subframe too large*/
                bw_etry((BitstreamWriter*)fixed_subframe);
                fixed_subframe->close(fixed_subframe);
                fixed_subframe = NULL;
            }
        }

        if (options->max_lpc_order) {
            lpc_subframe =
                bw_open_limited_recorder(BS_BIG_ENDIAN,
                                         ceil_div(smallest_subframe_size, 8));

            if (!setjmp(*bw_try((BitstreamWriter*)lpc_subframe))) {
                encode_lpc_subframe((BitstreamWriter*)lpc_subframe,
                                    options,
                                    sample_count,
                                    samples,
                                    bits_per_sample,
                                    wasted_bps);
                bw_etry((BitstreamWriter*)lpc_subframe);

                if (!smallest_subframe_size ||
                    (lpc_subframe->bits_written(lpc_subframe) <=
                     smallest_subframe_size)) {
                    smallest_subframe_size =
                        lpc_subframe->bits_written(lpc_subframe);
                    if (fixed_subframe) {
                        fixed_subframe->close(fixed_subframe);
                        fixed_subframe = NULL;
                    }
                } else {
                    /*LPC subframe too large*/

                    /*this is a rare case when the LPC subframe
                      isn't larger by some whole number of bytes*/
                    lpc_subframe->close(lpc_subframe);
                    lpc_subframe = NULL;
                }
            } else {
                /*LPC subframe too large*/
                bw_etry((BitstreamWriter*)lpc_subframe);
                lpc_subframe->close(lpc_subframe);
                lpc_subframe = NULL;
            }
        }

        if (lpc_subframe) {
            lpc_subframe->copy(lpc_subframe, output);
            lpc_subframe->close(lpc_subframe);
        } else if (fixed_subframe) {
            fixed_subframe->copy(fixed_subframe, output);
            fixed_subframe->close(fixed_subframe);
        } else {
            encode_verbatim_subframe(output,
                                     sample_count,
                                     samples,
                                     bits_per_sample,
                                     wasted_bps);
        }
    }
}

static void
write_subframe_header(BitstreamWriter *output,
                      subframe_type_t subframe_type,
                      unsigned predictor_order,
                      unsigned wasted_bps)
{
    output->write(output, 1, 0);

    switch (subframe_type) {
    case CONSTANT:
        output->write(output, 6, 0);
        break;
    case VERBATIM:
        output->write(output, 6, 1);
        break;
    case FIXED:
        output->write(output, 3, 1);
        output->write(output, 3, predictor_order);
        break;
    case LPC:
        output->write(output, 1, 1);
        output->write(output, 5, predictor_order - 1);
    }

    if (wasted_bps > 0) {
        output->write(output, 1, 1);
        output->write_unary(output, 1, wasted_bps - 1);
    } else {
        output->write(output, 1, 0);
    }
}

static void
encode_constant_subframe(BitstreamWriter *output,
                         unsigned sample_count,
                         int sample,
                         unsigned bits_per_sample,
                         unsigned wasted_bps)
{
    write_subframe_header(output, CONSTANT, 0, wasted_bps);
    output->write_signed(output, bits_per_sample, sample);
}

static void
encode_verbatim_subframe(BitstreamWriter *output,
                         unsigned sample_count,
                         const int samples[],
                         unsigned bits_per_sample,
                         unsigned wasted_bps)
{
    unsigned i;

    write_subframe_header(output, VERBATIM, 0, wasted_bps);
    for (i = 0; i < sample_count; i++) {
        output->write_signed(output, bits_per_sample, samples[i]);
    }
}

static void
encode_fixed_subframe(BitstreamWriter *output,
                      const struct flac_encoding_options *options,
                      unsigned sample_count,
                      const int samples[],
                      unsigned bits_per_sample,
                      unsigned wasted_bps)
{
    const unsigned max_order = sample_count > 4 ? 4 : sample_count - 1;
    int order1[max_order >= 1 ? sample_count - 1 : 0];
    int order2[max_order >= 2 ? sample_count - 2 : 0];
    int order3[max_order >= 3 ? sample_count - 3 : 0];
    int order4[max_order >= 4 ? sample_count - 4 : 0];
    const int *orders[] = {samples, order1, order2, order3, order4};
    uint64_t best_order_sum;
    unsigned best_order;
    unsigned i;

    /*determine best FIXED subframe order*/
    if (max_order >= 1) {
        next_fixed_order(sample_count, samples, order1);
    }
    if (max_order >= 2) {
        next_fixed_order(sample_count - 1, order1, order2);
    }
    if (max_order >= 3) {
        next_fixed_order(sample_count - 2, order2, order3);
    }
    if (max_order >= 4) {
        next_fixed_order(sample_count - 3, order3, order4);
    }

    best_order_sum = abs_sum(sample_count, orders[0]);
    best_order = 0;

    for (i = 1; i <= max_order; i++) {
        const uint64_t order_sum = abs_sum(sample_count - i, orders[i]);
        if (order_sum < best_order_sum) {
            best_order_sum = order_sum;
            best_order = i;
        }
    }

    /*write subframe header*/
    write_subframe_header(output,
                          FIXED,
                          best_order,
                          wasted_bps);

    /*write warm-up samples*/
    for (i = 0; i < best_order; i++) {
        output->write_signed(output, bits_per_sample, samples[i]);
    }

    /*write residual block*/
    write_residual_block(output,
                         options,
                         sample_count,
                         best_order,
                         orders[i]);
}

static void
next_fixed_order(unsigned sample_count,
                 const int previous_order[],
                 int next_order[])
{
    unsigned i;
    for (i = 1; i < sample_count; i++) {
        next_order[i - 1] = previous_order[i] - previous_order[i - 1];
    }
}

static uint64_t
abs_sum(unsigned count, const int values[])
{
    uint64_t accumulator = 0;
    for (; count; count--) {
        accumulator += abs(*values);
        values += 1;
    }
    return accumulator;
}

static void
encode_lpc_subframe(BitstreamWriter *output,
                    const struct flac_encoding_options *options,
                    unsigned sample_count,
                    const int samples[],
                    unsigned bits_per_sample,
                    unsigned wasted_bps)
{
    unsigned predictor_order;
    unsigned precision;
    int shift;
    int coefficients[MAX_QLP_COEFFS];

    calculate_best_lpc_params(options,
                              sample_count,
                              samples,
                              bits_per_sample,
                              &predictor_order,
                              &precision,
                              &shift,
                              coefficients);

    write_subframe_header(output, LPC, predictor_order, wasted_bps);

    write_lpc_subframe(output,
                       options,
                       sample_count,
                       samples,
                       bits_per_sample,
                       predictor_order,
                       precision,
                       shift,
                       coefficients);
}

static void
write_lpc_subframe(BitstreamWriter *output,
                   const struct flac_encoding_options *options,
                   unsigned sample_count,
                   const int samples[],
                   unsigned bits_per_sample,
                   unsigned predictor_order,
                   unsigned precision,
                   int shift,
                   const int coefficients[])
{
    int residuals[sample_count - 1];
    unsigned i;

    for (i = 0; i < predictor_order; i++) {
        output->write_signed(output, bits_per_sample, samples[i]);
    }
    output->write(output, 4, precision - 1);
    output->write_signed(output, 5, shift);
    for (i = 0; i < predictor_order; i++) {
        output->write_signed(output, precision, coefficients[i]);
    }
    for (i = predictor_order; i < sample_count; i++) {
        int64_t sum = 0;
        unsigned j;
        for (j = 0; j < predictor_order; j++) {
            sum += ((int64_t)coefficients[j] * (int64_t)samples[i - j - 1]);
        }
        sum >>= shift;
        residuals[i - predictor_order] = samples[i] - sum;
    }
    write_residual_block(output,
                         options,
                         sample_count,
                         predictor_order,
                         residuals);
}

static void
calculate_best_lpc_params(const struct flac_encoding_options *options,
                          unsigned sample_count,
                          const int samples[],
                          unsigned bits_per_sample,
                          unsigned *predictor_order,
                          unsigned *precision,
                          int *shift,
                          int coefficients[])
{
    assert(sample_count > 0);

    if (sample_count == 1) {
        /*set some dummy coefficients since the only sample
          will be a warm-up sample*/
        *predictor_order = 1;
        *precision = 2;
        *shift = 0;
        coefficients[0] = 0;
    } else {
        const unsigned max_lpc_order =
            sample_count <= options->max_lpc_order ?
            sample_count - 1 : options->max_lpc_order;
        double windowed_signal[sample_count];
        double autocorrelated[options->max_lpc_order + 1];

        window_signal(sample_count, samples, options->window, windowed_signal);

        compute_autocorrelation_values(sample_count,
                                       windowed_signal,
                                       max_lpc_order,
                                       autocorrelated);

        if (autocorrelated[0] == 0.0) {
            /*all samples are 0, so use dummy coefficients*/
            *predictor_order = 1;
            *precision = 2;
            *shift = 0;
            coefficients[0] = 0;
        } else {
            *precision = options->qlp_coeff_precision;
            double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS];
            double error[max_lpc_order];

            compute_lp_coefficients(max_lpc_order,
                                    autocorrelated,
                                    lp_coeff,
                                    error);

            if (!options->exhaustive_model_search) {
                /*if not exhaustive search, estimate best order*/
                *predictor_order =
                    estimate_best_lpc_order(bits_per_sample,
                                            *precision,
                                            sample_count,
                                            max_lpc_order,
                                            error);

                /*then quantize coefficients of estimated best order*/
                quantize_lp_coefficients(*predictor_order,
                                         lp_coeff,
                                         *precision,
                                         coefficients,
                                         shift);
            } else {
                /*if exhaustive search, quantize all coefficients*/

                unsigned order;
                unsigned best_subframe_size = UINT_MAX;

                for (order = 1; order <= max_lpc_order; order++) {
                    BitstreamAccumulator *subframe =
                        bw_open_limited_accumulator(
                            BS_BIG_ENDIAN,
                            best_subframe_size == UINT_MAX ?
                            0 : best_subframe_size);
                    int candidate_coeff[order];
                    int candidate_shift;

                    quantize_lp_coefficients(order,
                                             lp_coeff,
                                             *precision,
                                             candidate_coeff,
                                             &candidate_shift);

                    if (!setjmp(*bw_try((BitstreamWriter*)subframe))) {
                        write_lpc_subframe((BitstreamWriter*)subframe,
                                           options,
                                           sample_count,
                                           samples,
                                           bits_per_sample,
                                           order,
                                           *precision,
                                           candidate_shift,
                                           candidate_coeff);

                        bw_etry((BitstreamWriter*)subframe);

                        if (subframe->bits_written(subframe) <
                            best_subframe_size) {
                            /*and use values which generate
                              the smallest LPC subframe when written*/
                            *predictor_order = order;
                            *shift = candidate_shift;
                            memcpy(coefficients,
                                   candidate_coeff,
                                   order * sizeof(int));
                            best_subframe_size =
                                subframe->bits_written(subframe);
                        }
                    } else {
                        bw_etry((BitstreamWriter*)subframe);
                    }

                    subframe->close(subframe);
                }
            }
        }
    }
}

static void
window_signal(unsigned sample_count,
              const int samples[],
              const double window[],
              double windowed_signal[])
{
    unsigned i;
    for (i = 0; i < sample_count; i++) {
        windowed_signal[i] = samples[i] * window[i];
    }
}

static void
compute_autocorrelation_values(unsigned sample_count,
                               const double windowed_signal[],
                               unsigned max_lpc_order,
                               double autocorrelated[])
{
    unsigned i;
    unsigned j;

    for (i = 0; i <= max_lpc_order; i++) {
        autocorrelated[i] = 0.0;
        for (j = 0; j < sample_count - i; j++) {
            autocorrelated[i] += windowed_signal[j] * windowed_signal[j + i];
        }
    }
}

static void
compute_lp_coefficients(unsigned max_lpc_order,
                        const double autocorrelated[],
                        double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS],
                        double error[])
{
    double k;
    double q;
    unsigned i;

    k = autocorrelated[1] / autocorrelated[0];
    lp_coeff[0][0] = k;
    error[0] = autocorrelated[0] * (1.0 - pow(k, 2));
    for (i = 1; i < max_lpc_order; i++) {
        double sum = 0.0;
        unsigned j;
        for (j = 0; j < i; j++) {
            sum += lp_coeff[i - 1][j] * autocorrelated[i - j];
        }
        q = autocorrelated[i + 1] - sum;
        k = q / error[i - 1];
        for (j = 0; j < i; j++) {
            lp_coeff[i][j] =
                lp_coeff[i - 1][j] - (k * lp_coeff[i - 1][i - j - 1]);
        }
        lp_coeff[i][i] = k;
        error[i] = error[i - 1] * (1.0 - pow(k, 2));
    }
}

static unsigned
estimate_best_lpc_order(unsigned bits_per_sample,
                        unsigned precision,
                        unsigned sample_count,
                        unsigned max_lpc_order,
                        const double error[])
{
    const double error_scale = pow(log(2), 2) / (sample_count * 2);
    double best_bits = DBL_MAX;
    unsigned best_order = 0;
    unsigned i;
    for (i = 1; i <= max_lpc_order; i++) {
        const double header_bits =
            i * (bits_per_sample + precision);
        const double bits_per_residual =
            log2(error[i - 1] * error_scale) / 2;
        const double subframe_bits =
            header_bits + (bits_per_residual * (sample_count - i));

        if (subframe_bits < best_bits) {
            best_order = i;
            best_bits = subframe_bits;
        }
    }
    assert(best_order > 0);
    return best_order;
}

static void
quantize_lp_coefficients(unsigned lpc_order,
                         double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS],
                         unsigned precision,
                         int qlp_coeff[],
                         int *shift)
{
    const int max_coeff = (1 << (precision - 1)) - 1;
    const int min_coeff = -(1 << (precision - 1));
    const int min_shift = 0;
    const int max_shift = (1 << 4) - 1;
    double max_lp_coeff = 0.0;
    unsigned error = 0.0;
    unsigned i;

    for (i = 0; i < lpc_order; i++) {
        if (fabs(lp_coeff[lpc_order - 1][i]) > max_lp_coeff) {
            max_lp_coeff = fabs(lp_coeff[lpc_order - 1][i]);
        }
    }
    assert(max_lp_coeff > 0.0);
    *shift = (precision - 1) - (int)(floor(log2(max_lp_coeff))) - 1;

    /*ensure shift fits into a signed 5 bit value*/
    if (*shift < min_shift) {
        /*don't use negative shifts*/
        *shift = min_shift;
    } else if (*shift > max_shift) {
        *shift = max_shift;
    }

    for (i = 0; i < lpc_order; i++) {
        const double sum = error + lp_coeff[lpc_order - 1][i] * (1 << *shift);
        const int round_sum = lround(sum);
        qlp_coeff[i] = MIN(MAX(round_sum, min_coeff), max_coeff);
        assert(qlp_coeff[i] <= (1 << (precision - 1)) - 1);
        assert(qlp_coeff[i] >= -(1 << (precision - 1)));
        error = sum - qlp_coeff[i];
    }
}

static void
write_residual_block(BitstreamWriter *output,
                     const struct flac_encoding_options *options,
                     unsigned sample_count,
                     unsigned predictor_order,
                     const int residuals[])
{
    unsigned partition_order;
    unsigned partition_count;
    unsigned rice_parameters[1 << options->max_residual_partition_order];
    unsigned coding = 0;
    unsigned p;
    unsigned i = 0;

    best_rice_parameters(options,
                         sample_count,
                         predictor_order,
                         residuals,
                         &partition_order,
                         rice_parameters);

    partition_count = 1 << partition_order;

    /*adjust coding method for large Rice parameters*/
    for (p = 0; p < partition_count; p++) {
        if (rice_parameters[p] > 14) {
            coding = 1;
        }
    }

    output->write(output, 2, coding);
    output->write(output, 4, partition_order);

    /*write residual partition(s)*/
    for (p = 0; p < partition_count; p++) {
        unsigned partition_size =
            (sample_count / partition_count) - (p == 0 ? predictor_order : 0);
        const int shift = 1 << rice_parameters[p];

        output->write(output, coding ? 5 : 4, rice_parameters[p]);

        for (; partition_size; partition_size--) {
            const int unsigned_ =
                residuals[i] >= 0 ?
                residuals[i] << 1 :
                ((-residuals[i] - 1) << 1) + 1;

            const div_t split = div(unsigned_, shift);

            output->write_unary(output, 1, split.quot);

            output->write(output, rice_parameters[p], split.rem);

            i += 1;
        }
    }
}

static void
best_rice_parameters(const struct flac_encoding_options *options,
                     unsigned sample_count,
                     unsigned predictor_order,
                     const int residuals[],
                     unsigned *partition_order,
                     unsigned rice_parameters[])
{
    if ((sample_count - predictor_order) == 0) {
        /*no residuals*/
        *partition_order = 0;
        rice_parameters[0] = 0;
    } else {
        const unsigned max_p_order =
            maximum_partition_order(sample_count,
                                    predictor_order,
                                    options->max_residual_partition_order);
        unsigned i;
        unsigned best_total_size = UINT_MAX;

        for (i = 0; i <= max_p_order; i++) {
            const unsigned partition_count = 1 << i;
            unsigned p_rice[partition_count];
            unsigned total_partitions_size = 0;
            unsigned p;

            for (p = 0; p < partition_count; p++) {
                const unsigned partition_samples =
                    (sample_count / partition_count) -
                    ((p == 0) ? predictor_order : 0);
                const unsigned start =
                    (p == 0) ? 0 :
                    p * sample_count / partition_count - predictor_order;
                const unsigned end = start + partition_samples;
                unsigned j;
                unsigned partition_sum = 0;
                unsigned partition_size;

                for (j = start; j < end; j++) {
                    partition_sum += abs(residuals[j]);
                }

                if (partition_sum > partition_samples) {
                    p_rice[p] =
                        ceil(log2((double)partition_sum /
                                  (double)partition_samples));
                    if (p_rice[p] > options->max_rice_parameter) {
                        p_rice[p] = options->max_rice_parameter;
                    }
                } else {
                    p_rice[p] = 0;
                }

                partition_size =
                    4 +
                    ((1 + p_rice[p]) * partition_samples) +
                    ((p_rice[p] > 0) ?
                    (partition_sum >> (p_rice[p] - 1)) :
                    (partition_sum << 1)) -
                    (partition_samples / 2);

                total_partitions_size += partition_size;
            }

            if (total_partitions_size < best_total_size) {
                best_total_size = total_partitions_size;
                *partition_order = i;
                memcpy(rice_parameters,
                       p_rice,
                       sizeof(unsigned) * partition_count);
            }
        }
    }
}

static unsigned
maximum_partition_order(unsigned sample_count,
                        unsigned predictor_order,
                        unsigned max_partition_order)
{
    unsigned i = 0;

    /*ensure residuals divide evenly into 2 ^ i partitions,
      that the initial partition contains at least 1 sample
      and that the partition order doesn't exceed 15*/
    while (((sample_count % (1 << i)) == 0) &&
           ((sample_count / (1 << i)) > predictor_order) &&
           (i <= max_partition_order)) {
        i += 1;
    }

    /*if one of the conditions no longer holds, back up one*/
    return (i > 0) ? i - 1 : 0;
}

static struct flac_frame_size*
push_frame_size(struct flac_frame_size *head,
                unsigned byte_size,
                unsigned pcm_frames_size)
{
    struct flac_frame_size *frame_size = malloc(sizeof(struct flac_frame_size));
    frame_size->byte_size = byte_size;
    frame_size->pcm_frames_size = pcm_frames_size;
    frame_size->next = head;
    return frame_size;
}

static void
reverse_frame_sizes(struct flac_frame_size **head)
{
    struct flac_frame_size *reversed = NULL;
    struct flac_frame_size *top = *head;
    while (top) {
        *head = (*head)->next;
        top->next = reversed;
        reversed = top;
        top = *head;
    }
    *head = reversed;
}

static int
samples_identical(unsigned sample_count, const int *samples)
{
    unsigned i;
    assert(sample_count > 0);

    for (i = 1; i < sample_count; i++) {
        if (samples[0] != samples[i]) {
            return 0;
        }
    }
    return 1;
}

static inline unsigned
sample_wasted_bps(int sample) {
    if (sample == 0) {
        return UINT_MAX;
    } else {
        unsigned j = 1;
        while ((sample % (1 << j)) == 0) {
            j += 1;
        }
        return j - 1;
    }
}

static unsigned
calculate_wasted_bps(unsigned sample_count, const int *samples)
{
    unsigned wasted_bps = UINT_MAX;
    unsigned i;
    for (i = 0; i < sample_count; i++) {
        const unsigned wasted = sample_wasted_bps(samples[i]);
        if (wasted == 0) {
            /*stop looking once a wasted BPS of 0 is found*/
            return 0;
        } else if (wasted < wasted_bps) {
            wasted_bps = wasted;
        }
    }
    return (wasted_bps < UINT_MAX) ? wasted_bps : 0;
}

static void
tukey_window(double alpha, unsigned block_size, double *window)
{
    unsigned Np = alpha / 2 * block_size - 1;
    unsigned i;
    for (i = 0; i < block_size; i++) {
        if (i <= Np) {
            window[i] = (1 - cos(M_PI * i / Np)) / 2;
        } else if (i >= (block_size - Np - 1)) {
            window[i] = (1 - cos(M_PI * (block_size - i - 1) / Np)) / 2;
        } else {
            window[i] = 1.0;
        }
    }
}

/*****************
 * main function *
 *****************/

#ifdef EXECUTABLE

#include <getopt.h>
#include <errno.h>

int main(int argc, char *argv[])
{
    static struct flac_encoding_options options;
    char* output_filename = NULL;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;
    struct PCMReader *pcmreader;
    FILE *output_file;
    BitstreamWriter *output;
    struct flac_frame_size *frame_sizes;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"block-size",              required_argument, NULL, 'B'},
        {"max-lpc-order",           required_argument, NULL, 'l'},
        {"min-partition-order",     required_argument, NULL, 'P'},
        {"max-partition-order",     required_argument, NULL, 'R'},
        {"mid-side",                no_argument,
         &options.mid_side, 1},
        {"adaptive-mid-side",       no_argument,
         &options.adaptive_mid_side, 1},
        {"exhaustive-model-search", no_argument,
         &options.exhaustive_model_search, 1},
        {"disable-verbatim-subframes", no_argument,
         &options.use_verbatim, 0},
        {"disable-constant-subframes", no_argument,
         &options.use_constant, 0},
        {"disable-fixed-subframes", no_argument,
         &options.use_fixed, 0},
        {NULL,                      no_argument,       NULL,  0}
    };
    const static char* short_opts = "-hc:r:b:B:l:P:R:mMe";

    flacenc_init_options(&options);

    errno = 0;
    while ((c = getopt_long(argc,
                            argv,
                            short_opts,
                            long_opts,
                            NULL)) != -1) {
        switch (c) {
        case 1:
            if (output_filename == NULL) {
                output_filename = optarg;
            } else {
                printf("only one output file allowed\n");
                return 1;
            }
            break;
        case 'c':
            if (((channels = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --channel \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'r':
            if (((sample_rate = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --sample-rate \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'b':
            if (((bits_per_sample = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --bits-per-sample \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'B':
            if (((options.block_size = strtoul(optarg, NULL, 10)) == 0) &&
                  errno) {
                printf("invalid --block-size \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'l':
            if (((options.max_lpc_order = strtoul(optarg, NULL, 10)) == 0) &&
                  errno) {
                printf("invalid --max-lpc-order \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'P':
            if (((options.min_residual_partition_order =
                  strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --min-partition-order \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'R':
            if (((options.max_residual_partition_order =
                  strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --max-partition-order \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'm':
            options.mid_side = 1;
            break;
        case 'M':
            options.adaptive_mid_side = 1;
            break;
        case 'e':
            options.exhaustive_model_search = 1;
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: flacenc [options] <output.flac>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("\n");
            printf("-B, --block-size=#              block size\n");
            printf("-l, --max-lpc-order=#           maximum LPC order\n");
            printf("-P, --min-partition-order=#     minimum partition order\n");
            printf("-R, --max-partition-order=#     maximum partition order\n");
            printf("-m, --mid-side                  use mid-side encoding\n");
            printf("-M, --adaptive-mid-side         "
                   "use adaptive mid-side encoding\n");
            printf("-m, --mid-side                  use mid-side encoding\n");
            printf("-e, --exhaustive-model-search   "
                   "search for best subframe exhaustively\n");
            return 0;
        default:
            break;
        }
    }

    assert((channels > 0) && (channels <= 8));
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16) ||
           (bits_per_sample == 24));
    assert(sample_rate > 0);

    errno = 0;
    if (output_filename == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    } else if ((output_file = fopen(output_filename, "wb")) == NULL) {
        fprintf(stderr, "*** Error %s: %s\n", output_filename, strerror(errno));
        return 1;
    }

    pcmreader = pcmreader_open(stdin,
                               sample_rate,
                               channels,
                               0,
                               bits_per_sample,
                               1,1);
    output = bw_open(output_file, BS_BIG_ENDIAN);

    pcmreader_display(pcmreader, stderr);
    fputs("\n", stderr);
    flacenc_display_options(&options, stderr);

    frame_sizes = flacenc_encode_flac(pcmreader, output, &options, 0);

    while (frame_sizes) {
        struct flac_frame_size *next = frame_sizes->next;
        fprintf(stderr, "frame size : %u bytes, %u samples\n",
                frame_sizes->byte_size,
                frame_sizes->pcm_frames_size);
        free(frame_sizes);
        frame_sizes = next;
    }

    output->close(output);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}
#endif
