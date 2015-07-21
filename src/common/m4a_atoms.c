#include "m4a_atoms.h"
#include <string.h>
#include <ctype.h>

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
  static void free_##NAME(struct qt_atom *self);
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
ATOM_DEF(stts)
ATOM_DEF(stsc)
ATOM_DEF(stsz)
ATOM_DEF(stco)
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
    unsigned i;

    set_atom_name(atom, "ftyp");
    atom->type = QT_FTYP;
    memcpy(atom->_.ftyp.major_brand, major_brand, 4);
    atom->_.ftyp.major_brand_version = major_brand_version;
    atom->_.ftyp.compatible_brand_count = compatible_brand_count;
    atom->_.ftyp.compatible_brands =
        malloc(sizeof(uint8_t*) * compatible_brand_count);
    va_start(ap, compatible_brand_count);
    for (i = 0; i < compatible_brand_count; i++) {
        uint8_t *brand = va_arg(ap, uint8_t*);
        atom->_.ftyp.compatible_brands[i] = malloc(4);
        memcpy(atom->_.ftyp.compatible_brands[i], brand, 4);
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
qt_mvhd_new(int version,
            time_t timestamp,
            unsigned sample_rate,
            unsigned total_pcm_frames)
{
    /*the mvhd atom has a lot of crap nobody really cares about
      so I'll punt on storing it internally until a parsing routine
      requires it*/

    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "mvhd");
    atom->type = QT_MVHD;
    atom->_.mvhd.version = version;
    atom->_.mvhd.timestamp = timestamp;
    atom->_.mvhd.sample_rate = sample_rate;
    atom->_.mvhd.total_pcm_frames = total_pcm_frames;
    atom->display = display_mvhd;
    atom->build = build_mvhd;
    atom->size = size_mvhd;
    atom->free = free_mvhd;
    return atom;
}

struct qt_atom*
qt_tkhd_new(int version,
            time_t timestamp,
            unsigned total_pcm_frames)
{
    /*the tkhd atom also has a lot of crap nobody really cares about*/

    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "tkhd");
    atom->type = QT_TKHD;
    atom->_.tkhd.version = version;
    atom->_.tkhd.timestamp = timestamp;
    atom->_.tkhd.total_pcm_frames = total_pcm_frames;
    atom->display = display_tkhd;
    atom->build = build_tkhd;
    atom->size = size_tkhd;
    atom->free = free_tkhd;
    return atom;
}

struct qt_atom*
qt_mdhd_new(int version,
            time_t timestamp,
            unsigned sample_rate,
            unsigned total_pcm_frames)
{
    /*the mdhd atom has slightly less crap nobody really cares about*/

    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "mdhd");
    atom->type = QT_MDHD;
    atom->_.mdhd.version = version;
    atom->_.mdhd.timestamp = timestamp;
    atom->_.mdhd.sample_rate = sample_rate;
    atom->_.mdhd.total_pcm_frames = total_pcm_frames;
    atom->display = display_mdhd;
    atom->build = build_mdhd;
    atom->size = size_mdhd;
    atom->free = free_mdhd;
    return atom;
}

struct qt_atom*
qt_hdlr_new(unsigned component_name_length,
            const uint8_t component_name[])
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "hdlr");
    atom->type = QT_HDLR;
    atom->_.hdlr.component_name_length = component_name_length;
    atom->_.hdlr.component_name = malloc(component_name_length);
    memcpy(atom->_.hdlr.component_name,
           component_name,
           component_name_length);
    atom->display = display_hdlr;
    atom->build = build_hdlr;
    atom->size = size_hdlr;
    atom->free = free_hdlr;
    return atom;
}

struct qt_atom*
qt_smhd_new(void)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "smhd");
    atom->type = QT_SMHD;
    atom->display = display_smhd;
    atom->build = build_smhd;
    atom->size = size_smhd;
    atom->free = free_smhd;
    return atom;
}

struct qt_atom*
qt_dref_new(unsigned reference_atom_count, ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, "dref");
    atom->type = QT_DREF;
    atom->_.dref = NULL;

    va_start(ap, reference_atom_count);
    for (; reference_atom_count; reference_atom_count--) {
        struct qt_atom *reference_atom = va_arg(ap, struct qt_atom*);
        atom->_.dref = atom_list_append(atom->_.dref, reference_atom);
    }
    va_end(ap);

    atom->display = display_dref;
    atom->build = build_dref;
    atom->size = size_dref;
    atom->free = free_dref;

    return atom;
}

struct qt_atom*
qt_stsd_new(unsigned description_atom_count, ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    va_list ap;

    set_atom_name(atom, "stsd");
    atom->type = QT_STSD;
    atom->_.stsd = NULL;

    va_start(ap, description_atom_count);
    for (; description_atom_count; description_atom_count--) {
        struct qt_atom *description_atom = va_arg(ap, struct qt_atom*);
        atom->_.stsd = atom_list_append(atom->_.stsd, description_atom);
    }
    va_end(ap);

    atom->display = display_stsd;
    atom->build = build_stsd;
    atom->size = size_stsd;
    atom->free = free_stsd;

    return atom;
}

struct qt_atom*
qt_alac_new(unsigned max_samples_per_frame,
            unsigned bits_per_sample,
            unsigned history_multiplier,
            unsigned initial_history,
            unsigned maximum_K,
            unsigned channels,
            unsigned max_coded_frame_size,
            unsigned bitrate,
            unsigned sample_rate)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "alac");
    atom->type = QT_ALAC;
    atom->_.alac.max_samples_per_frame = max_samples_per_frame;
    atom->_.alac.bits_per_sample = bits_per_sample;
    atom->_.alac.history_multiplier = history_multiplier;
    atom->_.alac.initial_history = initial_history;
    atom->_.alac.maximum_K = maximum_K;
    atom->_.alac.channels = channels;
    atom->_.alac.max_coded_frame_size = max_coded_frame_size;
    atom->_.alac.bitrate = bitrate;
    atom->_.alac.sample_rate = sample_rate;
    atom->display = display_alac;
    atom->build = build_alac;
    atom->size = size_alac;
    atom->free = free_alac;
    return atom;
}

struct qt_atom*
qt_stts_new(unsigned times_count, ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    unsigned i;
    va_list ap;

    set_atom_name(atom, "stts");
    atom->type = QT_STTS;
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
qt_stsc_new(unsigned entries_count, ...)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    unsigned i;
    va_list ap;

    set_atom_name(atom, "stsc");
    atom->type = QT_STSC;
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
qt_stsz_new(unsigned frames_count)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "stsz");
    atom->type = QT_STSZ;
    atom->_.stsz.frames_count = frames_count;
    atom->_.stsz.frame_size = calloc(frames_count, sizeof(unsigned));
    atom->display = display_stsz;
    atom->build = build_stsz;
    atom->size = size_stsz;
    atom->free = free_stsz;
    return atom;
}

struct qt_atom*
qt_stco_new(unsigned chunk_offsets)
{
    struct qt_atom *atom = malloc(sizeof(struct qt_atom));
    set_atom_name(atom, "stco");
    atom->type = QT_STCO;
    atom->_.stco.offsets_count = chunk_offsets;
    atom->_.stco.chunk_offset = calloc(chunk_offsets, sizeof(unsigned));
    atom->display = display_stco;
    atom->build = build_stco;
    atom->size = size_stco;
    atom->free = free_stco;
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
    char time[] = "XXXX-XX-XX XX:XX:XX";

    strftime(time, sizeof(time),
             "%Y-%m-%d %H:%M:%S",
             localtime(&self->_.mvhd.timestamp));

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %d [%s] %u %u\n",
            self->_.mvhd.version,
            time,
            self->_.mvhd.sample_rate,
            self->_.mvhd.total_pcm_frames);
}

static void
build_mvhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, self->_.mvhd.version ? 1 : 0); /*version*/
    stream->write(stream, 24, 0);                           /*flags*/
    if (self->_.mvhd.version) {
        /*created date*/
        stream->write(stream, 64,
                      time_to_mac_utc64(self->_.mvhd.timestamp));

        /*modified date*/
        stream->write(stream, 64,
                      time_to_mac_utc64(self->_.mvhd.timestamp));

        /*sample rate*/
        stream->write(stream, 32, self->_.mvhd.sample_rate);

        /*total PCM frames*/
        stream->write(stream, 64, self->_.mvhd.total_pcm_frames);
    } else {
        /*created date*/
        stream->write(stream, 32,
                      time_to_mac_utc(self->_.mvhd.timestamp));

        /*modified date*/
        stream->write(stream, 32,
                      time_to_mac_utc(self->_.mvhd.timestamp));

        /*sample rate*/
        stream->write(stream, 32, self->_.mvhd.sample_rate);

        /*total PCM frames*/
        stream->write(stream, 32, self->_.mvhd.total_pcm_frames);
    }

    stream->write(stream, 32, 0x10000); /*playback speed*/
    stream->write(stream, 16, 0x100);   /*user volume*/
    stream->write(stream, 80, 0);       /*padding*/
    stream->build(stream, "9*32u",      /*window geometry matrixes*/
                  0x10000,
                  0,
                  0,
                  0,
                  0x10000,
                  0,
                  0,
                  0,
                  0x40000000);
   stream->write_64(stream, 64, 0);     /*QuickTime preview*/
   stream->write(stream, 32, 0);        /*QuickTime still poster*/
   stream->write_64(stream, 64, 0);     /*QuickTime selection time*/
   stream->write(stream, 32, 0);        /*QuickTime current time*/
   stream->write(stream, 32, 2);        /*next track ID*/
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
    char time[] = "XXXX-XX-XX XX:XX:XX";

    strftime(time, sizeof(time),
             "%Y-%m-%d %H:%M:%S",
             localtime(&self->_.tkhd.timestamp));

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %d [%s] %u\n",
            self->_.tkhd.version,
            time,
            self->_.tkhd.total_pcm_frames);
}

static void
build_tkhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, self->_.tkhd.version ? 1 : 0); /*version*/
    stream->build(stream, "20u 4*1u", 0, 1, 1, 1, 1);       /*flags*/

    if (self->_.tkhd.version) {
        /*created date*/
        stream->write_64(stream, 64,
                         time_to_mac_utc64(self->_.tkhd.timestamp));

        /*modified date*/
        stream->write_64(stream, 64,
                         time_to_mac_utc64(self->_.tkhd.timestamp));

        /*track ID*/
        stream->write(stream, 32, 1);

        /*padding*/
        stream->write(stream, 32, 0);

        /*total PCM frames*/
        stream->write_64(stream, 64, self->_.tkhd.total_pcm_frames);
    } else {
        /*created date*/
        stream->write(stream, 32,
                      time_to_mac_utc(self->_.tkhd.timestamp));

        /*modified date*/
        stream->write(stream, 32,
                      time_to_mac_utc(self->_.tkhd.timestamp));

        /*track ID*/
        stream->write(stream, 32, 1);

        /*padding*/
        stream->write(stream, 32, 0);

        /*total PCM frames*/
        stream->write(stream, 32, self->_.tkhd.total_pcm_frames);
    }

    stream->write(stream, 64, 0);      /*padding*/
    stream->write(stream, 16, 0);      /*video layer*/
    stream->write(stream, 16, 0);      /*QuickTime alternate*/
    stream->write(stream, 16, 0x1000); /*volume*/
    stream->write(stream, 16, 0);      /*padding*/

    stream->build(stream, "9*32u",     /*video geometry matrixes*/
                  0x10000,
                  0,
                  0,
                  0,
                  0x10000,
                  0,
                  0,
                  0,
                  0x40000000);

    stream->write(stream, 32, 0);     /*video width*/
    stream->write(stream, 32, 0);     /*video height*/
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
    char time[] = "XXXX-XX-XX XX:XX:XX";

    strftime(time, sizeof(time),
             "%Y-%m-%d %H:%M:%S",
             localtime(&self->_.tkhd.timestamp));

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %d [%s] %u %u\n",
            self->_.mdhd.version,
            time,
            self->_.mdhd.sample_rate,
            self->_.mdhd.total_pcm_frames);
}

static void
build_mdhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    const char language[3] = {'u', 'n', 'd'};
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, self->_.mdhd.version ? 1 : 0); /*version*/
    stream->write(stream, 24, 0);                           /*flags*/

    if (self->_.mdhd.version) {
        /*created date*/
        stream->write_64(stream, 64,
                         time_to_mac_utc64(self->_.mdhd.timestamp));

        /*modified date*/
        stream->write_64(stream, 64,
                         time_to_mac_utc64(self->_.mdhd.timestamp));

        /*time scale*/
        stream->write(stream, 32, self->_.mdhd.sample_rate);

        /*duration*/
        stream->write_64(stream, 64, self->_.mdhd.total_pcm_frames);
    } else {
        /*created date*/
        stream->write(stream, 32, time_to_mac_utc(self->_.mdhd.timestamp));

        /*modified date*/
        stream->write(stream, 32, time_to_mac_utc(self->_.mdhd.timestamp));

        /*time scale*/
        stream->write(stream, 32, self->_.mdhd.sample_rate);

        /*duration*/
        stream->write(stream, 32, self->_.mdhd.total_pcm_frames);
    }

    stream->write(stream, 1, 0); /*padding*/
    for (i = 0; i < 3; i++) {
        stream->write(stream, 5, language[i] - 0x60);
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
    unsigned i;

    display_indent(indent, output);
    display_name(self->name, output);
    fputs(" - \"", output);
    for (i = 0; i < self->_.hdlr.component_name_length; i++) {
        fputc(self->_.hdlr.component_name[i], output);
    }
    fputs("\"\n", output);
}

static void
build_hdlr(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    const uint8_t null[4] = {0, 0, 0, 0};
    const uint8_t soun[4] = {0x73, 0x6F, 0x75, 0x6E};

    build_header(self, stream);
    stream->write(stream, 8, 0);          /*version*/
    stream->write(stream, 24, 0);         /*flags*/
    stream->write_bytes(stream, null, 4); /*QuickTime type*/
    stream->write_bytes(stream, soun, 4); /*QuickTime subtype*/
    stream->write_bytes(stream, null, 4); /*QuickTime manufacturer*/
    stream->write_bytes(stream, null, 4); /*QuickTime reserved flags*/
    stream->write_bytes(stream, null, 4); /*QuickTime reserved flags mask*/
    stream->write(stream, 8, self->_.hdlr.component_name_length);
    stream->write_bytes(stream,
                        self->_.hdlr.component_name,
                        self->_.hdlr.component_name_length);
}

static unsigned
size_hdlr(const struct qt_atom *self)
{
    return 33 + self->_.hdlr.component_name_length;
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
    display_indent(indent, output);
    display_name(self->name, output);
    fputs("\n", output);
}

static void
build_smhd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
    stream->write(stream, 16, 0); /*audio balance*/
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
    display_indent(indent, output);
    display_name(self->name, output);
    fputs("\n", output);
    for (list = self->_.dref; list; list = list->next) {
        list->atom->display(list->atom, indent + 1, output);
    }
}

static void
build_dref(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    struct qt_atom_list *reference;

    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
    /*number of references*/
    stream->write(stream, 32, atom_list_len(self->_.dref));
    for (reference = self->_.dref; reference; reference = reference->next) {
        reference->atom->build(reference->atom, stream);
    }
}

static unsigned
size_dref(const struct qt_atom *self)
{
    unsigned size = 8 + 8;
    struct qt_atom_list *reference;
    for (reference = self->_.dref;
         reference;
         reference = reference->next) {
        size += reference->atom->size(reference->atom);
    }
    return size;
}

static void
free_dref(struct qt_atom *self)
{
    atom_list_free(self->_.dref);
    free(self);
}

/*** stst ***/

static void
display_stsd(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    struct qt_atom_list *list;
    display_indent(indent, output);
    display_name(self->name, output);
    fputs("\n", output);
    for (list = self->_.stsd; list; list = list->next) {
        list->atom->display(list->atom, indent + 1, output);
    }
}

static void
build_stsd(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    struct qt_atom_list *reference;

    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
    /*number of references*/
    stream->write(stream, 32, atom_list_len(self->_.stsd));
    for (reference = self->_.stsd; reference; reference = reference->next) {
        reference->atom->build(reference->atom, stream);
    }
}

static unsigned
size_stsd(const struct qt_atom *self)
{
    unsigned size = 8 + 8;
    struct qt_atom_list *reference;
    for (reference = self->_.stsd;
         reference;
         reference = reference->next) {
        size += reference->atom->size(reference->atom);
    }
    return size;
}

static void
free_stsd(struct qt_atom *self)
{
    atom_list_free(self->_.stsd);
    free(self);
}

/*** alac ***/

static void
display_alac(const struct qt_atom *self,
             unsigned indent,
             FILE *output)
{
    const char format[] = "     - %21s : %u\n";

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, format + 4, "max samples per frame",
            self->_.alac.max_samples_per_frame);

    display_indent(indent, output);
    fprintf(output, format, "bits-per-sample",
            self->_.alac.bits_per_sample);

    display_indent(indent, output);
    fprintf(output, format, "history multiplier",
            self->_.alac.history_multiplier);

    display_indent(indent, output);
    fprintf(output, format, "initial history",
            self->_.alac.initial_history);

    display_indent(indent, output);
    fprintf(output, format, "maximum K",
            self->_.alac.maximum_K);

    display_indent(indent, output);
    fprintf(output, format, "channels",
            self->_.alac.channels);

    display_indent(indent, output);
    fprintf(output, format, "max coded frame size",
            self->_.alac.max_coded_frame_size);

    display_indent(indent, output);
    fprintf(output, format, "bitrate",
            self->_.alac.bitrate);

    display_indent(indent, output);
    fprintf(output, format, "sample rate",
            self->_.alac.sample_rate);
}

static void
build_alac(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    const uint8_t alac_id[4] = {0x61, 0x6C, 0x61, 0x63};

    build_header(self, stream);
    stream->write(stream, 48, 0);     /*reserved*/
    stream->write(stream, 16, 1);     /*reference index*/
    stream->write(stream, 16, 0);     /*version*/
    stream->write(stream, 16, 0);     /*revision level*/
    stream->write(stream, 32, 0);     /*vendor*/
    stream->write(stream, 16, self->_.alac.channels);
    stream->write(stream, 16, self->_.alac.bits_per_sample);
    stream->write(stream, 16, 0);     /*compression ID*/
    stream->write(stream, 16, 0);     /*audio packet size*/
    stream->write(stream, 32, 44100); /*fake sample rate*/

    stream->write(stream, 32, 36);    /*sub ALAC size*/
    stream->write_bytes(stream, alac_id, 4);
    stream->write(stream, 32, 0);     /*padding*/
    stream->write(stream, 32, self->_.alac.max_samples_per_frame);
    stream->write(stream, 8, 0);      /*padding*/
    stream->write(stream, 8, self->_.alac.bits_per_sample);
    stream->write(stream, 8, self->_.alac.history_multiplier);
    stream->write(stream, 8, self->_.alac.initial_history);
    stream->write(stream, 8, self->_.alac.maximum_K);
    stream->write(stream, 8, self->_.alac.channels);
    stream->write(stream, 16, 0x00FF); /*unknown*/
    stream->write(stream, 32, self->_.alac.max_coded_frame_size);
    stream->write(stream, 32, self->_.alac.bitrate);
    stream->write(stream, 32, self->_.alac.sample_rate);
}

static unsigned
size_alac(const struct qt_atom *self)
{
    return 72;
}

static void
free_alac(struct qt_atom *self)
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
    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %u entries\n", self->_.stts.times_count);
    for (i = 0; i < self->_.stts.times_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u occurences, %u PCM frames\n",
                self->_.stts.times[i].occurences,
                self->_.stts.times[i].pcm_frame_count);
    }
}

static void
build_stts(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
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
    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %u entries\n", self->_.stts.times_count);
    for (i = 0; i < self->_.stsc.entries_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u first chunk, %u frames per chunk\n",
                self->_.stsc.entries[i].first_chunk,
                self->_.stsc.entries[i].frames_per_chunk);
    }

}

static void
build_stsc(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
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

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %u sizes\n", self->_.stsz.frames_count);
    for (i = 0; i < self->_.stsz.frames_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u) %u bytes\n", i, self->_.stsz.frame_size[i]);
    }
}

static void
build_stsz(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
    stream->write(stream, 32, 0); /*block byte size*/
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

    display_indent(indent, output);
    display_name(self->name, output);
    fprintf(output, " - %u offsets\n", self->_.stco.offsets_count);
    for (i = 0; i < self->_.stco.offsets_count; i++) {
        display_indent(indent, output);
        fprintf(output, "     - %u) 0x%X\n", i, self->_.stco.chunk_offset[i]);
    }
}

static void
build_stco(const struct qt_atom *self,
           BitstreamWriter *stream)
{
    unsigned i;

    build_header(self, stream);
    stream->write(stream, 8, 0);  /*version*/
    stream->write(stream, 24, 0); /*flags*/
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

#ifdef STANDALONE
int
main(int argc, char *argv[])
{
    //struct qt_atom *atom = qt_stts_new(2, 645, 4096, 1, 4080);
    //struct qt_atom *atom = qt_stsc_new(2, 1, 5, 130, 1);
    struct qt_atom *atom = qt_stco_new(5);

    BitstreamWriter *w = bw_open(stdout, BS_BIG_ENDIAN);
    atom->display(atom, 0, stderr);
    fprintf(stderr, "atom size : %u bytes\n", atom->size(atom));
    atom->build(atom, w);
    atom->free(atom);

    return 0;
}
#endif
