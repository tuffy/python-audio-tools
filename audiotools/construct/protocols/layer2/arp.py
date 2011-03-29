"""
Ethernet (TCP/IP protocol stack)
"""
from construct import *
from ethernet import MacAddressAdapter
from construct.protocols.layer3.ipv4 import IpAddressAdapter



def HwAddress(name):
    return IfThenElse(name, lambda ctx: ctx.hardware_type == "ETHERNET",
        MacAddressAdapter(Field("data", lambda ctx: ctx.hwaddr_length)),
        Field("data", lambda ctx: ctx.hwaddr_length)
    )

def ProtoAddress(name):
    return IfThenElse(name, lambda ctx: ctx.protocol_type == "IP",
        IpAddressAdapter(Field("data", lambda ctx: ctx.protoaddr_length)),
        Field("data", lambda ctx: ctx.protoaddr_length)
    )

arp_header = Struct("arp_header",
    Enum(UBInt16("hardware_type"),
        ETHERNET = 1,
        EXPERIMENTAL_ETHERNET = 2,
        ProNET_TOKEN_RING = 4,
        CHAOS = 5,
        IEEE802 = 6,
        ARCNET = 7,
        HYPERCHANNEL = 8,
        ULTRALINK = 13,
        FRAME_RELAY = 15,
        FIBRE_CHANNEL = 18,
        IEEE1394 = 24,
        HIPARP = 28,
        ISO7816_3 = 29,
        ARPSEC = 30,
        IPSEC_TUNNEL = 31,
        INFINIBAND = 32,
    ),
    Enum(UBInt16("protocol_type"),
        IP = 0x0800,
    ),
    UBInt8("hwaddr_length"),
    UBInt8("protoaddr_length"),
    Enum(UBInt16("opcode"),
        REQUEST = 1,
        REPLY = 2,
        REQUEST_REVERSE = 3,
        REPLY_REVERSE = 4,
        DRARP_REQUEST = 5,
        DRARP_REPLY = 6,
        DRARP_ERROR = 7,
        InARP_REQUEST = 8,
        InARP_REPLY = 9,
        ARP_NAK = 10
        
    ),
    HwAddress("source_hwaddr"),
    ProtoAddress("source_protoaddr"),
    HwAddress("dest_hwaddr"),
    ProtoAddress("dest_protoaddr"),
)

rarp_header = Rename("rarp_header", arp_header)


if __name__ == "__main__":
    cap1 = "00010800060400010002e3426009c0a80204000000000000c0a80201".decode("hex")
    obj = arp_header.parse(cap1)
    print obj
    print repr(arp_header.build(obj))

    print "-" * 80
    
    cap2 = "00010800060400020011508c283cc0a802010002e3426009c0a80204".decode("hex")
    obj = arp_header.parse(cap2)
    print obj
    print repr(arp_header.build(obj))













