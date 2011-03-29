"""
Transmission Control Protocol (TCP/IP protocol stack)
"""
from construct import *


tcp_header = Struct("tcp_header",
    UBInt16("source"),
    UBInt16("destination"),
    UBInt32("seq"),
    UBInt32("ack"),
    EmbeddedBitStruct(
        ExprAdapter(Nibble("header_length"), 
            encoder = lambda obj, ctx: obj / 4,
            decoder = lambda obj, ctx: obj * 4,
        ),
        Padding(3),
        Struct("flags",
            Flag("ns"),
            Flag("cwr"),
            Flag("ece"),
            Flag("urg"),
            Flag("ack"),
            Flag("psh"),
            Flag("rst"),
            Flag("syn"),
            Flag("fin"),
        ),
    ),
    UBInt16("window"),
    UBInt16("checksum"),
    UBInt16("urgent"),
    Field("options", lambda ctx: ctx.header_length - 20),
)

if __name__ == "__main__":
    cap = "0db5005062303fb21836e9e650184470c9bc0000".decode("hex")
    
    obj = tcp_header.parse(cap)
    print obj
    print repr(tcp_header.build(obj))
















