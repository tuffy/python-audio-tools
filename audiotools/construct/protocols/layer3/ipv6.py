"""
Internet Protocol version 6 (TCP/IP protocol stack)
"""
from construct import *
from ipv4 import ProtocolEnum


class Ipv6AddressAdapter(Adapter):
    def _encode(self, obj, context):
        return "".join(part.decode("hex") for part in obj.split(":"))
    def _decode(self, obj, context):
        return ":".join(b.encode("hex") for b in obj)

def Ipv6Address(name):
    return Ipv6AddressAdapter(Bytes(name, 16))


ipv6_header = Struct("ip_header",
    EmbeddedBitStruct(
        OneOf(Bits("version", 4), [6]),
        Bits("traffic_class", 8),
        Bits("flow_label", 20),
    ),
    UBInt16("payload_length"),
    ProtocolEnum(UBInt8("protocol")),
    UBInt8("hoplimit"),
    Alias("ttl", "hoplimit"),
    Ipv6Address("source"),
    Ipv6Address("destination"),
)


if __name__ == "__main__":
    o = ipv6_header.parse("\x6f\xf0\x00\x00\x01\x02\x06\x80"
        "0123456789ABCDEF" "FEDCBA9876543210"
        )
    print o
    print repr(ipv6_header.build(o))






