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
  QT_FREE
} qt_atom_type_t;

struct qt_atom_list;

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
qt_dref_new(unsigned reference_atom_count,
            ...);

struct qt_atom*
qt_free_new(unsigned padding_bytes);
