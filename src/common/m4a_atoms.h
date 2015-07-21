#include <stdint.h>
#include <stdarg.h>
#include <time.h>
#include "../bitstream.h"

typedef enum {
  QT_LEAF,
  QT_TREE,
  QT_FTYP,
  QT_MVHD,
  QT_TKHD,
  QT_MDHD,
  QT_HDLR,
  QT_SMHD,
  QT_DREF,
  QT_STSD,
  QT_ALAC,
  QT_STTS,
  QT_STSC,
  QT_STSZ,
  QT_STCO,
  QT_FREE
} qt_atom_type_t;

struct qt_atom_list;
struct stts_time;
struct stsc_entry;

struct qt_atom {
    uint8_t name[4];

    qt_atom_type_t type;

    union {
        struct {
            unsigned data_size;
            uint8_t *data;
        } leaf;

        struct qt_atom_list *tree;

        struct {
            uint8_t major_brand[4];
            unsigned major_brand_version;
            unsigned compatible_brand_count;
            uint8_t **compatible_brands;
        } ftyp;

        struct {
            int version;
            time_t timestamp;
            unsigned sample_rate;
            unsigned total_pcm_frames;
        } mvhd;

        struct {
            int version;
            time_t timestamp;
            unsigned total_pcm_frames;
        } tkhd;

        struct {
            int version;
            time_t timestamp;
            unsigned sample_rate;
            unsigned total_pcm_frames;
        } mdhd;

        struct {
            unsigned component_name_length;
            uint8_t *component_name;
        } hdlr;

        struct qt_atom_list *dref;

        struct qt_atom_list *stsd;

        struct {
            unsigned max_samples_per_frame;
            unsigned bits_per_sample;
            unsigned history_multiplier;
            unsigned initial_history;
            unsigned maximum_K;
            unsigned channels;
            unsigned max_coded_frame_size;
            unsigned bitrate;
            unsigned sample_rate;
        } alac;

        struct {
            unsigned times_count;
            struct stts_time *times;
        } stts;

        struct {
            unsigned entries_count;
            struct stsc_entry *entries;
        } stsc;

        struct {
            unsigned frames_count;
            unsigned *frame_size;
        } stsz;

        struct {
            unsigned offsets_count;
            unsigned *chunk_offset;
        } stco;

        unsigned free;
    } _;

    /*prints a user-readable version of the atom to the given stream
      and at the given indentation level*/
    void (*display)(const struct qt_atom *self,
                    unsigned indent,
                    FILE *output);

    /*outputs atom to the given stream, including its 8 byte header*/
    void (*build)(const struct qt_atom *self,
                  BitstreamWriter *stream);

    /*returns the size of the atom in bytes, including its 8 byte header*/
    unsigned (*size)(const struct qt_atom *self);

    /*deallocates atom and any sub-atoms*/
    void (*free)(struct qt_atom *self);
};

struct qt_atom_list {
    struct qt_atom *atom;
    struct qt_atom_list *next;
};

struct stts_time {
    unsigned occurences;
    unsigned pcm_frame_count;
};

struct stsc_entry {
    unsigned first_chunk;
    unsigned frames_per_chunk;
    unsigned description_index;
};

struct qt_atom*
qt_leaf_new(const char name[4],
            unsigned data_size,
            const uint8_t data[]);

/*constructs atom from sub-atoms
  references to the sub-atoms are "stolen" from argument list
  and are deallocated when the container is deallocated*/
struct qt_atom*
qt_tree_new(const char name[4],
            unsigned sub_atoms,
            ...);

struct qt_atom*
qt_ftyp_new(const uint8_t major_brand[4],
            unsigned major_brand_version,
            unsigned compatible_brand_count,
            ...);

struct qt_atom*
qt_mvhd_new(int version,
            time_t timestamp,
            unsigned sample_rate,
            unsigned total_pcm_frames);

struct qt_atom*
qt_tkhd_new(int version,
            time_t timestamp,
            unsigned total_pcm_frames);

struct qt_atom*
qt_mdhd_new(int version,
            time_t timestamp,
            unsigned sample_rate,
            unsigned total_pcm_frames);

struct qt_atom*
qt_hdlr_new(unsigned component_name_length,
            const uint8_t component_name[]);

struct qt_atom*
qt_smhd_new(void);

struct qt_atom*
qt_dref_new(unsigned reference_atom_count, ...);

struct qt_atom*
qt_stsd_new(unsigned description_atom_count, ...);

struct qt_atom*
qt_alac_new(unsigned max_samples_per_frame,
            unsigned bits_per_sample,
            unsigned history_multiplier,
            unsigned initial_history,
            unsigned maximum_K,
            unsigned channels,
            unsigned max_coded_frame_size,
            unsigned bitrate,
            unsigned sample_rate);

/*for each "times_count", there is both a frame_count and frame_duration
  unsigned value which populates the atom*/
struct qt_atom*
qt_stts_new(unsigned times_count, ...);

/*for each "entries_count" there is both a first_chunk and frames_per_chunk
  unsigned value which populates the atom*/
struct qt_atom*
qt_stsc_new(unsigned entries_count, ...);

/*generates a stsz atom whose frame sizes are all initialized at 0
  one is expected to update them with actual values once
  encoding is finished*/
struct qt_atom*
qt_stsz_new(unsigned frames_count);

/*generates a stco atom whose chunk offsets are all initialized at 0
  one is expected to update them with actual values once
  encoding is finished*/
struct qt_atom*
qt_stco_new(unsigned chunk_offsets);

struct qt_atom*
qt_free_new(unsigned padding_bytes);
