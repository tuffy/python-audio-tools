"""
ISDN User Part (SS7 protocol stack)
"""
from construct import *


isup_header = Struct("isup_header",
    Bytes("routing_label", 5),
    UBInt16("cic"),
    UBInt8("message_type"),
    # mandatory fixed parameters
    # mandatory variable parameters
    # optional parameters
)

