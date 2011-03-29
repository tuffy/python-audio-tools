"""
Internet Control Message Protocol for IPv4 (TCP/IP protocol stack)
"""
from construct import *
from ipv4 import IpAddress


echo_payload = Struct("echo_payload",
    UBInt16("identifier"),
    UBInt16("sequence"),
    Bytes("data", 32), # length is implementation dependent... 
                       # is anyone using more than 32 bytes?
)

dest_unreachable_payload = Struct("dest_unreachable_payload",
    Padding(2),
    UBInt16("next_hop_mtu"),
    IpAddress("host"),
    Bytes("echo", 8),
)

dest_unreachable_code = Enum(Byte("code"),
    Network_unreachable_error = 0,
    Host_unreachable_error = 1,
    Protocol_unreachable_error = 2,
    Port_unreachable_error = 3,
    The_datagram_is_too_big = 4,
    Source_route_failed_error = 5,
    Destination_network_unknown_error = 6,
    Destination_host_unknown_error = 7,
    Source_host_isolated_error = 8,
    Desination_administratively_prohibited = 9,
    Host_administratively_prohibited2 = 10,
    Network_TOS_unreachable = 11,
    Host_TOS_unreachable = 12,
)

icmp_header = Struct("icmp_header",
    Enum(Byte("type"),
        Echo_reply = 0,
        Destination_unreachable = 3,
        Source_quench = 4,
        Redirect = 5,
        Alternate_host_address = 6,
        Echo_request = 8,
        Router_advertisement = 9,
        Router_solicitation = 10,
        Time_exceeded = 11,
        Parameter_problem = 12,
        Timestamp_request = 13,
        Timestamp_reply = 14,
        Information_request = 15,
        Information_reply = 16,
        Address_mask_request = 17,
        Address_mask_reply = 18,
        _default_ = Pass,
    ),
    Switch("code", lambda ctx: ctx.type, 
        {
            "Destination_unreachable" : dest_unreachable_code,
        },
        default = Byte("code"),
    ),
    UBInt16("crc"),
    Switch("payload", lambda ctx: ctx.type, 
        {
            "Echo_reply" : echo_payload,
            "Echo_request" : echo_payload,
            "Destination_unreachable" : dest_unreachable_payload,
        }, 
        default = Pass
    )
)


if __name__ == "__main__":
    cap1 = ("0800305c02001b006162636465666768696a6b6c6d6e6f70717273747576776162"
        "63646566676869").decode("hex")
    cap2 = ("0000385c02001b006162636465666768696a6b6c6d6e6f70717273747576776162"
        "63646566676869").decode("hex")
    cap3 = ("0301000000001122aabbccdd0102030405060708").decode("hex")
    
    print icmp_header.parse(cap1)
    print icmp_header.parse(cap2)
    print icmp_header.parse(cap3)











