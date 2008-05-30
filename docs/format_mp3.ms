.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "MP3"
.PP
MP3 is the de-facto standard for lossy audio.
It is little more than a series of MPEG frames with an
optional ID3v2 metadata header and optional ID3v1 metadata
footer.
.PP
MP3 decoders are assumed to be very tolerant of anything in
the stream that doesn't look like an MPEG frame, ignoring such
junk until the next frame is found.
Since MP3 files have no standard container format in which
non-MPEG data can be placed, metadata such as ID3 tags are often
made `sync-safe' by formatting them in a way that decoders won't
confuse tags for MPEG frames.

.SUBSECTION "the MP3 file stream"
.PP
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
       0--16 ID3v2 Metadata
       --16 MPEG @roman Frame sub 1@
       --16 MPEG @roman Frame sub 2@
       --16-dashed ...
       --16 ID3v1 Metadata
.end dformat
.bp
.SUBSECTION "an MPEG frame header"
.PP
.begin dformat
style bitwid 0.64
style recspread 0
noname
    0-7-8 Frame Sync (all set)
noname
    8-10-3 Frame Sync
    11-12-2 MPEG ID
    13-14-2 Layer Description
    15-15-1 Prot.
noname
    16-19-4 Bitrate
    20-21-2 Sampling
    22-22-1 Pad
    23-23-1 Private
noname
    24-25-2 Channel
    26-27-2 Mode Extension
    28-28-1 Copyright
    29-29-1 Original
    30-31-2 Emphasis
.end dformat
.PP
.ps 8
Layer I frames always contain 384 samples.
.PP
.ps 8
Layer II and Layer III frames always contain 1152 samples.
.PP
.ps 8
To find the total size of an MPEG frame, use one of the following
formulas:
.RS
.IP \(bu
Layer I	: @ Byte~Length = left ({12 * Bitrate} over {Sampling} + Pad right )~~*~~4 @
.IP
.IP \(bu
Layer II/III	: @ Byte~Length = {144 * Bitrate} over {Sampling} + Pad @
.RE
.PP
.2C
.ps 8
For example, an MPEG-1 Layer III frame with a sampling rate of 44100, 
a bitrate of 128kbps and a set pad bit is 418 bytes long, including the header.
.PP
.ps 8
@ 418 = {144 * 128000} over {44100} + 1 @
.ps 8
.KS
.TS
tab(:);
| c s || c s |
| c | l || c | l |
| c | l || c | l |.
_
MPEG ID:Layer Description
_
bits:version:bits:layer
=
00:MPEG 2.5:00:reserved
01:reserved:01:Layer III
10:MPEG 2:10:Layer II
11:MPEG 1:11:Layer I
_
.TE
.KE
.ps 8
If the `Protection' bit is set, the frame header is followed by a
16 bit CRC.
.KS
.TS
tab(:);
| c s s s |
| c | c | c | c |
| c | r | r | r |.
_
Sampling
_
bits:MPEG-1:MPEG-2:MPEG-2.5
=
00:44100:22050:11025
01:48000:24000:12000
10:32000:16000:8000
11:reserved:reserved:reserved
_
.TE
.KE
.KS
.TS
tab(:);
| c s |
| c | l |.
_
Channel
_
bits:type
=
00:Stereo
01:Joint stereo
10:Dual channel stereo
11:Mono
_
.TE
.KE
.KS
.TS
tab(:);
| c s s s s s |
| c | c | c | c | c | c |
| c | r | r | r | r | r |.
_
Bitrate \s6(in 1000 bits per second)\s0
_
bits:MPEG-1:MPEG-1:MPEG-1:MPEG-2:MPEG-2
\^:Layer-1:Layer-2:Layer-3:Layer-1:Layer-2/3
=
0000:free:free:free:free:free
0001:32:32:32:32:8
0010:64:48:40:48:16
0011:96:56:48:56:24
0100:128:64:56:64:32
0101:160:80:64:80:40
0110:192:96:80:96:48
0111:224:112:96:112:56
1000:256:128:112:128:64
1001:288:160:128:144:80
1010:320:192:160:160:96
1011:352:224:192:176:112
1100:384:256:224:192:128
1101:416:320:256:224:144
1110:448:384:320:256:160
1111:bad:bad:bad:bad:bad
_
.TE
.KE
.ps 10
.1C
.bp
.so format_xing.ms
.bp
.so format_id3v1.ms
.bp
.so format_id3v2.ms
