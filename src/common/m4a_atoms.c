#include "m4a_atoms.h"
#include <string.h>
#include <ctype.h>

/*private function definitions*/

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
ATOM_DEF(free);

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

static void
atom_list_free(struct qt_atom_list *head);


/*public function implementations*/

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

/*private function implementations*/

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

static void
atom_list_free(struct qt_atom_list *head)
{
    if (head) {
        atom_list_free(head->next);
        head->atom->free(head->atom);
        free(head);
    }
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
    //struct qt_atom *atom = qt_ftyp_new((uint8_t*)"M4A ",
    //                                   0,
    //                                   4,
    //                                   (uint8_t*)"M4A ",
    //                                   (uint8_t*)"mp42",
    //                                   (uint8_t*)"isom",
    //                                   (uint8_t*)"\x00\x00\x00\x00");

    struct qt_atom *atom = qt_free_new(8);

    BitstreamWriter *w = bw_open(stdout, BS_BIG_ENDIAN);
    atom->display(atom, 0, stderr);
    fprintf(stderr, "atom size : %u bytes\n", atom->size(atom));
    atom->build(atom, w);
    atom->free(atom);

    return 0;
}
#endif
