"""
tcpdump capture file
"""
from construct import *
import time
from datetime import datetime


class MicrosecAdapter(Adapter):
    def _decode(self, obj, context):
        return datetime.fromtimestamp(obj[0] + (obj[1] / 1000000.0))
    def _encode(self, obj, context):
        offset = time.mktime(*obj.timetuple())
        sec = int(offset)
        usec = (offset - sec) * 1000000
        return (sec, usec)

packet = Struct("packet",
    MicrosecAdapter(
        Sequence("time", 
            ULInt32("time"),
            ULInt32("usec"),
        )
    ),
    ULInt32("length"),
    Padding(4),
    HexDumpAdapter(Field("data", lambda ctx: ctx.length)),
)

cap_file = Struct("cap_file",
    Padding(24),
    Rename("packets", OptionalGreedyRange(packet)),
)


if __name__ == "__main__":
    obj = cap_file.parse_stream(open("../../test/cap2.cap", "rb"))
    print len(obj.packets)

















