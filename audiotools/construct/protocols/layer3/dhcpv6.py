"""
the Dynamic Host Configuration Protocol (DHCP) for IPv6

http://www.networksorcery.com/enp/rfc/rfc3315.txt
"""
from construct import *
from ipv6 import Ipv6Address


dhcp_option = Struct("dhcp_option",
    Enum(UBInt16("code"),
        OPTION_CLIENTID = 1,
        OPTION_SERVERID = 2,
        OPTION_IA_NA = 3,
        OPTION_IA_TA = 4,
        OPTION_IAADDR = 5,
        OPTION_ORO = 6,
        OPTION_PREFERENCE = 7,
        OPTION_ELAPSED_TIME = 8,
        OPTION_RELAY_MSG = 9,
        OPTION_AUTH = 11,
        OPTION_UNICAST = 12,
        OPTION_STATUS_CODE = 13,
        OPTION_RAPID_COMMIT = 14,
        OPTION_USER_CLASS = 15,
        OPTION_VENDOR_CLASS = 16,
        OPTION_VENDOR_OPTS = 17,
        OPTION_INTERFACE_ID = 18,
        OPTION_RECONF_MSG = 19,
        OPTION_RECONF_ACCEPT = 20,
        SIP_SERVERS_DOMAIN_NAME_LIST = 21,
        SIP_SERVERS_IPV6_ADDRESS_LIST = 22,
        DNS_RECURSIVE_NAME_SERVER = 23,
        DOMAIN_SEARCH_LIST = 24,
        OPTION_IA_PD = 25,
        OPTION_IAPREFIX = 26,
        OPTION_NIS_SERVERS = 27,
        OPTION_NISP_SERVERS = 28,
        OPTION_NIS_DOMAIN_NAME = 29,
        OPTION_NISP_DOMAIN_NAME = 30,
        SNTP_SERVER_LIST = 31,
        INFORMATION_REFRESH_TIME = 32,
        BCMCS_CONTROLLER_DOMAIN_NAME_LIST = 33,
        BCMCS_CONTROLLER_IPV6_ADDRESS_LIST = 34,
        OPTION_GEOCONF_CIVIC = 36,
        OPTION_REMOTE_ID = 37,
        RELAY_AGENT_SUBSCRIBER_ID = 38,
        OPTION_CLIENT_FQDN = 39,        
    ),
    UBInt16("length"),
    Field("data", lambda ctx: ctx.length),
)

client_message = Struct("client_message",
    Bitwise(BitField("transaction_id", 24)),
)

relay_message = Struct("relay_message",
    Byte("hop_count"),
    Ipv6Address("linkaddr"),
    Ipv6Address("peeraddr"),
)

dhcp_message = Struct("dhcp_message",
    Enum(Byte("msgtype"),
        # these are client-server messages
        SOLICIT = 1,
        ADVERTISE = 2,
        REQUEST = 3,
        CONFIRM = 4,
        RENEW = 5,
        REBIND = 6,
        REPLY = 7,
        RELEASE_ = 8,
        DECLINE_ = 9,
        RECONFIGURE = 10,
        INFORMATION_REQUEST = 11,
        # these two are relay messages
        RELAY_FORW = 12,
        RELAY_REPL = 13,
    ),
    # relay messages have a different structure from client-server messages
    Switch("params", lambda ctx: ctx.msgtype,
        {
            "RELAY_FORW" : relay_message,
            "RELAY_REPL" : relay_message,
        },
        default = client_message,
    ),
    Rename("options", GreedyRange(dhcp_option)),
)


if __name__ == "__main__":
    test1 = "\x03\x11\x22\x33\x00\x17\x00\x03ABC\x00\x05\x00\x05HELLO"
    test2 = "\x0c\x040123456789abcdef0123456789abcdef\x00\x09\x00\x0bhello world\x00\x01\x00\x00"
    print dhcp_message.parse(test1)
    print dhcp_message.parse(test2)













