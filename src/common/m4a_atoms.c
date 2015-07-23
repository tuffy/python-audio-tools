#include "m4a_atoms.h"
#include <string.h>
#include <ctype.h>
#include <assert.h>

/*stream is a big-endian BitstreamReader
  atom_size is the size of the atom, *not including its 8 byte header!*
  atom_name is the atom's name*/
typedef struct qt_atom* (*atom_parser_f)(BitstreamReader *stream,
                                         unsigned atom_size,
                                         const char atom_name[4]);

/******************************/
/*private function definitions*/
/******************************/

#define ATOM_DEF(NAME)                                     \
  static void display_##NAME(const struct qt_atom *self,   \
                             unsigned indent,              \
                             FILE *output);                \
                                                           \
  static void build_##NAME(const struct qt_atom *self,     \
                           BitstreamWriter *stream);       \
                                                           \
  static unsigned size_##NAME(const struct qt_atom *self); \
                                                           \
  static void free_##NAME(struct qt_atom *self);           \
                                                           \
  static struct qt_atom*                                   \
  parse_##NAME(BitstreamReader *stream,                    \
               unsigned atom_size,                         \
               const char atom_name[4]);
ATOM_DEF(leaf)
ATOM_DEF(tree)
ATOM_DEF(ftyp)
ATOM_DEF(mvhd)
ATOM_DEF(tkhd)
ATOM_DEF(mdhd)
ATOM_DEF(hdlr)
ATOM_DEF(smhd)
ATOM_DEF(dref)
ATOM_DEF(stsd)
ATOM_DEF(alac)
ATOM_DEF(sub_alac)
ATOM_DEF(stts)
ATOM_DEF(stsc)
ATOM_DEF(stsz)
ATOM_DEF(stco)
ATOM_DEF(meta)
ATOM_DEF(data)
ATOM_DEF(free)

static void
build_header(const struct qt_atom *self, BitstreamWriter *stream);

static void
display_indent(unsigned indent, FILE *output);

static inline void
set_atom_name(struct qt_atom *atom, const char name[4])
{
    atom->name[0] = (uint8_t)name[0];
    atom->name[1] = (uint8_t)name[1];
    atom->name[2] = (uint8_t)name[2];
    atom->name[3] = (uint8_t)name[3];
}

static void
display_name(const uint8_t name[], FILE *output);

static struct qt_atom_list*
atom_list_append(struct qt_atom_list *head, struct qt_atom *atom);

static unsigned
atom_list_len(struct qt_atom_list *head);

static void
atom_list_free(struct qt_atom_list *head);

static unsigned
time_to_mac_utc(time_t time);

static uint64_t
time_to_mac_utc64(time_t time);

static atom_parser_f
atom_parser(const char *atom_name);

static void
add_ftyp_brand(struct qt_atom *atom, const uint8_t compatible_brand[4]);

typedef enum {
    A_INT,
    A_UNSIGNED,
    A_UINT64,
    A_ARRAY_UNSIGNED,
    A_ARRAY_CHAR,
    A_STRING
} field_type_t;

/*for each "field_count" there are 3 arguments:
  char* field_label
  field_type_t type
  and some value

  unless "type" is one of the arrays, in which case there are 4 arguments:
  char* field_label
  field_type_t type
  unsigned length
  and an array of values of that length*/
static void
display_fields(unsigned indent,
               FILE *output,
               const uint8_t atom_name[4],
               unsigned field_count,
               ...);

/*********************************/
/*public function implementations*/
/*********************************/

struct qt_atom*
qt_leaf_new(const char name[4],
            unsigned data_size,
            const uint8_t data[])
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, name);
    atom->type = QT_LEAF;
    atom->_.leaf.data_size = data_size;
    atom->_.leaf.data = malloc(data_size);
    memcpy(atom->_.leaf.data, data, data_size);
    atom->display = display_leaf;
    atom->build = build_leaf;
    atom->size = size_leaf;
    atom->free = free_leaf;
    return atom;
}

struct qt_atom*
qt_tree_new(const char name[4],
            unsigned sub_atoms,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, name);
    atom->type = QT_TREE;
    atom->_.tree = NULL;

    va_start(ap, sub_atoms);
    for (; sub_atoms; sub_atoms--) {
        struct qt_atom *sub_atom = va_arg(ap, struct qt_atom*);
        atom->_.tree = atom_list_append(atom->_.tree, sub_atom);
    }
    va_end(ap);

    atom->display = display_tree;
    atom->build = build_tree;
    atom->size = size_tree;
    atom->free = free_tree;
    return atom;
}

struct qt_atom*
qt_ftyp_new(const uint8_t major_brand[4],
            unsigned major_brand_version,
            unsigned compatible_brand_count,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, "ftyp");
    atom->type = QT_FTYP;
    memcpy(atom->_.ftyp.major_brand, major_brand, 4);
    atom->_.ftyp.major_brand_version = major_brand_version;
    atom->_.ftyp.compatible_brand_count = 0;
    atom->_.ftyp.compatible_brands = NULL;
    va_start(ap, compatible_brand_count);
    for (; compatible_brand_count; compatible_brand_count--) {
        uint8_t *brand = va_arg(ap, uint8_t*);
        add_ftyp_brand(atom, brand);
    }
    va_end(ap);
    atom->display = display_ftyp;
    atom->build = build_ftyp;
    atom->size = size_ftyp;
    atom->free = free_ftyp;
    return atom;
}

struct qt_atom*
qt_free_new(unsigned padding_bytes)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));

    set_atom_name(atom, "free");
    atom->type = QT_FREE;
    atom->_.free = padding_bytes;
    atom->display = display_free;
    atom->build = build_free;
    atom->size = size_free;
    atom->free = free_free;
    return atom;
}

struct qt_atom*
qt_mvhd_new(unsigned version,
            unsigned flags,
            qt_time_t created_date,
            qt_time_t modified_date,
            unsigned time_scale,
            qt_time_t duration,
            unsigned playback_speed,
            unsigned user_volume,
            const unsigned geometry[9],
            uint64_t preview,
            unsigned poster,
            uint64_t qt_selection_time,
            unsigned qt_current_time,
            unsigned next_track_id)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "mvhd");
    atom->type = QT_MVHD;
    atom->_.mvhd.version = version;
    atom->_.mvhd.flags = flags;
    atom->_.mvhd.created_date = created_date;
    atom->_.mvhd.modified_date = modified_date;
    atom->_.mvhd.time_scale = time_scale;
    atom->_.mvhd.duration = duration;
    atom->_.mvhd.playback_speed = playback_speed;
    atom->_.mvhd.user_volume = user_volume;
    memcpy(atom->_.mvhd.geometry, geometry, 9 * sizeof(unsigned));
    atom->_.mvhd.preview = preview;
    atom->_.mvhd.poster = poster;
    atom->_.mvhd.qt_selection_time = qt_selection_time;
    atom->_.mvhd.qt_current_time = qt_current_time;
    atom->_.mvhd.next_track_id = next_track_id;
    atom->display = display_mvhd;
    atom->build = build_mvhd;
    atom->size = size_mvhd;
    atom->free = free_mvhd;
    return atom;
}

struct qt_atom*
qt_tkhd_new(unsigned version,
            unsigned flags,
            qt_time_t created_date,
            qt_time_t modified_date,
            unsigned track_id,
            qt_time_t duration,
            unsigned layer,
            unsigned qt_alternate,
            unsigned volume,
            const unsigned geometry[9],
            unsigned video_width,
            unsigned video_height)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "tkhd");
    atom->type = QT_TKHD;
    atom->_.tkhd.version = version;
    atom->_.tkhd.flags = flags;
    atom->_.tkhd.created_date = created_date;
    atom->_.tkhd.modified_date = modified_date;
    atom->_.tkhd.track_id = track_id;
    atom->_.tkhd.duration = duration;
    atom->_.tkhd.layer = layer;
    atom->_.tkhd.qt_alternate = qt_alternate;
    atom->_.tkhd.volume = volume;
    memcpy(atom->_.tkhd.geometry, geometry, 9 * sizeof(unsigned));
    atom->_.tkhd.video_width = video_width;
    atom->_.tkhd.video_height = video_height;
    atom->display = display_tkhd;
    atom->build = build_tkhd;
    atom->size = size_tkhd;
    atom->free = free_tkhd;
    return atom;
}

struct qt_atom*
qt_mdhd_new(unsigned version,
            unsigned flags,
            qt_time_t created_date,
            qt_time_t modified_date,
            unsigned time_scale,
            qt_time_t duration,
            const char language[3],
            unsigned quality)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "mdhd");
    atom->type = QT_MDHD;
    atom->_.mdhd.version = version;
    atom->_.mdhd.flags = flags;
    atom->_.mdhd.created_date = created_date;
    atom->_.mdhd.modified_date = modified_date;
    atom->_.mdhd.time_scale = time_scale;
    atom->_.mdhd.duration = duration;
    memcpy(atom->_.mdhd.language, language, 3 * sizeof(char));
    atom->_.mdhd.quality = quality;
    atom->display = display_mdhd;
    atom->build = build_mdhd;
    atom->size = size_mdhd;
    atom->free = free_mdhd;
    return atom;
}

struct qt_atom*
qt_hdlr_new(unsigned version,
            unsigned flags,
            const char qt_type[4],
            const char qt_subtype[4],
            const char qt_manufacturer[4],
            unsigned qt_flags,
            unsigned qt_flags_mask,
            unsigned component_name_length,
            const char component_name[],
            unsigned padding)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "hdlr");
    atom->type = QT_HDLR;
    atom->_.hdlr.version = version;
    atom->_.hdlr.flags = flags;
    memcpy(atom->_.hdlr.qt_type, qt_type, 4);
    memcpy(atom->_.hdlr.qt_subtype, qt_subtype, 4);
    memcpy(atom->_.hdlr.qt_manufacturer, qt_manufacturer, 4);
    atom->_.hdlr.qt_flags = qt_flags;
    atom->_.hdlr.qt_flags_mask = qt_flags_mask;
    atom->_.hdlr.component_name_length = component_name_length;
    atom->_.hdlr.component_name = malloc(component_name_length);
    memcpy(atom->_.hdlr.component_name,
           component_name,
           component_name_length);
    atom->_.hdlr.padding = padding;
    atom->display = display_hdlr;
    atom->build = build_hdlr;
    atom->size = size_hdlr;
    atom->free = free_hdlr;
    return atom;
}

struct qt_atom*
qt_smhd_new(unsigned version,
            unsigned flags,
            unsigned balance)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "smhd");
    atom->type = QT_SMHD;
    atom->_.smhd.version = version;
    atom->_.smhd.flags = flags;
    atom->_.smhd.balance = balance;
    atom->display = display_smhd;
    atom->build = build_smhd;
    atom->size = size_smhd;
    atom->free = free_smhd;
    return atom;
}

struct qt_atom*
qt_dref_new(unsigned version,
            unsigned flags,
            unsigned reference_atom_count,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, "dref");
    atom->type = QT_DREF;
    atom->_.dref.version = version;
    atom->_.dref.flags = flags;
    atom->_.dref.references = NULL;

    va_start(ap, reference_atom_count);
    for (; reference_atom_count; reference_atom_count--) {
        struct qt_atom *reference_atom = va_arg(ap, struct qt_atom*);
        atom->_.dref.references =
            atom_list_append(atom->_.dref.references, reference_atom);
    }
    va_end(ap);

    atom->display = display_dref;
    atom->build = build_dref;
    atom->size = size_dref;
    atom->free = free_dref;

    return atom;
}

struct qt_atom*
qt_stsd_new(unsigned version,
            unsigned flags,
            unsigned description_atom_count,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, "stsd");
    atom->type = QT_STSD;
    atom->_.stsd.version = version;
    atom->_.stsd.flags = flags;
    atom->_.stsd.descriptions = NULL;

    va_start(ap, description_atom_count);
    for (; description_atom_count; description_atom_count--) {
        struct qt_atom *description_atom = va_arg(ap, struct qt_atom*);
        atom->_.stsd.descriptions =
            atom_list_append(atom->_.stsd.descriptions, description_atom);
    }
    va_end(ap);

    atom->display = display_stsd;
    atom->build = build_stsd;
    atom->size = size_stsd;
    atom->free = free_stsd;

    return atom;
}

struct qt_atom*
qt_alac_new(unsigned reference_index,
            unsigned version,
            unsigned revision_level,
            uint8_t vendor[4],
            unsigned channels,
            unsigned bits_per_sample,
            unsigned compression_id,
            unsigned audio_packet_size,
            unsigned sample_rate,
            struct qt_atom *sub_alac)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "alac");
    atom->type = QT_ALAC;
    atom->_.alac.reference_index = reference_index;
    atom->_.alac.version = version;
    atom->_.alac.revision_level = revision_level;
    memcpy(atom->_.alac.vendor, vendor, 4);
    atom->_.alac.channels = channels;
    atom->_.alac.bits_per_sample = bits_per_sample;
    atom->_.alac.compression_id = compression_id;
    atom->_.alac.audio_packet_size = audio_packet_size;
    atom->_.alac.sample_rate = sample_rate;
    atom->_.alac.sub_alac = sub_alac;
    atom->display = display_alac;
    atom->build = build_alac;
    atom->size = size_alac;
    atom->free = free_alac;
    return atom;
}

struct qt_atom*
qt_sub_alac_new(unsigned max_samples_per_frame,
                unsigned bits_per_sample,
                unsigned history_multiplier,
                unsigned initial_history,
                unsigned maximum_K,
                unsigned channels,
                unsigned unknown,
                unsigned max_coded_frame_size,
                unsigned bitrate,
                unsigned sample_rate)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "alac");
    atom->type = QT_SUB_ALAC;
    atom->_.sub_alac.max_samples_per_frame = max_samples_per_frame;
    atom->_.sub_alac.bits_per_sample = bits_per_sample;
    atom->_.sub_alac.history_multiplier = history_multiplier;
    atom->_.sub_alac.initial_history = initial_history;
    atom->_.sub_alac.maximum_K = maximum_K;
    atom->_.sub_alac.channels = channels;
    atom->_.sub_alac.unknown = unknown;
    atom->_.sub_alac.max_coded_frame_size = max_coded_frame_size;
    atom->_.sub_alac.bitrate = bitrate;
    atom->_.sub_alac.sample_rate = sample_rate;
    atom->display = display_sub_alac;
    atom->build = build_sub_alac;
    atom->size = size_sub_alac;
    atom->free = free_sub_alac;
    return atom;
}

struct qt_atom*
qt_stts_new(unsigned version,
            unsigned flags,
            unsigned times_count,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    unsigned i;
    va_list ap;

    set_atom_name(atom, "stts");
    atom->type = QT_STTS;
    atom->_.stts.version = version;
    atom->_.stts.flags = flags;
    atom->_.stts.times_count = times_count;
    atom->_.stts.times = malloc(times_count * sizeof(struct stts_time));

    va_start(ap, times_count);
    for (i = 0; i < times_count; i++) {
        atom->_.stts.times[i].occurences = va_arg(ap, unsigned);
        atom->_.stts.times[i].pcm_frame_count = va_arg(ap, unsigned);
    }
    va_end(ap);

    atom->display = display_stts;
    atom->build = build_stts;
    atom->size = size_stts;
    atom->free = free_stts;
    return atom;
}

struct qt_atom*
qt_stsc_new(unsigned version,
            unsigned flags,
            unsigned entries_count,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    unsigned i;
    va_list ap;

    set_atom_name(atom, "stsc");
    atom->type = QT_STSC;
    atom->_.stsc.version = version;
    atom->_.stsc.flags = flags;
    atom->_.stsc.entries_count = entries_count;
    atom->_.stsc.entries = malloc(entries_count * sizeof(struct stsc_entry));

    va_start(ap, entries_count);
    for (i = 0; i < entries_count; i++) {
        atom->_.stsc.entries[i].first_chunk = va_arg(ap, unsigned);
        atom->_.stsc.entries[i].frames_per_chunk = va_arg(ap, unsigned);
        atom->_.stsc.entries[i].description_index = 1;
    }
    va_end(ap);

    atom->display = display_stsc;
    atom->build = build_stsc;
    atom->size = size_stsc;
    atom->free = free_stsc;
    return atom;
}

struct qt_atom*
qt_stsz_new(unsigned version,
            unsigned flags,
            unsigned frame_byte_size,
            unsigned frames_count)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "stsz");
    atom->type = QT_STSZ;
    atom->_.stsz.version = version;
    atom->_.stsz.flags = flags;
    atom->_.stsz.frame_byte_size = frame_byte_size;
    atom->_.stsz.frames_count = frames_count;
    atom->_.stsz.frame_size = calloc(frames_count, sizeof(unsigned));
    atom->display = display_stsz;
    atom->build = build_stsz;
    atom->size = size_stsz;
    atom->free = free_stsz;
    return atom;
}

struct qt_atom*
qt_stco_new(unsigned version,
            unsigned flags,
            unsigned chunk_offsets)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "stco");
    atom->type = QT_STCO;
    atom->_.stco.version = version;
    atom->_.stco.flags = flags;
    atom->_.stco.offsets_count = chunk_offsets;
    atom->_.stco.chunk_offset = calloc(chunk_offsets, sizeof(unsigned));
    atom->display = display_stco;
    atom->build = build_stco;
    atom->size = size_stco;
    atom->free = free_stco;
    return atom;
}

struct qt_atom*
qt_meta_new(unsigned version,
            unsigned flags,
            unsigned sub_atom_count,
            ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, "meta");
    atom->type = QT_META;
    atom->_.meta.version = version;
    atom->_.meta.flags = flags;
    atom->_.meta.sub_atoms = NULL;

    va_start(ap, sub_atom_count);
    for (; sub_atom_count; sub_atom_count--) {
        struct qt_atom *sub_atom = va_arg(ap, struct qt_atom*);
        atom->_.meta.sub_atoms =
            atom_list_append(atom->_.meta.sub_atoms, sub_atom);
    }
    va_end(ap);

    atom->display = display_meta;
    atom->build = build_meta;
    atom->size = size_meta;
    atom->free = free_meta;
    return atom;
}

struct qt_atom*
qt_data_new(unsigned type, unsigned data_size, const uint8_t data[])
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "data");
    atom->type = QT_DATA;
    atom->_.data.type = type;
    atom->_.data.data_size = data_size;
    atom->_.data.data = malloc(data_size);
    memcpy(atom->_.data.data, data, data_size);
    atom->display = display_data;
    atom->build = build_data;
    atom->size = size_data;
    atom->free = free_data;
    return atom;
}

struct qt_atom*
qt_atom_parse(BitstreamReader *reader)
{
    unsigned atom_size;
    uint8_t atom_name[4];
    struct qt_atom *atom;

    /*grab the 8 byte atom header*/
    atom_size = reader->read(reader, 32);
    reader->read_bytes(reader, atom_name, 4);

    assert(atom_size >= 8);

    /*use appropriate parser for atom based on its name*/
    atom = atom_parser((char*)atom_name)(reader,
                                         atom_size - 8,
                                         (char*)atom_name);

#ifndef NDEBUG
    if (atom->size(atom) != atom_size) {
        fputs("size mismatch for atom \"", stderr);
        display_name(atom_name, stderr);
        fprintf(stderr, "\" : %u bytes in header, %u bytes calculated size\n",
                atom_size, atom->size(atom));
        assert(0);
    }
#endif

    assert(atom->size(atom) == atom_size);

    return atom;
}

/**********************************/
/*private function implementations*/
/**********************************/

static void
build_header(const struct qt_atom *self, BitstreamWriter *stream)
{
    stream->write(stream, 32, self->size(self));
    stream->write_bytes(stream, self->name, 4);
}

static void
display_indent(unsigned indent, FILE *output)
{
    for (; indent; indent--) {
        fputs("  ", output);
    }
}

static void
display_name(const uint8_t name[], FILE *output)
{
    unsigned i;
    for (i = 0; i < 4; i++) {
        if (isprint(name[i])) {
            fputc(name[i], output);
        } else {
            fprintf(output, "\\x%2.2X", name[i]);
        }
    }
}

static struct qt_atom_list*
atom_list_append(struct qt_atom_list *head, struct qt_atom *atom)
{
    if (head) {
        head->next = atom_list_append(head->next, atom);
        return head;
    } else {
        struct qt_atom_list *list = malloc(sizeof(struct qt_atom_list));
        list->atom = atom;
        list->next = NULL;
        return list;
    }
}

static unsigned
atom_list_len(struct qt_atom_list *head)
{
    if (head) {
        return 1 + atom_list_len(head->next);
    } else {
        return 0;
    }
}

static void
atom_list_free(struct qt_atom_list *head)
{
    if (head) {
        atom_list_free(head->next);
        head->atom->free(head->atom);
        free(head);
    }
}

static unsigned
time_to_mac_utc(time_t time)
{
    /*seconds since the Mac epoch, which is Jan 1st, 1904, 00:00:00*/
    struct tm epoch = {0};

    epoch.tm_year = 4;
    epoch.tm_mon = 0;
    epoch.tm_mday = 1;

    return (unsigned)difftime(time, timegm(&epoch));
}

static uint64_t
time_to_mac_utc64(time_t time)
{
    /*seconds since the Mac epoch, which is Jan 1st, 1904, 00:00:00*/
    struct tm epoch = {0};

    epoch.tm_year = 4;
    epoch.tm_mon = 0;
    epoch.tm_mday = 1;

    return (uint64_t)difftime(time, timegm(&epoch));
}

/*** leaf ***/

static void
display_leaf(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %u bytes\n", self->_.leaf.data_size);
}

static struct qt_atom*
parse_leaf(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    struct qt_atom *atom;
    /*FIXME - avoid allocating the whole world*/
    uint8_t *data = malloc(atom_size);
    stream->read_bytes(stream, data, atom_size);
    atom = qt_leaf_new(atom_name, atom_size, data);
    free(data);
    return atom;
}

static void
build_leaf(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write_bytes(stream, self->_.leaf.data, self->_.leaf.data_size);
}

static unsigned
size_leaf(const struct qt_atom *self)
{
    return 8 + self->_.leaf.data_size;
}

static void
free_leaf(struct qt_atom *self)
{
    free(self->_.leaf.data);
    free(self);
}

/*** tree ***/

static void
display_tree(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    struct qt_atom_list *list;
    display_indent(indent, output);
    display_name(self->name, output);
    fputs("\n", output);
    for (list = self->_.tree; list; list = list->next) {
        list->atom->display(list->atom, indent + 1, output);
    }
}

static struct qt_atom*
parse_tree(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    struct qt_atom *atom = qt_tree_new(atom_name, 0);

    while (atom_size) {
        struct qt_atom *sub_atom = qt_atom_parse(stream);
        atom->_.tree = atom_list_append(atom->_.tree, sub_atom);
        atom_size -= sub_atom->size(sub_atom);
    }

    return atom;
}

static void
build_tree(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    struct qt_atom_list *list;
    build_header(self, stream);
    for (list = self->_.tree; list; list = list->next) {
        list->atom->build(list->atom, stream);
    }
}

static unsigned
size_tree(const struct qt_atom *self)
{
    unsigned size = 8; /*include header*/
    struct qt_atom_list *list;
    for (list = self->_.tree; list; list = list->next) {
        size += list->atom->size(list->atom);
    }
    return size;
}

static void
free_tree(struct qt_atom *self)
{
    atom_list_free(self->_.tree);
    free(self);
}

/*** ftyp ***/

static void
display_ftyp(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    unsigned i;

    display_indent(indent, output);
    display_name(self->name, output);
    fputs(" - \"", output);
    display_name(self->_.ftyp.major_brand, output);
    fputs("\"", output);
    fprintf(output, " %u ", self->_.ftyp.major_brand_version);
    for (i = 0; i < self->_.ftyp.compatible_brand_count; i++) {
        fputs("\"", output);
        display_name(self->_.ftyp.compatible_brands[i], output);
        fputs("\"", output);
        if ((i + 1) < self->_.ftyp.compatible_brand_count) {
            fputs(", ", output);
        } else {
            fputs("\n", output);
        }
    }
}

static struct qt_atom*
parse_ftyp(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    struct qt_atom *atom;
    uint8_t major_brand[4];
    unsigned major_brand_version;

    stream->read_bytes(stream, major_brand, 4);
    major_brand_version = stream->read(stream, 32);
    atom = qt_ftyp_new(major_brand, major_brand_version, 0);
    atom_size -= 8;

    while (atom_size) {
        uint8_t compatible_brand[4];
        stream->read_bytes(stream, compatible_brand, 4);
        atom_size -= 4;
        add_ftyp_brand(atom, compatible_brand);
    }

    return atom;
}

static void
build_ftyp(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write_bytes(stream, self->_.ftyp.major_brand, 4);
    stream->write(stream, 32, self->_.ftyp.major_brand_version);
    for (i = 0; i < self->_.ftyp.compatible_brand_count; i++) {
        stream->write_bytes(stream, self->_.ftyp.compatible_brands[i], 4);
    }
}

static unsigned
size_ftyp(const struct qt_atom *self)
{
    return 8 + 8 + 4 * self->_.ftyp.compatible_brand_count;
}

static void
free_ftyp(struct qt_atom *self)
{
    unsigned i;
    for (i = 0; i < self->_.ftyp.compatible_brand_count; i++) {
        free(self->_.ftyp.compatible_brands[i]);
    }
    free(self->_.ftyp.compatible_brands);
    free(self);
}

/*** mvhd ***/

static void
display_mvhd(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_fields(
        indent, output, self->name, 13,
        "version",           A_UNSIGNED, self->_.mvhd.version,
        "flags",             A_UNSIGNED, self->_.mvhd.flags,
        "created date",      A_UINT64,   self->_.mvhd.created_date,
        "modified date",     A_UINT64,   self->_.mvhd.modified_date,
        "time scale",        A_UNSIGNED, self->_.mvhd.time_scale,
        "duration",          A_UINT64,   self->_.mvhd.duration,
        "playback speed",    A_UNSIGNED, self->_.mvhd.playback_speed,
        "user volume",       A_UNSIGNED, self->_.mvhd.user_volume,
        "geometry",          A_ARRAY_UNSIGNED, 9, self->_.mvhd.geometry,
        "preview",           A_UINT64,   self->_.mvhd.preview,
        "poster",            A_UNSIGNED, self->_.mvhd.poster,
        "qt selection time", A_UINT64,   self->_.mvhd.qt_selection_time,
        "qt current time",   A_UNSIGNED, self->_.mvhd.qt_current_time,
        "next track ID",     A_UNSIGNED, self->_.mvhd.next_track_id);

}

static struct qt_atom*
parse_mvhd(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned version;
    unsigned flags;
    qt_time_t created_date;
    qt_time_t modified_date;
    unsigned time_scale;
    qt_time_t duration;
    unsigned playback_speed;
    unsigned user_volume;
    unsigned geometry[9];
    uint64_t preview;
    unsigned poster;
    uint64_t qt_selection_time;
    unsigned qt_current_time;
    unsigned next_track_id;

    version = stream->read(stream, 8);
    flags = stream->read(stream, 24);
    if (version) {
        created_date = stream->read_64(stream, 64);
        modified_date = stream->read_64(stream, 64);
        time_scale = stream->read(stream, 32);
        duration = stream->read_64(stream, 64);
    } else {
        created_date = stream->read(stream, 32);
        modified_date = stream->read(stream, 32);
        time_scale = stream->read(stream, 32);
        duration = stream->read(stream, 32);
    }

    stream->parse(stream, "32u 16u 10P 9*32u 64U 32u 64U 32u 32u",
                  &playback_speed,
                  &user_volume,
                  &geometry[0],
                  &geometry[1],
                  &geometry[2],
                  &geometry[3],
                  &geometry[4],
                  &geometry[5],
                  &geometry[6],
                  &geometry[7],
                  &geometry[8],
                  &preview,
                  &poster,
                  &qt_selection_time,
                  &qt_current_time,
                  &next_track_id);

    return qt_mvhd_new(version,
                       flags,
                       created_date,
                       modified_date,
                       time_scale,
                       duration,
                       playback_speed,
                       user_volume,
                       geometry,
                       preview,
                       poster,
                       qt_selection_time,
                       qt_current_time,
                       next_track_id);
}

static void
build_mvhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, self->_.mvhd.version);
    stream->write(stream, 24, self->_.mvhd.flags);
    if (self->_.mvhd.version) {
        stream->write_64(stream, 64, self->_.mvhd.created_date);
        stream->write_64(stream, 64, self->_.mvhd.modified_date);
        stream->write(stream, 32, self->_.mvhd.time_scale);
        stream->write_64(stream, 64, self->_.mvhd.duration);
    } else {
        stream->write(stream, 32, (unsigned)self->_.mvhd.created_date);
        stream->write(stream, 32, (unsigned)self->_.mvhd.modified_date);
        stream->write(stream, 32, self->_.mvhd.time_scale);
        stream->write(stream, 32, (unsigned)self->_.mvhd.duration);
    }

    stream->build(stream, "32u 16u 10P 9*32u 64U 32u 64U 32u 32u",
                  self->_.mvhd.playback_speed,
                  self->_.mvhd.user_volume,
                  self->_.mvhd.geometry[0],
                  self->_.mvhd.geometry[1],
                  self->_.mvhd.geometry[2],
                  self->_.mvhd.geometry[3],
                  self->_.mvhd.geometry[4],
                  self->_.mvhd.geometry[5],
                  self->_.mvhd.geometry[6],
                  self->_.mvhd.geometry[7],
                  self->_.mvhd.geometry[8],
                  self->_.mvhd.preview,
                  self->_.mvhd.poster,
                  self->_.mvhd.qt_selection_time,
                  self->_.mvhd.qt_current_time,
                  self->_.mvhd.next_track_id);
}

static unsigned
size_mvhd(const struct qt_atom *self)
{
    if (self->_.mvhd.version) {
        return 120;
    } else {
        return 108;
    }
}

static void
free_mvhd(struct qt_atom *self)
{
    free(self);
}

/*** tkhd ***/

static void
display_tkhd(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_fields(
        indent, output, self->name, 11,
        "version",       A_INT,      self->_.tkhd.version,
        "flags",         A_UNSIGNED, self->_.tkhd.flags,
        "created date",  A_UINT64,   self->_.tkhd.created_date,
        "modified date", A_UINT64,   self->_.tkhd.modified_date,
        "track ID",      A_UNSIGNED, self->_.tkhd.track_id,
        "duration",      A_UINT64,   self->_.tkhd.duration,
        "layer",         A_UNSIGNED, self->_.tkhd.layer,
        "QT alternate",  A_UNSIGNED, self->_.tkhd.qt_alternate,
        "geometry",      A_ARRAY_UNSIGNED, 9, self->_.tkhd.geometry,
        "video width",   A_UNSIGNED, self->_.tkhd.video_width,
        "video height",  A_UNSIGNED, self->_.tkhd.video_height);
}

static struct qt_atom*
parse_tkhd(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    int version;
    unsigned flags;
    qt_time_t created_date;
    qt_time_t modified_date;
    unsigned track_id;
    qt_time_t duration;
    unsigned layer;
    unsigned qt_alternate;
    unsigned volume;
    unsigned geometry[9];
    unsigned video_width;
    unsigned video_height;

    version = stream->read(stream, 8);
    flags = stream->read(stream, 24);
    if (version) {
        created_date = stream->read_64(stream, 64);
        modified_date = stream->read_64(stream, 64);
        track_id = stream->read(stream, 32);
        stream->skip(stream, 32);
        duration = stream->read_64(stream, 64);
    } else {
        created_date = stream->read(stream, 32);
        modified_date = stream->read(stream, 32);
        track_id = stream->read(stream, 32);
        stream->skip(stream, 32);
        duration = stream->read(stream, 32);
    }

    stream->parse(stream, "8P 16u 16u 16u 16p 9*32u 32u 32u",
                  &layer,
                  &qt_alternate,
                  &volume,
                  &geometry[0],
                  &geometry[1],
                  &geometry[2],
                  &geometry[3],
                  &geometry[4],
                  &geometry[5],
                  &geometry[6],
                  &geometry[7],
                  &geometry[8],
                  &video_width,
                  &video_height);

    return qt_tkhd_new(version,
                       flags,
                       created_date,
                       modified_date,
                       track_id,
                       duration,
                       layer,
                       qt_alternate,
                       volume,
                       geometry,
                       video_width,
                       video_height);
}

static void
build_tkhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, self->_.tkhd.version ? 1 : 0); /*version*/
    stream->build(stream, "24u", self->_.tkhd.flags);

    if (self->_.tkhd.version) {
        stream->write_64(stream, 64, self->_.tkhd.created_date);
        stream->write_64(stream, 64, self->_.tkhd.modified_date);
        stream->write(stream, 32, self->_.tkhd.track_id);
        stream->write(stream, 32, 0);
        stream->write_64(stream, 64, self->_.tkhd.duration);
    } else {
        stream->write(stream, 32, (unsigned)self->_.tkhd.created_date);
        stream->write(stream, 32, (unsigned)self->_.tkhd.modified_date);
        stream->write(stream, 32, self->_.tkhd.track_id);
        stream->write(stream, 32, 0);
        stream->write(stream, 32, (unsigned)self->_.tkhd.duration);
    }

    stream->build(stream, "8P 16u 16u 16u 16p 9*32u 32u 32u",
                  self->_.tkhd.layer,
                  self->_.tkhd.qt_alternate,
                  self->_.tkhd.volume,
                  self->_.tkhd.geometry[0],
                  self->_.tkhd.geometry[1],
                  self->_.tkhd.geometry[2],
                  self->_.tkhd.geometry[3],
                  self->_.tkhd.geometry[4],
                  self->_.tkhd.geometry[5],
                  self->_.tkhd.geometry[6],
                  self->_.tkhd.geometry[7],
                  self->_.tkhd.geometry[8],
                  self->_.tkhd.video_width,
                  self->_.tkhd.video_height);
}

static unsigned
size_tkhd(const struct qt_atom *self)
{
    if (self->_.tkhd.version) {
        return 104;
    } else {
        return 92;
    }
}

static void
free_tkhd(struct qt_atom *self)
{
    free(self);
}

/*** mdhd ***/

static void
display_mdhd(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_fields(
        indent, output, self->name, 8,
        "version", A_INT, self->_.mdhd.version,
        "flags", A_UNSIGNED, self->_.mdhd.flags,
        "created date", A_UINT64, self->_.mdhd.created_date,
        "modified date", A_UINT64, self->_.mdhd.modified_date,
        "time scale", A_UNSIGNED, self->_.mdhd.time_scale,
        "duration", A_UINT64, self->_.mdhd.duration,
        "language", A_ARRAY_CHAR, 3, self->_.mdhd.language,
        "quality", A_UNSIGNED, self->_.mdhd.quality);
}

static struct qt_atom*
parse_mdhd(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    int version;
    int flags;
    qt_time_t created_date;
    qt_time_t modified_date;
    unsigned time_scale;
    qt_time_t duration;
    char language[3];
    unsigned quality;
    unsigned i;

    version = stream->read(stream, 8);
    flags = stream->read(stream, 24);
    if (version) {
        created_date = stream->read_64(stream, 64);
        modified_date = stream->read_64(stream, 64);
        time_scale = stream->read(stream, 32);
        duration = stream->read_64(stream, 64);
    } else {
        created_date = stream->read(stream, 32);
        modified_date = stream->read(stream, 32);
        time_scale = stream->read(stream, 32);
        duration = stream->read(stream, 32);
    }
    stream->skip(stream, 1);
    for (i = 0; i < 3; i++) {
        language[i] = stream->read(stream, 5) + 0x60;
    }
    quality = stream->read(stream, 16);

    return qt_mdhd_new(version,
                       flags,
                       created_date,
                       modified_date,
                       time_scale,
                       duration,
                       language,
                       quality);
}

static void
build_mdhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, self->_.mdhd.version ? 1 : 0);
    stream->write(stream, 24, self->_.mdhd.flags);

    if (self->_.mdhd.version) {
        stream->write_64(stream, 64, self->_.mdhd.created_date);
        stream->write_64(stream, 64, self->_.mdhd.modified_date);
        stream->write(stream, 32, self->_.mdhd.time_scale);
        stream->write_64(stream, 64, self->_.mdhd.duration);
    } else {
        stream->write(stream, 32, (unsigned)self->_.mdhd.created_date);
        stream->write(stream, 32, (unsigned)self->_.mdhd.modified_date);
        stream->write(stream, 32, self->_.mdhd.time_scale);
        stream->write(stream, 32, (unsigned)self->_.mdhd.duration);
    }

    stream->write(stream, 1, 0); /*padding*/
    for (i = 0; i < 3; i++) {
        stream->write(stream, 5, self->_.mdhd.language[i] - 0x60);
    }

    stream->write(stream, 16, 0); /*QuickTime quality*/
}

static unsigned
size_mdhd(const struct qt_atom *self)
{
    if (self->_.mdhd.version) {
        return 44;
    } else {
        return 32;
    }
}

static void
free_mdhd(struct qt_atom *self)
{
    free(self);
}

/*** hdlr ***/

static void
display_hdlr(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_fields(
        indent, output, self->name, 8,
        "version",         A_UNSIGNED,  self->_.hdlr.version,
        "flags",           A_UNSIGNED,  self->_.hdlr.flags,
        "QT type",         A_STRING, 4, self->_.hdlr.qt_type,
        "QT subtype",      A_STRING, 4, self->_.hdlr.qt_subtype,
        "QT manufacturer", A_STRING, 4, self->_.hdlr.qt_manufacturer,
        "QT flags",        A_UNSIGNED,  self->_.hdlr.qt_flags,
        "QT flags mask",   A_UNSIGNED,  self->_.hdlr.qt_flags_mask,
        "padding",         A_UNSIGNED,  self->_.hdlr.padding);
}

static struct qt_atom*
parse_hdlr(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned version;
    unsigned flags;
    char qt_type[4];
    char qt_subtype[4];
    char qt_manufacturer[4];
    unsigned qt_flags;
    unsigned qt_flags_mask;
    unsigned component_name_length;
    char *component_name;
    unsigned padding;
    struct qt_atom *atom;

    version = stream->read(stream, 8);
    flags = stream->read(stream, 24);
    stream->read_bytes(stream, (uint8_t*)qt_type, 4);
    stream->read_bytes(stream, (uint8_t*)qt_subtype, 4);
    stream->read_bytes(stream, (uint8_t*)qt_manufacturer, 4);
    qt_flags = stream->read(stream, 32);
    qt_flags_mask = stream->read(stream, 32);
    component_name_length = stream->read(stream, 8);
    component_name = malloc(component_name_length);
    stream->read_bytes(stream,
                       (uint8_t*)component_name,
                       component_name_length);
    padding = atom_size - (25 + component_name_length);
    stream->skip_bytes(stream, padding);

    atom = qt_hdlr_new(version,
                       flags,
                       qt_type,
                       qt_subtype,
                       qt_manufacturer,
                       qt_flags,
                       qt_flags_mask,
                       component_name_length,
                       component_name,
                       padding);

    free(component_name);
    return atom;
}

static void
build_hdlr(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, self->_.hdlr.version);
    stream->write(stream, 24, self->_.hdlr.flags);
    stream->write_bytes(stream, self->_.hdlr.qt_type, 4);
    stream->write_bytes(stream, self->_.hdlr.qt_subtype, 4);
    stream->write_bytes(stream, self->_.hdlr.qt_manufacturer, 4);
    stream->write(stream, 32, self->_.hdlr.qt_flags);
    stream->write(stream, 32, self->_.hdlr.qt_flags_mask);
    stream->write(stream, 8, self->_.hdlr.component_name_length);
    stream->write_bytes(stream,
                        self->_.hdlr.component_name,
                        self->_.hdlr.component_name_length);
    stream->write(stream, 8 * self->_.hdlr.padding, 0);
}

static unsigned
size_hdlr(const struct qt_atom *self)
{
    return 33 + self->_.hdlr.component_name_length + self->_.hdlr.padding;
}

static void
free_hdlr(struct qt_atom *self)
{
    free(self->_.hdlr.component_name);
    free(self);
}

/*** smhd ***/

static void
display_smhd(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_fields(
        indent, output, self->name, 3,
        "version", A_UNSIGNED, self->_.smhd.version,
        "flags",   A_UNSIGNED, self->_.smhd.flags,
        "balance", A_UNSIGNED, self->_.smhd.balance);
}

static struct qt_atom*
parse_smhd(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned balance = stream->read(stream, 16);
    stream->skip(stream, 16);
    return qt_smhd_new(version, flags, balance);
}

static void
build_smhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, self->_.smhd.version);
    stream->write(stream, 24, self->_.smhd.flags);
    stream->write(stream, 16, self->_.smhd.balance);
    stream->write(stream, 16, 0); /*padding*/
}

static unsigned
size_smhd(const struct qt_atom *self)
{
    return 16;
}

static void
free_smhd(struct qt_atom *self)
{
    free(self);
}

/*** dref ***/

static void
display_dref(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    struct qt_atom_list *list;

    display_fields(
        indent, output, self->name, 3,
        "version",         A_UNSIGNED, self->_.dref.version,
        "flags",           A_UNSIGNED, self->_.dref.flags,
        "reference atoms", A_UNSIGNED, atom_list_len(self->_.dref.references));

    for (list = self->_.dref.references; list; list = list->next) {
        list->atom->display(list->atom, indent + 1, output);
    }
}

static struct qt_atom*
parse_dref(BitstreamReader *stream,
           unsigned atom_size,
           const char *atom_name)
{
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned reference_atom_count = stream->read(stream, 32);
    struct qt_atom *dref = qt_dref_new(version, flags, 0);
    for (; reference_atom_count; reference_atom_count--) {
        struct qt_atom *reference = qt_atom_parse(stream);
        dref->_.dref.references =
            atom_list_append(dref->_.dref.references, reference);
    }
    return dref;
}

static void
build_dref(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    struct qt_atom_list *reference;

    build_header(self, stream);
    stream->write(stream, 8, self->_.dref.version);
    stream->write(stream, 24, self->_.dref.flags);
    /*number of references*/
    stream->write(stream, 32, atom_list_len(self->_.dref.references));
    for (reference = self->_.dref.references;
         reference;
         reference = reference->next) {
        reference->atom->build(reference->atom, stream);
    }
}

static unsigned
size_dref(const struct qt_atom *self)
{
    unsigned size = 8 + 8;
    struct qt_atom_list *reference;
    for (reference = self->_.dref.references;
         reference;
         reference = reference->next) {
        size += reference->atom->size(reference->atom);
    }
    return size;
}

static void
free_dref(struct qt_atom *self)
{
    atom_list_free(self->_.dref.references);
    free(self);
}

/*** stsd ***/

static void
display_stsd(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    struct qt_atom_list *list;

    display_fields(
        indent, output, self->name, 3,
        "version",           A_UNSIGNED, self->_.stsd.version,
        "flags",             A_UNSIGNED, self->_.stsd.flags,
        "description atoms", A_UNSIGNED,
        atom_list_len(self->_.stsd.descriptions));

    for (list = self->_.stsd.descriptions; list; list = list->next) {
        list->atom->display(list->atom, indent + 1, output);
    }
}

static struct qt_atom*
parse_stsd(BitstreamReader *stream,
           unsigned atom_size,
           const char *atom_name)
{
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned description_atom_count = stream->read(stream, 32);
    struct qt_atom *stsd = qt_stsd_new(version, flags, 0);
    for (; description_atom_count; description_atom_count--) {
        struct qt_atom *description = qt_atom_parse(stream);
        stsd->_.stsd.descriptions =
            atom_list_append(stsd->_.stsd.descriptions, description);
    }
    return stsd;
}

static void
build_stsd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    struct qt_atom_list *descriptions;

    build_header(self, stream);
    stream->write(stream, 8, self->_.stsd.version);
    stream->write(stream, 24, self->_.stsd.flags);
    /*number of descriptions*/
    stream->write(stream, 32, atom_list_len(self->_.stsd.descriptions));
    for (descriptions = self->_.stsd.descriptions;
         descriptions;
         descriptions = descriptions->next) {
        descriptions->atom->build(descriptions->atom, stream);
    }
}

static unsigned
size_stsd(const struct qt_atom *self)
{
    unsigned size = 8 + 8;
    struct qt_atom_list *descriptions;
    for (descriptions = self->_.stsd.descriptions;
         descriptions;
         descriptions = descriptions->next) {
        size += descriptions->atom->size(descriptions->atom);
    }
    return size;
}

static void
free_stsd(struct qt_atom *self)
{
    atom_list_free(self->_.stsd.descriptions);
    free(self);
}

/*** alac ***/

static void
display_alac(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_fields(
        indent, output, self->name, 9,
        "reference index",   A_UNSIGNED, self->_.alac.reference_index,
        "version",           A_UNSIGNED, self->_.alac.version,
        "revision level",    A_UNSIGNED, self->_.alac.revision_level,
        "vendor",            A_STRING, 4, self->_.alac.vendor,
        "channels",          A_UNSIGNED, self->_.alac.channels,
        "bits per sample",   A_UNSIGNED, self->_.alac.bits_per_sample,
        "compression ID",    A_UNSIGNED, self->_.alac.compression_id,
        "audio packet size", A_UNSIGNED, self->_.alac.audio_packet_size,
        "sample rate",       A_UNSIGNED, self->_.alac.sample_rate);
    self->_.alac.sub_alac->display(self->_.alac.sub_alac, indent + 1, output);
}

static struct qt_atom*
parse_alac(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned reference_index;
    unsigned version;
    unsigned revision_level;
    uint8_t vendor[4];
    unsigned channels;
    unsigned bits_per_sample;
    unsigned compression_id;
    unsigned audio_packet_size;
    unsigned sample_rate;
    struct qt_atom *sub_alac;

    unsigned sub_alac_size;
    char sub_alac_name[4];

    stream->parse(stream, "48p 3*16u 4b 4*16u 32u",
                  &reference_index,
                  &version,
                  &revision_level,
                  vendor,
                  &channels,
                  &bits_per_sample,
                  &compression_id,
                  &audio_packet_size,
                  &sample_rate);

    sub_alac_size = stream->read(stream, 32);
    stream->read_bytes(stream, (uint8_t*)sub_alac_name, 4);
    sub_alac = parse_sub_alac(stream, sub_alac_size - 8, sub_alac_name);
    assert(sub_alac_size == sub_alac->size(sub_alac));

    return qt_alac_new(reference_index,
                       version,
                       revision_level,
                       vendor,
                       channels,
                       bits_per_sample,
                       compression_id,
                       audio_packet_size,
                       sample_rate,
                       sub_alac);
}

static void
build_alac(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->build(stream, "48p 3*16u 4b 4*16u 32u",
                  self->_.alac.reference_index,
                  self->_.alac.version,
                  self->_.alac.revision_level,
                  self->_.alac.vendor,
                  self->_.alac.channels,
                  self->_.alac.bits_per_sample,
                  self->_.alac.compression_id,
                  self->_.alac.audio_packet_size,
                  self->_.alac.sample_rate);
    self->_.alac.sub_alac->build(self->_.alac.sub_alac, stream);
}

static unsigned
size_alac(const struct qt_atom *self)
{
    return 36 + self->_.alac.sub_alac->size(self->_.alac.sub_alac);
}

static void
free_alac(struct qt_atom *self)
{
    self->_.alac.sub_alac->free(self->_.alac.sub_alac);
    free(self);
}

/*** sub alac ***/

static void
display_sub_alac(const struct qt_atom *self,
                 unsigned indent,
                 FILE *output)
{
    display_fields(
        indent, output, self->name, 10,
        "max samples per frame", A_UNSIGNED,
        self->_.sub_alac.max_samples_per_frame,
        "bits per sample",       A_UNSIGNED, self->_.sub_alac.bits_per_sample,
        "history multiplier",    A_UNSIGNED,
        self->_.sub_alac.history_multiplier,
        "initial history",       A_UNSIGNED, self->_.sub_alac.initial_history,
        "maximum K",             A_UNSIGNED, self->_.sub_alac.maximum_K,
        "channels",              A_UNSIGNED, self->_.sub_alac.channels,
        "unknown",               A_UNSIGNED, self->_.sub_alac.unknown,
        "max coded frame size",  A_UNSIGNED,
        self->_.sub_alac.max_coded_frame_size,
        "bitrate",               A_UNSIGNED, self->_.sub_alac.bitrate,
        "sample rate",           A_UNSIGNED, self->_.sub_alac.sample_rate);
}

static struct qt_atom*
parse_sub_alac(BitstreamReader *stream,
               unsigned atom_size,
               const char atom_name[4])
{
    unsigned max_samples_per_frame;
    unsigned bits_per_sample;
    unsigned history_multiplier;
    unsigned initial_history;
    unsigned maximum_K;
    unsigned channels;
    unsigned unknown;
    unsigned max_coded_frame_size;
    unsigned bitrate;
    unsigned sample_rate;

    stream->parse(stream, "32p 32u 8p 5*8u 16u 3*32u",
                  &max_samples_per_frame,
                  &bits_per_sample,
                  &history_multiplier,
                  &initial_history,
                  &maximum_K,
                  &channels,
                  &unknown,
                  &max_coded_frame_size,
                  &bitrate,
                  &sample_rate);

   return qt_sub_alac_new(max_samples_per_frame,
                          bits_per_sample,
                          history_multiplier,
                          initial_history,
                          maximum_K,
                          channels,
                          unknown,
                          max_coded_frame_size,
                          bitrate,
                          sample_rate);
}

static void
build_sub_alac(const struct qt_atom *self,
               BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->build(stream, "32p 32u 8p 5*8u 16u 3*32u",
                  self->_.sub_alac.max_samples_per_frame,
                  self->_.sub_alac.bits_per_sample,
                  self->_.sub_alac.history_multiplier,
                  self->_.sub_alac.initial_history,
                  self->_.sub_alac.maximum_K,
                  self->_.sub_alac.channels,
                  self->_.sub_alac.unknown,
                  self->_.sub_alac.max_coded_frame_size,
                  self->_.sub_alac.bitrate,
                  self->_.sub_alac.sample_rate);
}

static unsigned
size_sub_alac(const struct qt_atom *self)
{
    return 36;
}

static void
free_sub_alac(struct qt_atom *self)
{
    free(self);
}

/*** stts ***/

static void
display_stts(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    unsigned i;
    display_fields(
        indent, output, self->name, 3,
        "version",     A_UNSIGNED, self->_.stts.version,
        "flags",       A_UNSIGNED, self->_.stts.flags,
        "times count", A_UNSIGNED, self->_.stts.times_count);
    for (i = 0; i < self->_.stts.times_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %d) %u occurences, %u PCM frames\n",
                i,
                self->_.stts.times[i].occurences,
                self->_.stts.times[i].pcm_frame_count);
    }
}

static struct qt_atom*
parse_stts(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned i;
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned times_count = stream->read(stream, 32);
    struct qt_atom *stts = qt_stts_new(version, flags, 0);

    stts->_.stts.times_count = times_count;
    stts->_.stts.times = realloc(stts->_.stts.times,
                                 times_count * sizeof(struct stts_time));

    for (i = 0; i < times_count; i++) {
        stts->_.stts.times[i].occurences = stream->read(stream, 32);
        stts->_.stts.times[i].pcm_frame_count = stream->read(stream, 32);
    }

    return stts;
}

static void
build_stts(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, self->_.stts.version);
    stream->write(stream, 24, self->_.stts.flags);
    stream->write(stream, 32, self->_.stts.times_count);
    for (i = 0; i < self->_.stts.times_count; i++) {
        stream->write(stream, 32, self->_.stts.times[i].occurences);
        stream->write(stream, 32, self->_.stts.times[i].pcm_frame_count);
    }
}

static unsigned
size_stts(const struct qt_atom *self)
{
    return 16 + self->_.stts.times_count * 8;
}

static void
free_stts(struct qt_atom *self)
{
    free(self->_.stts.times);
    free(self);
}

/*** stsc ***/

static void
display_stsc(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    unsigned i;
    display_fields(
        indent, output, self->name, 3,
        "version", A_UNSIGNED, self->_.stsc.version,
        "flags",   A_UNSIGNED, self->_.stsc.flags,
        "chunks",  A_UNSIGNED, self->_.stsc.entries_count);
    for (i = 0; i < self->_.stsc.entries_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u first chunk, %u frames per chunk\n",
                self->_.stsc.entries[i].first_chunk,
                self->_.stsc.entries[i].frames_per_chunk);
    }

}

static struct qt_atom*
parse_stsc(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned i;
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned entries_count = stream->read(stream, 32);
    struct qt_atom *stsc = qt_stsc_new(version, flags, 0);

    stsc->_.stsc.entries_count = entries_count;
    stsc->_.stsc.entries = realloc(stsc->_.stsc.entries,
                                   entries_count * sizeof(struct stsc_entry));

    for (i = 0; i < entries_count; i++) {
        stsc->_.stsc.entries[i].first_chunk = stream->read(stream, 32);
        stsc->_.stsc.entries[i].frames_per_chunk = stream->read(stream, 32);
        stsc->_.stsc.entries[i].description_index = stream->read(stream, 32);
    }

    return stsc;
}

static void
build_stsc(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, self->_.stsc.version);
    stream->write(stream, 24, self->_.stsc.flags);
    stream->write(stream, 32, self->_.stsc.entries_count);
    for (i = 0; i < self->_.stsc.entries_count; i++) {
        stream->write(stream, 32, self->_.stsc.entries[i].first_chunk);
        stream->write(stream, 32, self->_.stsc.entries[i].frames_per_chunk);
        stream->write(stream, 32, self->_.stsc.entries[i].description_index);
    }
}

static unsigned
size_stsc(const struct qt_atom *self)
{
    return 16 + self->_.stsc.entries_count * 12;
}

static void
free_stsc(struct qt_atom *self)
{
    free(self->_.stsc.entries);
    free(self);
}

/*** stsz ***/

static void
display_stsz(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    unsigned i;

    display_fields(
        indent, output, self->name, 4,
        "version",         A_UNSIGNED, self->_.stsz.version,
        "flags",           A_UNSIGNED, self->_.stsz.flags,
        "frame byte size", A_UNSIGNED, self->_.stsz.frame_byte_size,
        "frames count",    A_UNSIGNED, self->_.stsz.frames_count);
    for (i = 0; i < self->_.stsz.frames_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u) %u bytes\n", i, self->_.stsz.frame_size[i]);
    }
}

static struct qt_atom*
parse_stsz(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned i;
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned frame_byte_size = stream->read(stream, 32);
    unsigned frame_sizes = stream->read(stream, 32);
    struct qt_atom *stsz = qt_stsz_new(version,
                                       flags,
                                       frame_byte_size,
                                       frame_sizes);
    for (i = 0; i < frame_sizes; i++) {
        stsz->_.stsz.frame_size[i] = stream->read(stream, 32);
    }
    return stsz;
}

static void
build_stsz(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, self->_.stsz.version);
    stream->write(stream, 24, self->_.stsz.flags);
    stream->write(stream, 32, self->_.stsz.frame_byte_size);
    stream->write(stream, 32, self->_.stsz.frames_count);
    for (i = 0; i < self->_.stsz.frames_count; i++) {
        stream->write(stream, 32, self->_.stsz.frame_size[i]);
    }
}

static unsigned
size_stsz(const struct qt_atom *self)
{
    return 20 + self->_.stsz.frames_count * 4;
}

static void
free_stsz(struct qt_atom *self)
{
    free(self->_.stsz.frame_size);
    free(self);
}

/*** stco ***/

static void
display_stco(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    unsigned i;

    display_fields(
        indent, output, self->name, 3,
        "version", A_UNSIGNED, self->_.stco.version,
        "flags",   A_UNSIGNED, self->_.stco.flags,
        "offsets", A_UNSIGNED, self->_.stco.offsets_count);
    for (i = 0; i < self->_.stco.offsets_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u) 0x%X\n", i, self->_.stco.chunk_offset[i]);
    }
}

static struct qt_atom*
parse_stco(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned i;
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    unsigned chunk_offsets = stream->read(stream, 32);
    struct qt_atom *stco = qt_stco_new(version, flags, chunk_offsets);
    for (i = 0; i < chunk_offsets; i++) {
        stco->_.stco.chunk_offset[i] = stream->read(stream, 32);
    }
    return stco;
}

static void
build_stco(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, self->_.stco.version);
    stream->write(stream, 24, self->_.stco.flags);
    stream->write(stream, 32, self->_.stco.offsets_count);
    for (i = 0; i < self->_.stco.offsets_count; i++) {
        stream->write(stream, 32, self->_.stco.chunk_offset[i]);
    }
}

static unsigned
size_stco(const struct qt_atom *self)
{
    return 16 + self->_.stco.offsets_count * 4;
}

static void
free_stco(struct qt_atom *self)
{
    free(self->_.stco.chunk_offset);
    free(self);
}

/*** meta ***/

static void
display_meta(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    struct qt_atom_list *list;
    display_fields(
        indent, output, self->name, 2,
        "version", A_UNSIGNED, self->_.meta.version,
        "flags",   A_UNSIGNED, self->_.meta.flags);
    for (list = self->_.meta.sub_atoms; list; list = list->next) {
        list->atom->display(list->atom, indent + 1, output);
    }
}

static struct qt_atom*
parse_meta(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned version = stream->read(stream, 8);
    unsigned flags = stream->read(stream, 24);
    struct qt_atom *meta = qt_meta_new(version, flags, 0);
    atom_size -= 4; /*remove header*/
    while (atom_size) {
        struct qt_atom *sub_atom = qt_atom_parse(stream);
        atom_size -= sub_atom->size(sub_atom);
        meta->_.meta.sub_atoms = atom_list_append(meta->_.meta.sub_atoms,
                                                  sub_atom);
    }
    return meta;
}

static void
build_meta(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    struct qt_atom_list *list;
    build_header(self, stream);
    stream->write(stream, 8, self->_.meta.version);
    stream->write(stream, 24, self->_.meta.flags);
    for (list = self->_.meta.sub_atoms; list; list = list->next) {
        list->atom->build(list->atom, stream);
    }
}

static unsigned
size_meta(const struct qt_atom *self)
{
    unsigned size = 8 + 4; /*header + version + flags*/
    struct qt_atom_list *list;
    for (list = self->_.meta.sub_atoms; list; list = list->next) {
        size += list->atom->size(list->atom);
    }
    return size;
}

static void
free_meta(struct qt_atom *self)
{
    atom_list_free(self->_.meta.sub_atoms);
    free(self);
}

/*** data ***/

static void
display_data(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    unsigned i;

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - (%u) ", self->_.data.type);
    if (self->_.data.type == 1) {
        /*textual data*/
        fputs("\"", output);
        for (i = 0; i < self->_.data.data_size; i++) {
            if (isprint(self->_.data.data[i])) {
                fputc(self->_.data.data[i], output);
            } else {
                fprintf(output, "\\x%2.2X", self->_.data.data[i]);
            }
        }
        fputs("\"", output);
    } else {
        /*binary data*/
        fprintf(output, "%u bytes", self->_.data.data_size);
    }
    fputs("\n", output);
}

static struct qt_atom*
parse_data(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    unsigned type;
    unsigned data_size;
    uint8_t *data;
    struct qt_atom *atom;

    assert(atom_size > 8);
    type = stream->read(stream, 32);
    stream->skip(stream, 32);
    data_size = atom_size - 8;
    data = malloc(data_size);
    stream->read_bytes(stream, data, data_size);
    atom = qt_data_new(type, data_size, data);
    free(data);
    return atom;
}

static void
build_data(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 32, self->_.data.type);
    stream->write(stream, 32, 0); /*reserved*/
    stream->write_bytes(stream, self->_.data.data, self->_.data.data_size);
}

static unsigned
size_data(const struct qt_atom *self)
{
    return 8 + 8 + self->_.data.data_size;
}

static void
free_data(struct qt_atom *self)
{
    free(self->_.data.data);
    free(self);
}

/*** free ***/

static void
display_free(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %u bytes\n", self->_.free);
}

static struct qt_atom*
parse_free(BitstreamReader *stream,
           unsigned atom_size,
           const char atom_name[4])
{
    stream->skip_bytes(stream, atom_size);
    return qt_free_new(atom_size);
}

static void
build_free(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;
    build_header(self, stream);
    for (i = 0; i < self->_.free; i++) {
        stream->write(stream, 8, 0);
    }
}

static unsigned
size_free(const struct qt_atom *self)
{
    return 8 + self->_.free;
}

static void
free_free(struct qt_atom *self)
{
    free(self);
}

struct parser_s {
    char name[4];
    atom_parser_f parser;
};

static int
parser_cmp(const struct parser_s *e1, const struct parser_s *e2)
{
    return strncmp(e1->name, e2->name, 4);
}

typedef int (*cmp_f)(const void *e1, const void *e2);

#define A9 "\xa9"

static atom_parser_f
atom_parser(const char *atom_name)
{
    /*remember to keep this elements sorted ASCIIbetically
      as new parsers are added*/
    const static struct parser_s parsers[] = {{"----", parse_tree},
                                              {"alac", parse_alac},
                                              {"covr", parse_tree},
                                              {"cpil", parse_tree},
                                              {"cprt", parse_tree},
                                              {"data", parse_data},
                                              {"dinf", parse_tree},
                                              {"disk", parse_tree},
                                              {"dref", parse_dref},
                                              {"free", parse_free},
                                              {"ftyp", parse_ftyp},
                                              {"gnre", parse_tree},
                                              {"hdlr", parse_hdlr},
                                              {"ilst", parse_tree},
                                              {"mdhd", parse_mdhd},
                                              {"mdia", parse_tree},
                                              {"meta", parse_meta},
                                              {"minf", parse_tree},
                                              {"moov", parse_tree},
                                              {"mvhd", parse_mvhd},
                                              {"pgap", parse_tree},
                                              {"rtng", parse_tree},
                                              {"smhd", parse_smhd},
                                              {"stbl", parse_tree},
                                              {"stco", parse_stco},
                                              {"stsc", parse_stsc},
                                              {"stsd", parse_stsd},
                                              {"stsz", parse_stsz},
                                              {"stts", parse_stts},
                                              {"tkhd", parse_tkhd},
                                              {"tmpo", parse_tree},
                                              {"trak", parse_tree},
                                              {"trkn", parse_tree},
                                              {"udta", parse_tree},
                                              {A9"ART", parse_tree},
                                              {A9"alb", parse_tree},
                                              {A9"cmt", parse_tree},
                                              {A9"day", parse_tree},
                                              {A9"grp", parse_tree},
                                              {A9"nam", parse_tree},
                                              {A9"too", parse_tree},
                                              {A9"wrt", parse_tree}};
    struct parser_s key;
    struct parser_s *result;

    memcpy(key.name, atom_name, 4);
    result = bsearch(&key,
                     parsers,
                     sizeof(parsers) / sizeof(struct parser_s),
                     sizeof(struct parser_s),
                     (cmp_f)parser_cmp);

    if (result) {
        return result->parser;
    } else {
        /*catchall for any atoms we don't know*/
        return parse_leaf;
    }
}

static void
add_ftyp_brand(struct qt_atom *atom, const uint8_t compatible_brand[4])
{
    assert(atom->type == QT_FTYP);
    atom->_.ftyp.compatible_brands =
        realloc(atom->_.ftyp.compatible_brands,
                (atom->_.ftyp.compatible_brand_count + 1) * sizeof(uint8_t*));
    atom->_.ftyp.compatible_brands[atom->_.ftyp.compatible_brand_count] =
        malloc(4);
    memcpy(atom->_.ftyp.compatible_brands[atom->_.ftyp.compatible_brand_count],
           compatible_brand,
           4);
    atom->_.ftyp.compatible_brand_count += 1;
}

static void
display_fields(unsigned indent,
               FILE *output,
               const uint8_t atom_name[4],
               unsigned field_count,
               ...)
{
    unsigned i;
    va_list ap;

    va_start(ap, field_count);
    for (i = 0; i < field_count; i++) {
        char *field_label = va_arg(ap, char*);
        field_type_t type = va_arg(ap, field_type_t);

        display_indent(indent, output);
        if (i == 0) {
            display_name(atom_name, output);
        } else {
            fputs("    ", output);
        }
        fprintf(output, " - %s: ", field_label);

        switch (type) {
        case A_INT:
            fprintf(output, "%d", va_arg(ap, int));
            break;
        case A_UNSIGNED:
            fprintf(output, "%u", va_arg(ap, unsigned));
            break;
        case A_UINT64:
            fprintf(output, "%" PRIu64, va_arg(ap, uint64_t));
            break;
        case A_ARRAY_UNSIGNED:
            {
                unsigned length = va_arg(ap, unsigned);
                unsigned *array = va_arg(ap, unsigned*);
                unsigned j;
                fputs("[", output);
                for (j = 0; j < length; j++) {
                    fprintf(output, "%u", array[j]);
                    if ((j + 1) < length) {
                        fputs(", ", output);
                    }
                }
                fputs("]", output);
            }
            break;
        case A_ARRAY_CHAR:
            {
                unsigned length = va_arg(ap, unsigned);
                char *array = va_arg(ap, char*);
                unsigned j;
                fputs("[", output);
                for (j = 0; j < length; j++) {
                    fputc(array[j], output);
                    if ((j + 1) < length) {
                        fputs(", ", output);
                    }
                }
                fputs("]", output);
            }
            break;
        case A_STRING:
            {
                unsigned length = va_arg(ap, unsigned);
                uint8_t *array = va_arg(ap, uint8_t*);
                unsigned j;
                fputs("\"", output);
                for (j = 0; j < length; j++) {
                    if (isprint(array[j])) {
                        fputc(array[j], output);
                    } else {
                        fprintf(output, "\\x%2.2X", array[j]);
                    }
                }
                fputs("\"", output);
            }
            break;
        default:
            fputs("???", output);
            break;
        }

        fputs("\n", output);
    }
    va_end(ap);
}

#ifdef STANDALONE

#include <getopt.h>
#include <errno.h>
#include <sys/stat.h>

int
main(int argc, char *argv[])
{
    /*get input arguments*/
    char *filename = NULL;
    static int binary = 0;
    char c;
    const static struct option long_opts[] = {
        {"help",   no_argument, NULL,    'h'},
        {"binary", no_argument, &binary, 1},
        {NULL,     no_argument, NULL,    0}
    };
    const static char* short_opts = "-hb";
    FILE *file;
    BitstreamReader *reader;
    BitstreamWriter *writer;
    off_t total_size;

    while ((c = getopt_long(argc,
                            argv,
                            short_opts,
                            long_opts,
                            NULL)) != -1) {
        switch (c) {
        case 1:
            if (filename) {
                fprintf(stderr, "only one input file allowed\n");
                return 1;
            } else {
                filename = optarg;
            }
            break;
        case 'b':
            binary = 1;
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            fprintf(stdout, "*** Usage m4a-atoms [options] <input.m4a>\n");
            fprintf(stdout, "-b, --binary   output atom data as binary\n");
            return 0;
        default:
            break;
        }
    }

    if (!filename) {
        fprintf(stderr, "an input file is required\n");
        return 1;
    }

    if (binary) {
        writer = bw_open(stdout, BS_BIG_ENDIAN);
    }

    /*get input file's size and open it*/
    errno = 0;
    if ((file = fopen(filename, "rb")) != NULL) {
        struct stat stat;

        reader = br_open(file, BS_BIG_ENDIAN);
        if (fstat(fileno(file), &stat) == 0) {
            total_size = stat.st_size;
        } else {
            fprintf(stderr, "*** Error %s: %s\n", filename, strerror(errno));
            return 1;
        }
    } else {
        fprintf(stderr, "*** Error %s: %s\n", filename, strerror(errno));
        return 1;
    }

    /*while file still has data, read and output atoms*/
    while (total_size) {
        struct qt_atom *atom = qt_atom_parse(reader);
        if (binary) {
            atom->build(atom, writer);
            atom->display(atom, 0, stderr);
        } else {
            atom->display(atom, 0, stdout);
        }
        total_size -= atom->size(atom);
        atom->free(atom);
    }

    /*close input file*/
    reader->close(reader);

    if (binary) {
        writer->close(writer);
    }

    return 0;
}
#endif
