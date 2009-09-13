"""
Master Boot Record
The first sector on disk, contains the partition table, bootloader, et al.

http://www.win.tue.nl/~aeb/partitions/partition_types-1.html
"""
from construct import *


mbr = Struct("mbr",
    HexDumpAdapter(Bytes("bootloader_code", 446)),
    Array(4,
        Struct("partitions",
            Enum(Byte("state"),
                INACTIVE = 0x00,
                ACTIVE = 0x80,
            ),
            BitStruct("beginning",
                Octet("head"),
                Bits("sect", 6),
                Bits("cyl", 10),
            ),
            Enum(UBInt8("type"),
                Nothing = 0x00,
                FAT12 = 0x01,
                XENIX_ROOT = 0x02,
                XENIX_USR = 0x03,
                FAT16_old = 0x04,
                Extended_DOS = 0x05,
                FAT16 = 0x06,
                FAT32 = 0x0b,
                FAT32_LBA = 0x0c,
                NTFS = 0x07,
                LINUX_SWAP = 0x82,
                LINUX_NATIVE = 0x83,
                _default_ = Pass,
            ),
            BitStruct("ending",
                Octet("head"),
                Bits("sect", 6),
                Bits("cyl", 10),
            ),
            UBInt32("sector_offset"), # offset from MBR in sectors
            UBInt32("size"), # in sectors
        )
    ),
    Const(Bytes("signature", 2), "\x55\xAA"),
)



if __name__ == "__main__":
    cap1 = (
    "33C08ED0BC007CFB5007501FFCBE1B7CBF1B065057B9E501F3A4CBBDBE07B104386E00"
    "7C09751383C510E2F4CD188BF583C610497419382C74F6A0B507B4078BF0AC3C0074FC"
    "BB0700B40ECD10EBF2884E10E84600732AFE4610807E040B740B807E040C7405A0B607"
    "75D2804602068346080683560A00E821007305A0B607EBBC813EFE7D55AA740B807E10"
    "0074C8A0B707EBA98BFC1E578BF5CBBF05008A5600B408CD1372238AC1243F988ADE8A"
    "FC43F7E38BD186D6B106D2EE42F7E239560A77237205394608731CB80102BB007C8B4E"
    "028B5600CD1373514F744E32E48A5600CD13EBE48A560060BBAA55B441CD13723681FB"
    "55AA7530F6C101742B61606A006A00FF760AFF76086A0068007C6A016A10B4428BF4CD"
    "136161730E4F740B32E48A5600CD13EBD661F9C3496E76616C69642070617274697469"
    "6F6E207461626C65004572726F72206C6F6164696E67206F7065726174696E67207379"
    "7374656D004D697373696E67206F7065726174696E672073797374656D000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000002C4463B7BDB7BD00008001010007FEFFFF3F"
    "000000371671020000C1FF0FFEFFFF761671028A8FDF06000000000000000000000000"
    "000000000000000000000000000000000000000055AA"        
    ).decode("hex")
    
    print mbr.parse(cap1)





