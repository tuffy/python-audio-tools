"""
Executable and Linkable Format (ELF), 32 bit, little endian
Used on *nix systems as a replacement of the older a.out format
"""
from construct import *


elf32_program_header = Struct("program_header",
    Enum(ULInt32("type"),
        NULL = 0,
        LOAD = 1,
        DYNAMIC = 2,
        INTERP = 3,
        NOTE = 4,
        SHLIB = 5,
        PHDR = 6,
        _default_ = Pass,
    ),
    ULInt32("offset"),
    ULInt32("vaddr"),
    ULInt32("paddr"),
    ULInt32("file_size"),
    ULInt32("mem_size"),
    ULInt32("flags"),
    ULInt32("align"),
)

elf32_section_header = Struct("section_header",
    ULInt32("name_offset"),
    Pointer(lambda ctx: ctx._.strtab_data_offset + ctx.name_offset,
        CString("name")
    ),
    Enum(ULInt32("type"), 
        NULL = 0,
        PROGBITS = 1,
        SYMTAB = 2,
        STRTAB = 3,
        RELA = 4,
        HASH = 5,
        DYNAMIC = 6,
        NOTE = 7,
        NOBITS = 8,
        REL = 9,
        SHLIB = 10,
        DYNSYM = 11,
        _default_ = Pass,
    ),
    ULInt32("flags"),
    ULInt32("addr"),
    ULInt32("offset"),
    ULInt32("size"),
    ULInt32("link"),
    ULInt32("info"),
    ULInt32("align"),
    ULInt32("entry_size"),
    OnDemandPointer(lambda ctx: ctx.offset,
        HexDumpAdapter(Field("data", lambda ctx: ctx.size))
    ),
)

elf32_file = Struct("elf32_file",
    Struct("identifier",
        Const(Bytes("magic", 4), "\x7fELF"),
        Enum(Byte("file_class"),
            NONE = 0,
            CLASS32 = 1,
            CLASS64 = 2,
        ),
        Enum(Byte("encoding"),
            NONE = 0,
            LSB = 1,
            MSB = 2,            
        ),
        Byte("version"),
        Padding(9),
    ),
    Enum(ULInt16("type"),
        NONE = 0,
        RELOCATABLE = 1,
        EXECUTABLE = 2,
        SHARED = 3,
        CORE = 4,
    ),
    Enum(ULInt16("machine"),
        NONE = 0,
        M32 = 1,
        SPARC = 2,
        I386 = 3,
        Motorolla68K = 4,
        Motorolla88K = 5,
        Intel860 = 7,
        MIPS = 8,
    ),
    ULInt32("version"),
    ULInt32("entry"),
    ULInt32("ph_offset"),
    ULInt32("sh_offset"),
    ULInt32("flags"),
    ULInt16("header_size"),
    ULInt16("ph_entry_size"),
    ULInt16("ph_count"),
    ULInt16("sh_entry_size"),
    ULInt16("sh_count"),
    ULInt16("strtab_section_index"),
    
    # calculate the string table data offset (pointer arithmetics)
    # ugh... anyway, we need it in order to read the section names, later on
    Pointer(lambda ctx: 
        ctx.sh_offset + ctx.strtab_section_index * ctx.sh_entry_size + 16,
        ULInt32("strtab_data_offset"),
    ),
    
    # program header table
    Rename("program_table",
        Pointer(lambda ctx: ctx.ph_offset,
            Array(lambda ctx: ctx.ph_count,
                elf32_program_header
            )
        )
    ),
    
    # section table
    Rename("sections", 
        Pointer(lambda ctx: ctx.sh_offset,
            Array(lambda ctx: ctx.sh_count,
                elf32_section_header
            )
        )
    ),
)


if __name__ == "__main__":
    obj = elf32_file.parse_stream(open("../../test/_ctypes_test.so", "rb"))
    [s.data.value for s in obj.sections]
    print obj










