.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "Ogg Vorbis"
.PP
Ogg Vorbis is Vorbis audio in an Ogg container.
Ogg containers are a series of Ogg pages, each containing
one or more segments of data.
All of the fields within Ogg Vorbis are little-endian.

.SUBSECTION "the Ogg file stream"
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
       0--16 Ogg @roman Page sub 1@
       --16 Ogg @roman Page sub 2@
       --16-dashed ...
       --16 Ogg @roman Page sub n@
.end dformat

.SUBSECTION "an Ogg page"
.PP
.begin dformat
style bitwid 0.64
style recspread 0
noname
  0-31-8 Magic Number `OggS' (0x4F676753)
noname
  32-39-4 Version (0x00)
  40-47-4 Header Type
noname
  48-111-8 Granule Position
noname
  112-143-8 Bitstream Serial Number
noname
  144-175-8 Page Sequence Number
noname
  176-207-8 Checksum
noname
  208-215-2 Page Segments
  216-223-2 Segment @roman Length sub 1@
  224-231-2 Segment @roman Length sub 2@
  232--2-dashed ...
noname
  --8 @roman Segment sub 1@
noname
  --8 @roman Segment sub 2@
noname
  --8-dashed ...
.end dformat
.2C
.TS
tab(:);
| c s |
| c | l |
| c | l |.
_
Header Type
_
bits:page type
=
001:Continuation
010:Beginning of Stream
100:End of Stream
_
.TE
Granule position is a time marker.
In the case of Ogg Vorbis, it is the sample count.

Bitstream Serial Number is an identifier for the given
bitstream which is unique within the Ogg file.
For instance, an Ogg file might contain both video and
audio pages, interleaved.
The Ogg pages for the audio will have a different
serial number from those of the video so that the decoder
knows where to send the data of each.

Page sequence number is an integer counter which starts from 0
and increments 1 for each Ogg page.
Multiple bitstreams will have separate sequence numbers.

Checksum is a 32-bit checksum of the entire Ogg page.

The Page Segments value indicates how many segments are in
this Ogg page.
Each segment will have an 8-bit length.
If that length is 255, it indicates the next segment is
part of the current one and should be concatenated with it when
creating packets from the segments.
In this way, packets larger than 255 bytes can be stored in
an Ogg page.
If the final segment in the Ogg page has a length of 255 bytes,
the packet it is a part of continues into the next Ogg page.
.1C

.bp

.SUBSECTION "Ogg packets" 
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
  A1: --20 Ogg @roman Page sub 1@
  A2: --20 Ogg @roman Page sub 2@
  A3: --20 Ogg @roman Page sub 3@
      --20-dashed ...
noname
  B1: 30B-30B-10 @roman Segment sub 1@
      --4-invisible
  B2: 255B-255B-10 @roman Segment sub 2@
      255B-255B-10 @roman Segment sub 3@
      255B-255B-10 @roman Segment sub 4@
  B3: 255B-255B-10 @roman Segment sub 5@
      --4-invisible
  B4: 40B-40B-10 @roman Segment sub 6@
  B5: 60B-60B-10 @roman Segment sub 7@
noname
  C1: 30B-30B-21 @roman Packet sub 1@
  --8-invisible
  C2: 1060B-1060B-21 @roman Packet sub 2@
  --8-invisible
  C3: 60B-60B-21 @roman Packet sub 3@
pic line dotted from A1.sw to B1.nw
pic line dotted from A1.se to B1.ne
pic line dotted from A2.sw to B2.nw
pic line dotted from A2.se to B3.ne
pic line dotted from A3.sw to B4.nw
pic line dotted from A3.se to B5.ne
pic line dotted from B1.sw to C1.nw
pic line dotted from B1.se to C1.ne
pic line dotted from B2.sw to C2.nw
pic line dotted from B4.se to C2.ne
pic line dotted from B5.sw to C3.nw
pic line dotted from B5.se to C3.ne
.end dformat
This is an example Ogg stream to illustrate a few key points about
the format.
Note that Ogg pages may have one or more segments,
and packets are composed of one of more segments,
yet the boundaries between packets are segments
that are less than 255 bytes long.
Which segment belongs to which Ogg page is not important
for building packets.

.SUBSECTION "the Identification packet"
.PP
The first packet within a Vorbis stream is the Identification packet.
This contains the sample rate and number of channels.
Vorbis does not have a bits-per-sample field, as samples
are stored internally as floating point values and are
converted into a certain number of bits in the decoding process.
To find the total samples, use the Granule Position value
in the stream's final Ogg page.
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-7-5 Type (0x01)
    8-55-27 Header `vorbis' (0x766F72626973)
noname
    56-87-27 Vorbis version (0x00000000)
    88-95-5 Channels
noname
    96-127-32 Sample Rate
noname
    128-159-32 Maximum Bitrate
noname
    160-191-32 Nominal Bitrate
noname
    192-223-32 Minimum Bitrate
noname
    224-227-6 @roman Blocksize sub 0@
    228-231-6 @roman Blocksize sub 1@
    232-239-20 Framing flag (0x01)
.end dformat

.bp

.SUBSECTION "the Comment packet"
.PP
The second packet within a Vorbis stream is the Comment packet.
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
       0-7-9 Type (0x03)
       8-55-32 Header `vorbis' (0x766F72626973)
  A1:  56--28 Comment Data
       0-7-11 Framing (0x1)
noname
  VS:  --16 Vendor String
       0-31-16 Total Comments
       --16 Comment @roman String sub 1@
  CS:  --16 Comment @roman String sub 2@
  EN:   --16-dashed ...
noname
  S1:  0-31-18 Vendor String Length
  S2:  32-?-18 Vendor String
       --6-invisible
  S3:  0-31-18 Comment String Length
  S4:  32-?-18 Comment String
pic line dotted from A1.sw to VS.nw
pic line dotted from A1.se to EN.ne
pic line dotted from VS.sw to S1.nw
pic line dotted from VS.se to S2.ne
pic line dotted from CS.sw to S3.nw
pic line dotted from CS.se to S4.ne
.end dformat

.so format_vorbiscomment.ms

