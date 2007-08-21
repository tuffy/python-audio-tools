"""
User Datagram Protocol (TCP/IP protocol stack)
"""
from construct import *


udp_header = Struct("udp_header",
    Value("header_length", lambda ctx: 8),
    UBInt16("source"),
    UBInt16("destination"),
    ExprAdapter(UBInt16("payload_length"), 
        encoder = lambda obj, ctx: obj + 8,
        decoder = lambda obj, ctx: obj - 8,
    ),
    UBInt16("checksum"),
)

if __name__ == "__main__":
    cap = "0bcc003500280689".decode("hex")
    obj = udp_header.parse(cap)
    print obj
    print repr(udp_header.build(obj))


