"""
Domain Name System (TCP/IP protocol stack)
"""
from construct import *
from construct.protocols.layer3.ipv4 import IpAddressAdapter


class DnsStringAdapter(Adapter):
    def _encode(self, obj, context):
        parts = obj.split(".")
        parts.append("")
        return parts
    def _decode(self, obj, context):
        return ".".join(obj[:-1])

dns_record_class = Enum(UBInt16("class"),
    RESERVED = 0,
    INTERNET = 1,
    CHAOS = 3,
    HESIOD = 4,
    NONE = 254,
    ANY = 255,
)

dns_record_type = Enum(UBInt16("type"),
    IPv4 = 1,
    AUTHORITIVE_NAME_SERVER = 2,
    CANONICAL_NAME = 5,
    NULL = 10,
    MAIL_EXCHANGE = 15,
    TEXT = 16,
    X25 = 19,
    ISDN = 20,
    IPv6 = 28,
    UNSPECIFIED = 103,
    ALL = 255,
)

query_record = Struct("query_record",
    DnsStringAdapter(
        RepeatUntil(lambda obj, ctx: obj == "",
            PascalString("name")
        )
    ),
    dns_record_type,
    dns_record_class,
)

rdata = Field("rdata", lambda ctx: ctx.rdata_length)

resource_record = Struct("resource_record",
    CString("name", terminators = "\xc0\x00"),
    Padding(1),
    dns_record_type,
    dns_record_class,
    UBInt32("ttl"),
    UBInt16("rdata_length"),
    IfThenElse("data", lambda ctx: ctx.type == "IPv4",
        IpAddressAdapter(rdata),
        rdata
    )
)

dns = Struct("dns",
    UBInt16("id"),
    BitStruct("flags",
        Enum(Bit("type"),
            QUERY = 0,
            RESPONSE = 1,
        ),
        Enum(Nibble("opcode"),
            STANDARD_QUERY = 0,
            INVERSE_QUERY = 1,
            SERVER_STATUS_REQUEST = 2,
            NOTIFY = 4,
            UPDATE = 5,
        ),
        Flag("authoritive_answer"),
        Flag("truncation"),
        Flag("recurssion_desired"),
        Flag("recursion_available"),
        Padding(1),
        Flag("authenticated_data"),
        Flag("checking_disabled"),
        Enum(Nibble("response_code"),
            SUCCESS = 0,
            FORMAT_ERROR = 1,
            SERVER_FAILURE = 2,
            NAME_DOES_NOT_EXIST = 3,
            NOT_IMPLEMENTED = 4,
            REFUSED = 5,
            NAME_SHOULD_NOT_EXIST = 6,
            RR_SHOULD_NOT_EXIST = 7,
            RR_SHOULD_EXIST = 8,
            NOT_AUTHORITIVE = 9,
            NOT_ZONE = 10,
        ),
    ),
    UBInt16("question_count"),
    UBInt16("answer_count"),
    UBInt16("authority_count"),
    UBInt16("additional_count"),
    Array(lambda ctx: ctx.question_count,
        Rename("questions", query_record),
    ),
    Rename("answers", 
        Array(lambda ctx: ctx.answer_count, resource_record)
    ),
    Rename("authorities",
        Array(lambda ctx: ctx.authority_count, resource_record)
    ),
    Array(lambda ctx: ctx.additional_count,
        Rename("additionals", resource_record),
    ),
)


if __name__ == "__main__":
    cap1 = (
    "2624010000010000000000000377777706676f6f676c6503636f6d0000010001"
    ).decode("hex")
    
    cap2 = (
    "2624818000010005000600060377777706676f6f676c6503636f6d0000010001c00c00"
    "05000100089065000803777777016cc010c02c0001000100000004000440e9b768c02c"
    "0001000100000004000440e9b793c02c0001000100000004000440e9b763c02c000100"
    "0100000004000440e9b767c030000200010000a88600040163c030c030000200010000"
    "a88600040164c030c030000200010000a88600040165c030c030000200010000a88600"
    "040167c030c030000200010000a88600040161c030c030000200010000a88600040162"
    "c030c0c00001000100011d0c0004d8ef3509c0d0000100010000ca7c000440e9b309c0"
    "80000100010000c4c5000440e9a109c0900001000100004391000440e9b709c0a00001"
    "00010000ca7c000442660b09c0b00001000100000266000440e9a709"
    ).decode("hex")

    obj = dns.parse(cap1)
    print obj
    print repr(dns.build(obj))
    
    print "-" * 80
    
    obj = dns.parse(cap2)
    print obj
    print repr(dns.build(obj))
    
    


