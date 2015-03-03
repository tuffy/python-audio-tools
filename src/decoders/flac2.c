#include <inttypes.h>
#include <string.h>
#include <assert.h>
#include "../bitstream.h"
#include "../common/flac_crc.h"
#include "../framelist.h"
#include "../pcm_conv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

typedef enum {OK,
              INVALID_SYNC_CODE,
              INVALID_SAMPLE_RATE,
              INVALID_BPS,
              INVALID_CHANNEL_ASSIGNMENT,
              INVALID_UTF8,
              INVALID_CRC8,
              IOERROR_HEADER,
              IOERROR_SUBFRAME,
              INVALID_SUBFRAME_HEADER,
              INVALID_FIXED_ORDER,
              INVALID_LPC_ORDER,
              INVALID_CODING_METHOD} status_t;

typedef enum {INDEPENDENT,
              LEFT_DIFFERENCE,
              DIFFERENCE_RIGHT,
              AVERAGE_DIFFERENCE} channel_assignment_t;

typedef enum {CONSTANT,
              VERBATIM,
              FIXED,
              LPC} subframe_type_t;

struct STREAMINFO {
    unsigned minimum_block_size;
    unsigned maximum_block_size;
    unsigned minimum_frame_size;
    unsigned maximum_frame_size;
    unsigned sample_rate;
    unsigned channel_count;
    unsigned bits_per_sample;
    uint64_t total_samples;
    uint8_t MD5[16];
};

struct SEEKPOINT {
    uint64_t sample_number;
    uint64_t frame_offset;
    unsigned frame_samples;
};

struct SEEKTABLE {
    unsigned total_points;
    struct SEEKPOINT *seek_points;
};

struct frame_header {
    unsigned blocking_strategy;
    unsigned block_size;
    unsigned sample_rate;
    channel_assignment_t channel_assignment;
    unsigned channel_count;
    unsigned bits_per_sample;
    unsigned frame_number;
};

/*******************************
 * private function signatures *
 *******************************/

static int
valid_stream_id(BitstreamReader *r);

static void
read_block_header(BitstreamReader *r,
                  unsigned *last,
                  unsigned *type,
                  unsigned *size);

static void
read_STREAMINFO(BitstreamReader *r, struct STREAMINFO *streaminfo);

static void
read_SEEKTABLE(BitstreamReader *r,
               unsigned block_size,
               struct SEEKTABLE *seektable);

static void
read_VORBIS_COMMENT(BitstreamReader *r, unsigned *channel_mask);

static status_t
read_frame_header(BitstreamReader *r,
                  const struct STREAMINFO *streaminfo,
                  struct frame_header *frame_header);

static status_t
read_utf8(BitstreamReader *r, unsigned *utf8);

static status_t
read_subframe(BitstreamReader *r,
              unsigned block_size,
              unsigned bits_per_sample,
              int channel_data[]);

static status_t
read_subframe_header(BitstreamReader *r,
                     subframe_type_t *type,
                     unsigned *order,
                     unsigned *wasted_bps);

static void
read_CONSTANT_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[]);

static void
read_VERBATIM_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[]);

static status_t
read_FIXED_subframe(BitstreamReader *r,
                    unsigned block_size,
                    unsigned bits_per_sample,
                    unsigned predictor_order,
                    int samples[]);

static status_t
read_LPC_subframe(BitstreamReader *r,
                  unsigned block_size,
                  unsigned bits_per_sample,
                  unsigned predictor_order,
                  int samples[]);

static status_t
read_residual_block(BitstreamReader *r,
                    unsigned block_size,
                    unsigned predictor_order,
                    int residuals[]);

static void
decorrelate_left_difference(unsigned block_size,
                            const int left[],
                            const int difference[],
                            int right[]);
static void
decorrelate_difference_right(unsigned block_size,
                             const int difference[],
                             const int right[],
                             int left[]);

static void
decorrelate_average_difference(unsigned block_size,
                               const int average[],
                               const int difference[],
                               int left[],
                               int right[]);

const char*
flac_strerror(status_t status);

/***********************************
 * public function implementations *
 ***********************************/

/************************************
 * private function implementations *
 ************************************/

static int
valid_stream_id(BitstreamReader *r)
{
    unsigned char stream_id[4];
    const unsigned char valid_stream_id[4] = "fLaC";
    r->read_bytes(r, stream_id, 4);
    return (memcmp(stream_id, valid_stream_id, 4) == 0);
}

static void
read_block_header(BitstreamReader *r,
                  unsigned *last,
                  unsigned *type,
                  unsigned *size)
{
    r->parse(r, "1u 7u 24u", last, type, size);
}

static void
read_STREAMINFO(BitstreamReader *r, struct STREAMINFO *streaminfo)
{
    streaminfo->minimum_block_size = r->read(r, 16);
    streaminfo->maximum_block_size = r->read(r, 16);
    streaminfo->minimum_frame_size = r->read(r, 24);
    streaminfo->maximum_frame_size = r->read(r, 24);
    streaminfo->sample_rate = r->read(r, 20);
    streaminfo->channel_count = r->read(r, 3) + 1;
    streaminfo->bits_per_sample = r->read(r, 5) + 1;
    streaminfo->total_samples = r->read_64(r, 36);
    r->read_bytes(r, streaminfo->MD5, 16);
}

static void
read_SEEKTABLE(BitstreamReader *r,
               unsigned block_size,
               struct SEEKTABLE *seektable)
{
    const unsigned seekpoint_size = (64 + 64 + 16) / 8;
    unsigned i;

    seektable->total_points = block_size / seekpoint_size;
    seektable->seek_points =
        malloc(sizeof(struct SEEKPOINT) * seektable->total_points);
    for (i = 0; i < seektable->total_points; i++) {
        r->parse(r, "64U 64U 16u",
                 &(seektable->seek_points[i].sample_number),
                 &(seektable->seek_points[i].frame_offset),
                 &(seektable->seek_points[i].frame_samples));
    }
}

static void
read_VORBIS_COMMENT(BitstreamReader *r, unsigned *channel_mask)
{
    unsigned total_entries;

    r->set_endianness(r, BS_LITTLE_ENDIAN);

    /*ignore vendor string*/
    r->skip_bytes(r, r->read(r, 32));

    for (total_entries = r->read(r, 32);
         total_entries;
         total_entries--) {
        /*FIXME - look for channel mask entry*/
        r->skip_bytes(r, r->read(r, 32));
    }

    r->set_endianness(r, BS_BIG_ENDIAN);
}

static status_t
read_frame_header(BitstreamReader *r,
                  const struct STREAMINFO *streaminfo,
                  struct frame_header *frame_header)
{
    uint8_t crc8 = 0;
    unsigned encoded_block_size;
    unsigned encoded_sample_rate;
    unsigned encoded_channels;
    unsigned encoded_bps;

    if (!setjmp(*br_try(r))) {
        status_t status;

        r->add_callback(r, (bs_callback_f)flac_crc8, &crc8);
        if (r->read(r, 14) != 0x3FFE) {
            br_etry(r);
            return INVALID_SYNC_CODE;
        }
        r->skip(r, 1);
        frame_header->blocking_strategy = r->read(r, 1);
        encoded_block_size = r->read(r, 4);
        encoded_sample_rate = r->read(r, 4);
        encoded_channels = r->read(r, 4);
        encoded_bps = r->read(r, 3);
        r->skip(r, 1);
        if ((status = read_utf8(r, &(frame_header->frame_number))) != OK) {
            br_etry(r);
            return status;
        }

        switch (encoded_block_size) {
        case 0:
        default:
            frame_header->block_size = streaminfo->maximum_block_size;
            break;
        case 1: frame_header->block_size = 192; break;
        case 2: frame_header->block_size = 576; break;
        case 3: frame_header->block_size = 1152; break;
        case 4: frame_header->block_size = 2304; break;
        case 5: frame_header->block_size = 4608; break;
        case 6: frame_header->block_size = r->read(r, 8) + 1; break;
        case 7: frame_header->block_size = r->read(r, 16) + 1; break;
        case 8: frame_header->block_size = 256; break;
        case 9: frame_header->block_size = 512; break;
        case 10: frame_header->block_size = 1024; break;
        case 11: frame_header->block_size = 2048; break;
        case 12: frame_header->block_size = 4096; break;
        case 13: frame_header->block_size = 8192; break;
        case 14: frame_header->block_size = 16384; break;
        case 15: frame_header->block_size = 32768; break;
        }

        switch (encoded_sample_rate) {
        case 0:
        default:
            frame_header->sample_rate = streaminfo->sample_rate;
            break;
        case 1: frame_header->sample_rate = 88200; break;
        case 2: frame_header->sample_rate = 176400; break;
        case 3: frame_header->sample_rate = 192000; break;
        case 4: frame_header->sample_rate = 8000; break;
        case 5: frame_header->sample_rate = 16000; break;
        case 6: frame_header->sample_rate = 22050; break;
        case 7: frame_header->sample_rate = 24000; break;
        case 8: frame_header->sample_rate = 32000; break;
        case 9: frame_header->sample_rate = 44100; break;
        case 10: frame_header->sample_rate = 48000; break;
        case 11: frame_header->sample_rate = 96000; break;
        case 12: frame_header->sample_rate = r->read(r, 8) * 1000; break;
        case 13: frame_header->sample_rate = r->read(r, 16); break;
        case 14: frame_header->sample_rate = r->read(r, 16) * 10; break;
        case 15:
            br_etry(r);
            return INVALID_SAMPLE_RATE;
        }

        switch (encoded_bps) {
        case 0:
        default:
            frame_header->bits_per_sample = streaminfo->bits_per_sample;
            break;
        case 1: frame_header->bits_per_sample = 8; break;
        case 2: frame_header->bits_per_sample = 12; break;
        case 4: frame_header->bits_per_sample = 16; break;
        case 5: frame_header->bits_per_sample = 20; break;
        case 6: frame_header->bits_per_sample = 24; break;
        case 3:
        case 7:
            br_etry(r);
            return INVALID_BPS;
        }

        switch (encoded_channels) {
        case 0:
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
        case 6:
        case 7:
            frame_header->channel_assignment = INDEPENDENT;
            frame_header->channel_count = encoded_channels + 1;
            break;
        case 8:
            frame_header->channel_assignment = LEFT_DIFFERENCE;
            frame_header->channel_count = 2;
            break;
        case 9:
            frame_header->channel_assignment = DIFFERENCE_RIGHT;
            frame_header->channel_count = 2;
            break;
        case 10:
            frame_header->channel_assignment = AVERAGE_DIFFERENCE;
            frame_header->channel_count = 2;
            break;
        default:
            br_etry(r);
            return INVALID_CHANNEL_ASSIGNMENT;
        }

        r->skip(r, 8); /*CRC-8*/
        br_etry(r);
        r->pop_callback(r, NULL);
        if (crc8) {
            return INVALID_CRC8;
        } else {
            return OK;
        }
    } else {
        br_etry(r);
        return IOERROR_HEADER;
    }
}

static status_t
read_utf8(BitstreamReader *r, unsigned *utf8)
{
    const unsigned count = r->read_unary(r, 0);
    unsigned i;
    *utf8 = r->read(r, 7 - count);
    if (count > 0) {
        for (i = 0; i < (count - 1); i++) {
            if (r->read(r, 2) == 2) {
                *utf8 = (*utf8 << 8) | (r->read(r, 6));
            } else {
                return INVALID_UTF8;
            }
        }
    }
    return OK;
}

static status_t
read_subframe(BitstreamReader *r,
              unsigned block_size,
              unsigned bits_per_sample,
              int channel_data[])
{
    if (!setjmp(*br_try(r))) {
        subframe_type_t type;
        unsigned order;
        unsigned wasted_bps;
        status_t status;

        if ((status =
             read_subframe_header(r, &type, &order, &wasted_bps)) != OK) {
            br_etry(r);
            return status;
        } else {
            const unsigned effective_bps = bits_per_sample - wasted_bps;
            switch (type) {
            case CONSTANT:
                read_CONSTANT_subframe(r,
                                       block_size,
                                       effective_bps,
                                       channel_data);
                break;
            case VERBATIM:
                read_VERBATIM_subframe(r,
                                       block_size,
                                       effective_bps,
                                       channel_data);
                break;
            case FIXED:
                if ((status =
                     read_FIXED_subframe(r,
                                         block_size,
                                         effective_bps,
                                         order,
                                         channel_data)) != OK) {
                    return status;
                }
                break;
            case LPC:
                if ((status =
                     read_LPC_subframe(r,
                                       block_size,
                                       effective_bps,
                                       order,
                                       channel_data)) != OK) {
                    return status;
                }
                break;
            }
            br_etry(r);
            if (wasted_bps) {
                unsigned i;
                for (i = 0; i < block_size; i++) {
                    channel_data[i] <<= wasted_bps;
                }
            }
            return OK;
        }
    } else {
        br_etry(r);
        return IOERROR_SUBFRAME;
    }
}

static status_t
read_subframe_header(BitstreamReader *r,
                     subframe_type_t *type,
                     unsigned *order,
                     unsigned *wasted_bps)
{
    unsigned type_and_order;
    unsigned has_wasted_bps;

    r->skip(r, 1);
    type_and_order = r->read(r, 6);
    has_wasted_bps = r->read(r, 1);
    if (has_wasted_bps) {
        *wasted_bps = r->read_unary(r, 1) + 1;
    } else {
        *wasted_bps = 0;
    }
    if (type_and_order == 0) {
        *type = CONSTANT;
        return OK;
    } else if (type_and_order == 1) {
        *type = VERBATIM;
        return OK;
    } else if ((8 <= type_and_order) && (type_and_order <= 12)) {
        *type = FIXED;
        *order = type_and_order - 8;
        return OK;
    } else if ((32 <= type_and_order) && (type_and_order <= 63)) {
        *type = LPC;
        *order = type_and_order - 31;
        return OK;
    } else {
        return INVALID_SUBFRAME_HEADER;
    }
}

static void
read_CONSTANT_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[])
{
    const int constant = r->read_signed(r, bits_per_sample);
    for (; block_size; block_size--) {
        samples[0] = constant;
        samples += 1;
    }
}

static void
read_VERBATIM_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[])
{
    for (; block_size; block_size--) {
        samples[0] = r->read_signed(r, bits_per_sample);
        samples += 1;
    }
}

static status_t
read_FIXED_subframe(BitstreamReader *r,
                    unsigned block_size,
                    unsigned bits_per_sample,
                    unsigned predictor_order,
                    int samples[])
{
    if ((predictor_order > 4) || (predictor_order > block_size)) {
        return INVALID_FIXED_ORDER;
    } else {
        unsigned i;
        int residuals[block_size - predictor_order];
        status_t status;

        /*warm-up samples*/
        for (i = 0; i < predictor_order; i++) {
            samples[i] = r->read_signed(r, bits_per_sample);
        }

        /*residuals*/
        if ((status = read_residual_block(r,
                                          block_size,
                                          predictor_order,
                                          residuals)) != OK) {
            return status;
        }

        switch (predictor_order) {
        case 0:
            for (i = 0; i < block_size; i++) {
                samples[i] = residuals[i];
            }
            return OK;
        case 1:
            for (i = 1; i < block_size; i++) {
                samples[i] = samples[i - 1] + residuals[i - 1];
            }
            return OK;
        case 2:
            for (i = 2; i < block_size; i++) {
                samples[i] = (2 * samples[i - 1]) -
                             samples[i - 2] +
                             residuals[i - 2];
            }
            return OK;
        case 3:
            for (i = 3; i < block_size; i++) {
                samples[i] = (3 * samples[i - 1]) -
                             (3 * samples[i - 2]) +
                             samples[i - 3] +
                             residuals[i - 3];
            }
            return OK;
        case 4:
            for (i = 4; i < block_size; i++) {
                samples[i] = (4 * samples[i - 1]) -
                             (6 * samples[i - 2]) +
                             (4 * samples[i - 3]) -
                             samples[i - 4] +
                             residuals[i - 4];
            }
            return OK;
        default:
            return INVALID_FIXED_ORDER;
        }
    }
}

static status_t
read_LPC_subframe(BitstreamReader *r,
                  unsigned block_size,
                  unsigned bits_per_sample,
                  unsigned predictor_order,
                  int samples[])
{
    if (predictor_order >= block_size) {
        return INVALID_LPC_ORDER;
    } else {
        unsigned i;
        unsigned precision;
        int shift;
        int coefficient[predictor_order];
        int residuals[block_size - predictor_order];
        status_t status;

        /*warm-up samples*/
        for (i = 0; i < predictor_order; i++) {
            samples[i] = r->read_signed(r, bits_per_sample);
        }

        precision = r->read(r, 4) + 1;
        shift = r->read_signed(r, 5);
        if (shift < 0) {
            shift = 0;
        }

        /*coefficients*/
        for (i = 0; i < predictor_order; i++) {
            coefficient[i] = r->read_signed(r, precision);
        }

        if ((status = read_residual_block(r,
                                          block_size,
                                          predictor_order,
                                          residuals)) != OK) {
            return status;
        }

        for (i = predictor_order; i < block_size; i++) {
            int64_t sum = 0;
            unsigned j;
            for (j = 0; j < predictor_order; j++) {
                sum += (int64_t)coefficient[j] * (int64_t)samples[i - j - 1];
            }
            sum >>= shift;
            samples[i] = (int)sum + residuals[i - predictor_order];
        }

        return OK;
    }
}

static status_t
read_residual_block(BitstreamReader *r,
                    unsigned block_size,
                    unsigned predictor_order,
                    int residuals[])
{
    br_read_f read = r->read;
    br_read_unary_f read_unary = r->read_unary;
    const unsigned coding_method = r->read(r, 2);
    const unsigned partition_order = r->read(r, 4);
    const unsigned partition_count = 1 << partition_order;
    unsigned rice_bits;
    unsigned i = 0;
    unsigned p;

    if (coding_method == 0) {
        rice_bits = 4;
    } else if (coding_method == 1) {
        rice_bits = 5;
    } else {
        return INVALID_CODING_METHOD;
    }

    for (p = 0; p < partition_count; p++) {
        const unsigned rice = r->read(r, rice_bits);
        const unsigned partition_size = block_size / partition_count -
                                        (p == 0 ? predictor_order : 0);
        register unsigned j;
        if (((coding_method == 0) && (rice == 15)) ||
            ((coding_method == 1) && (rice == 31))) {
            const unsigned escape_code = read(r, 5);
            br_read_signed_f read_signed = r->read_signed;
            for (j = 0; j < partition_size; j++) {
                residuals[i++] = read_signed(r, escape_code);
            }
        } else {
            for (j = 0; j < partition_size; j++) {
                const unsigned MSB = read_unary(r, 1);
                const unsigned LSB = read(r, rice);
                const unsigned unsigned_ = (MSB << rice) | LSB;
                residuals[i++] = (unsigned_ % 2) ?
                                 (-(unsigned_ >> 1) - 1) :
                                 (unsigned_ >> 1);
            }
        }
    }

    return OK;
}

static void
decorrelate_left_difference(unsigned block_size,
                            const int left[],
                            const int difference[],
                            int right[])
{
    for (; block_size; block_size--) {
        right[0] = left[0] - difference[0];
        left += 1;
        right += 1;
        difference += 1;
    }
}

static void
decorrelate_difference_right(unsigned block_size,
                             const int difference[],
                             const int right[],
                             int left[])
{
    for (; block_size; block_size--) {
        left[0] = difference[0] + right[0];
        difference += 1;
        right += 1;
        left += 1;
    }
}

static void
decorrelate_average_difference(unsigned block_size,
                               const int average[],
                               const int difference[],
                               int left[],
                               int right[])
{
    for (; block_size; block_size--) {
        const int sum = (average[0] * 2) + (abs(difference[0]) % 2);
        left[0] = (sum + difference[0]) >> 1;
        right[0] = (sum - difference[0]) >> 1;
        average += 1;
        difference += 1;
        left += 1;
        right += 1;
    }
}

const char*
flac_strerror(status_t status)
{
    switch (status) {
    case OK:
        return "OK";
    default:
        return "undefined error";
    case INVALID_SYNC_CODE:
        return "invalid sync code in frame header";
    case INVALID_SAMPLE_RATE:
        return "invalid sample rate in frame header";
    case INVALID_BPS:
        return "invalid bits-per-sample in frame header";
    case INVALID_CHANNEL_ASSIGNMENT:
        return "invalid channel assignment in frame header";
    case INVALID_UTF8:
        return "invalid UTF-8 value in frame header";
    case INVALID_CRC8:
        return "invalid CRC-8 in frame header";
    case IOERROR_HEADER:
        return "I/O error reading frame header";
    case IOERROR_SUBFRAME:
        return "I/O error reading subframe data";
    case INVALID_SUBFRAME_HEADER:
        return "invalid subframe header";
    case INVALID_FIXED_ORDER:
        return "invalid FIXED subframe order";
    case INVALID_LPC_ORDER:
        return "invalid LPC subframe order";
    case INVALID_CODING_METHOD:
        return "invalid coding method";
    }
}

/*****************
 * main function *
 *****************/

#ifdef EXECUTABLE

#include <stdio.h>
#include <errno.h>

int main(int argc, char *argv[])
{
    FILE *file;
    BitstreamReader *reader;
    struct STREAMINFO streaminfo;
    int streaminfo_read = 0;
    unsigned remaining_frames = 0;

    if (argc < 2) {
        fprintf(stderr, "*** Usage : %s <file.flac>\n", argv[0]);
        return 1;
    }

    errno = 0;
    if ((file = fopen(argv[1], "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", argv[1], strerror(errno));
        return 1;
    }

    reader = br_open(file, BS_BIG_ENDIAN);

    if (!setjmp(*br_try(reader))) {
        unsigned last;
        unsigned type;
        unsigned size;

        /*check stream ID*/
        if (!valid_stream_id(reader)) {
            fputs("invalid stream ID\n", stderr);
            br_etry(reader);
            goto error;
        }

        /*parse metadata blocks*/
        do {
            read_block_header(reader, &last, &type, &size);

            switch (type) {
            case 0: /*STREAMINFO*/
                if (!streaminfo_read) {
                    read_STREAMINFO(reader, &streaminfo);
                    streaminfo_read = 1;
                } else {
                    fputs("multiple STREAMINFO blocks encountered\n", stderr);
                    br_etry(reader);
                    goto error;
                }
                break;
            case 1: /*PADDING*/
            case 2: /*APPLICATION*/
            case 3: /*SEEKTABLE*/
            case 4: /*VORBIS_COMMENT*/
            case 5: /*CUESHEET*/
            case 6: /*PICTURE*/
                reader->skip_bytes(reader, size);
                break;
            default:
                fprintf(stderr, "unknown block ID %u\n", type);
                br_etry(reader);
                goto error;
            }

        } while (last == 0);

        br_etry(reader);
    } else {
        br_etry(reader);
        fputs("I/O error reading stream\n", stderr);
        goto error;
    }

    if (streaminfo_read) {
        remaining_frames = streaminfo.total_samples;
    } else {
        fputs("no STREAMINFO block found\n", stderr);
        goto error;
    }

    /*decode frames*/
    while (remaining_frames) {
        struct frame_header frame_header;
        uint16_t crc16 = 0;
        status_t status;

        reader->add_callback(reader, (bs_callback_f)flac_crc16, &crc16);

        if ((status =
             read_frame_header(reader, &streaminfo, &frame_header)) != OK) {
            fputs(flac_strerror(status), stderr);
            goto error;
        } else {
            int pcm_data[frame_header.block_size *
                         frame_header.channel_count];
            const unsigned buffer_size = frame_header.bits_per_sample / 8;
            unsigned char buffer[buffer_size];
            int_to_pcm_f converter =
                int_to_pcm_converter(frame_header.bits_per_sample, 0, 1);
            unsigned i;

            if (frame_header.channel_assignment == INDEPENDENT) {
                unsigned c;

                for (c = 0; c < frame_header.channel_count; c++) {
                    int channel_data[frame_header.block_size];
                    if ((status =
                         read_subframe(reader,
                                       frame_header.block_size,
                                       frame_header.bits_per_sample,
                                       channel_data)) != OK) {
                        fputs(flac_strerror(status), stderr);
                        goto error;
                    } else {
                        put_channel_data(pcm_data,
                                         c,
                                         frame_header.channel_count,
                                         frame_header.block_size,
                                         channel_data);
                    }
                }
            } else if (frame_header.channel_assignment == LEFT_DIFFERENCE) {
                int left_data[frame_header.block_size];
                int difference_data[frame_header.block_size];
                int right_data[frame_header.block_size];

                if ((status = read_subframe(reader,
                                            frame_header.block_size,
                                            frame_header.bits_per_sample,
                                            left_data)) != OK) {
                    fputs(flac_strerror(status), stderr);
                    goto error;
                }
                if ((status = read_subframe(reader,
                                            frame_header.block_size,
                                            frame_header.bits_per_sample + 1,
                                            difference_data)) != OK) {
                    fputs(flac_strerror(status), stderr);
                    goto error;
                }

                decorrelate_left_difference(frame_header.block_size,
                                            left_data,
                                            difference_data,
                                            right_data);

                put_channel_data(pcm_data,
                                 0,
                                 2,
                                 frame_header.block_size,
                                 left_data);
                put_channel_data(pcm_data,
                                 1,
                                 2,
                                 frame_header.block_size,
                                 right_data);
            } else if (frame_header.channel_assignment == DIFFERENCE_RIGHT) {
                int difference_data[frame_header.block_size];
                int right_data[frame_header.block_size];
                int left_data[frame_header.block_size];

                if ((status = read_subframe(reader,
                                            frame_header.block_size,
                                            frame_header.bits_per_sample + 1,
                                            difference_data)) != OK) {
                    fputs(flac_strerror(status), stderr);
                    goto error;
                }
                if ((status = read_subframe(reader,
                                            frame_header.block_size,
                                            frame_header.bits_per_sample,
                                            right_data)) != OK) {
                    fputs(flac_strerror(status), stderr);
                    goto error;
                }

                decorrelate_difference_right(frame_header.block_size,
                                             difference_data,
                                             right_data,
                                             left_data);

                put_channel_data(pcm_data,
                                 0,
                                 2,
                                 frame_header.block_size,
                                 left_data);
                put_channel_data(pcm_data,
                                 1,
                                 2,
                                 frame_header.block_size,
                                 right_data);
            } else {
                int average_data[frame_header.block_size];
                int difference_data[frame_header.block_size];
                int right_data[frame_header.block_size];
                int left_data[frame_header.block_size];

                if ((status = read_subframe(reader,
                                            frame_header.block_size,
                                            frame_header.bits_per_sample,
                                            average_data)) != OK) {
                    fputs(flac_strerror(status), stderr);
                    goto error;
                }
                if ((status = read_subframe(reader,
                                            frame_header.block_size,
                                            frame_header.bits_per_sample + 1,
                                            difference_data)) != OK) {
                    fputs(flac_strerror(status), stderr);
                    goto error;
                }

                decorrelate_average_difference(frame_header.block_size,
                                               average_data,
                                               difference_data,
                                               left_data,
                                               right_data);

                put_channel_data(pcm_data,
                                 0,
                                 2,
                                 frame_header.block_size,
                                 left_data);
                put_channel_data(pcm_data,
                                 1,
                                 2,
                                 frame_header.block_size,
                                 right_data);
            }

            if (!setjmp(*br_try(reader))) {
                reader->byte_align(reader);
                reader->skip(reader, 16); /*CRC-16*/
                br_etry(reader);
            } else {
                br_etry(reader);
                fputs("I/O error reading CRC-16", stderr);
                goto error;
            }
            reader->pop_callback(reader, NULL);
            if (crc16) {
                fputs("invalid frame CRC-16", stderr);
                goto error;
            }

            for (i = 0;
                 i < frame_header.block_size * frame_header.channel_count;
                 i++) {
                converter(pcm_data[i], buffer);
                fwrite(buffer, sizeof(unsigned char), buffer_size, stdout);
            }

            remaining_frames -= frame_header.block_size;
        }
    }

    /*ensure MD5 sum matches that of STREAMINFO, if STREAMINFO's sum is set*/
    /*FIXME*/

    reader->close(reader);
    return 0;
error:
    reader->close(reader);
    return 1;
}

#endif
