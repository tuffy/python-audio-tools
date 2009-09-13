"""
Message Transport Part 2 (SS7 protocol stack)
(untested)
"""
from construct import *


mtp2_header = BitStruct("mtp2_header",
    Octet("flag1"),
    Bits("bsn", 7),
    Bit("bib"),
    Bits("fsn", 7),
    Bit("sib"),
    Octet("length"),
    Octet("service_info"),
    Octet("signalling_info"),
    Bits("crc", 16),
    Octet("flag2"),
)


