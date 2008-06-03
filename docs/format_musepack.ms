.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Musepack"
.PP
Musepack is a lossy audio format based on MP2 and designed for
transparency.
It comes in two varieties: SV7 and SV8 where `SV' stands for
Stream Version.
These container versions differ so heavily that they must be
considered separately from one another.
.SUBSECTION "Musepack SV7"
.PP
This is the earliest version of Musepack with wide support.
All of its fields are little-endian.
.SUBSUBSECTION "the Musepack SV7 file stream"
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
       0-223-20 Musepack header
       224--16 @roman Frame sub 1@
       --16 @roman Frame sub 2@
       --16-dashed ...
       --16 APEv2 tag
.end dformat
.SUBSUBSECTION "the Musepack SV7 header"
.PP
.begin dformat
style bitwid 0.32
style recspread 0
noname
  0-23-12 Signature (`MP+' 0x4D502B)
  24-31-4 Version (0x07)
noname
  32-63-16 Frame Count
noname
  64-79-16 Max Level
noname
  80-83-8 Profile
  84-85-4 Link
  86-87-4 Sample Rate
noname
  88-88-3 Intensity Stereo
  89-89-3 Midside Stereo
  90-95-10 Max Band
noname
  96-111-8 Title Gain
  112-127-8 Title Peak
noname
  128-143-8 Album Gain
  144-159-8 Album Peak
noname
  160-175-16 Unusued (0x00)
noname
  176-179-8 Last Frame Samples (low)
  180-180-3 True Gapless
  181-183-5 Unusued (0x00)
noname
  184-184-3 Fast Seeking
  185-191-13 Last Frame Samples (high)
noname
  192-215-10 Unknown
  216-223-6 Encoder Version
.end dformat
Each frame contains 1152 samples per channel.
Therefore:
.br
@"Total Samples" = (("Frame Count" - 1)~\[mu]~1152) + "Last Frame Samples"@
.br
Musepack files always have exactly 2 channels and always have
16 bits per sample.
.2C
.TS
tab(:);
| c s |
| c | c |
| c | r |.
_
Sampling Rate
_
bits:rate
=
00:44100
01:48000
10:37800
11:32000
_
.TE
.KS
.ps 8
.TS
tab(:);
| c s s s |
| c | c || c | c |
| c | l || c | l |.
_
Profile
_
bits:used profile:bits:used profile
=
0000:no profile:0001:Unstable/Experimental
0010:unused:0011:unusued
0100:unusued:0101:below Telephone
0110:below Telephone:0111:Telephone
1000:Thumb:1001:Radio
1010:Standard:1011:Xtreme
1100:Insane:1101:Braindead
1110:above Braindead:1111:above Braindead
_
.TE
.ps
.KE
.1C
.bp
.SUBSECTION "Musepack SV8"
.PP
This is the latest version of the Musepack stream.
All of its fields are big-endian.
.SUBSUBSECTION "the Musepack SV8 file stream"
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
       0-31-24 `MPCK' (0x4D50434B)
 A1:   32--16 @roman Packet sub 1@
       --16 @roman Packet sub 2@
       --16-dashed ...
       --16 APEv2 tag
noname
       --16-invis
 B1:   0-15-12 Key
       16-?-12 Length
 B2:   --20 Value
pic line dotted from A1.sw to B1.nw
pic line dotted from A1.se to B2.ne
.end dformat
`Key' is a two character uppercase ASCII string
(i.e. each digit must be between the characters 0x41 and 0x5A, inclusive).
`Length' is a variable length field indicating the size of the entire packet,
including the header.
This is a Nut-encoded field whose total size depends on whether
the eighth bit of each byte is 0 or 1.
The remaining seven bits of each byte combine to form the field's value,
which is big-endian.
.SUBSUBSECTION "Nut-encoded values"
.PP
.begin dformat
style bitwid 0.14
style recspread 0.1
1.
     0-0-1 0
     1-7-7 Value
     --6-invisible 0 to @2 sup 7 - 2@
2.
     0-0-1 1
     1-7-7 @roman Value sub 1@
     --1-invisible
     8-8-1 0
     9-15-7 @roman Value sub 2@
     --6-invisible 0 to @2 sup 14 - 2@
3.
     0-0-1 1
     1-7-7 @roman Value sub 1@
     --1-invisible
     8-8-1 1
     9-15-7 @roman Value sub 2@
     --1-invisible
     16-16-1 0
     17-23-7 @roman Value sub 3@
     --6-invisible 0 to @2 sup 21 - 2@
4.
     0-0-1 1
 F1: 1-7-7 @roman Value sub 1@
     --1-invisible
     8-8-1 1
 F2: 9-15-7 @roman Value sub 2@
     --1-invisible
     16-16-1 1
 F3: 17-23-7 @roman Value sub 3@
     --1-invisible
     24-24-1 0
 F4: 25-31-7 @roman Value sub 4@
     --6-invisible 0 to @2 sup 28 - 2@
noname
     --4-invisible
 V1: 0-6-7 @roman Value sub 1@
 V2: 7-13-7 @roman Value sub 2@
 V3: 14-20-7 @roman Value sub 3@
 V4: 21-27-7 @roman Value sub 4@
     --7-invisible \[<-] Actual Value
pic line dotted from F1.sw to V1.nw
pic line dotted from F1.se to V1.ne
pic line dotted from F2.sw to V2.nw
pic line dotted from F2.se to V2.ne
pic line dotted from F3.sw to V3.nw
pic line dotted from F3.se to V3.ne
pic line dotted from F4.sw to V4.nw
pic line dotted from F4.se to V4.ne
.end dformat
.SUBSUBSECTION "the SH packet"
.PP
This is the Stream Header, which must be found before the first
audio packet in the Musepack file.
.begin dformat
style bitwid 0.64
style recspread 0
noname
    0-31-8 CRC32
noname
    32-37-2 Version (0x8)
    38-?-3 Sample Count
    --3 Beginning Silence
noname
    0-2-3 Sample Rate
    3-7-5 Max Used Bands
noname
    8-11-3 Channels
    12-12-2 Mid Side Used
    13-15-3 Frame Count
.end dformat
.2C
`CRC32' is a checksum of everything in the header, not including the
checksum itself.
`Sample Count' is the total number of samples, as a Nut-encoded value.
`Beginning Silence' is the number of silence samples at the start
of the stream, also as a Nut-encoded value.
`Channels' is the total number of channels in the stream, minus 1.
`Mid Side Used' indicates the channels are stored using mid-side stereo.
`Frame Count' is used to calculate the total number of frames per
audio packet
(@"Number of Frames" = 4 sup "Frame Count"@).
.KS
.ps 8
.TS
tab(:);
| c s s s|
| c | c || c | c |
| c | r || c | r |.
_
Sampling Rate
_
bits:rate:bits:rate
=
000:44100:001:48000
010:37800:011:32000
_
.TE
.ps
.KE
.1C
.SUBSUBSECTION "the SE packet"
.PP
This is an empty packet that denotes the end of the Musepack stream.
A decoder should ignore everything after this packet, which allows
for metadata tags such as APEv2 to be placed at the end of the file.
.SUBSUBSECTION "the RG packet"
.PP
This is ReplayGain information about the audio file.
.begin dformat
style bitwid 0.64
style recspread 0
noname
    0-7-2 Version (0x1)
noname
    8-23-4 Title Gain
    24-39-4 Title Peak
noname
    40-55-4 Album Gain
    56-71-4 Album Peak
.end dformat
.SUBSUBSECTION "the EI packet"
.PP
This is information about the Musepack encoder.
.begin dformat
style bitwid 0.64
style recspread 0
noname
    0-6-3 Profile
    7-7-1 PNS
    8-15-4 Major Version
noname
    16-23-4 Minor Version
    24-31-4 Build
.end dformat
