"""
Ethernet (TCP/IP protocol stack)
"""
from construct import *


class MacAddressAdapter(Adapter):
    def _encode(self, obj, context):
        return obj.replace("-", "").decode("hex")
    def _decode(self, obj, context):
        return "-".join(b.encode("hex") for b in obj)

def MacAddress(name):
    return MacAddressAdapter(Bytes(name, 6))

ethernet_header = Struct("ethernet_header",
    MacAddress("destination"),
    MacAddress("source"),
    Enum(UBInt16("type"),
        IPv4 = 0x0800,
        ARP = 0x0806,
        RARP = 0x8035,
        X25 = 0x0805,
        IPX = 0x8137,
        IPv6 = 0x86DD,
        _default_ = Pass,
    ),
)


if __name__ == "__main__":
    cap = "0011508c283c0002e34260090800".decode("hex")
    obj = ethernet_header.parse(cap)
    print obj
    print repr(ethernet_header.build(obj))

