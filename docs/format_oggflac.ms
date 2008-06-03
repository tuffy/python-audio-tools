.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Ogg FLAC"
.PP
Ogg FLAC is a FLAC audio stream in an Ogg container.
Although it contains all the features of native FLAC,
Ogg FLAC is rarely used as a standalone audio format.
It is more useful when interleaved with an Ogg video stream
so that a movie can be presented with lossless audio.
However, this section will only deal with Ogg FLAC.
.SUBSECTION "the Ogg FLAC file stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
  A1: --13 Ogg Page
  A2: --13 Ogg Page
      --8-dashed ...
  A3: --13 Ogg Page
      --8-dashed ...
  A4: --13 Ogg Page
      --8-dashed ...
noname
  B1: --13 Segment
      --1-invisible
  B2: --10 Segment
  B3: --10 Segment
      --1-invisible
  B4: --10 Segment
  B5: --10 Segment
      --1-invisible
  B6: --10 Segment
  B7: --10 Segment
noname
  C1:  --13 STREAMINFO
  C2:  --13 Vorbis Comment
       --8 @roman Metadata sub 3@
  C4:  --8 @roman Metadata sub 4@
       --9-dashed ...
       --8 @roman Frame sub 1@
  C5:  --8 @roman Frame sub 2@
       --9-dashed ...
pic line dotted from A1.sw to B1.nw
pic line dotted from A1.se to B1.ne
pic line dotted from B1.sw to C1.nw
pic line dotted from B1.se to C1.ne
pic line dotted from A2.sw to B2.nw
pic line dotted from A2.se to B3.ne
pic line dotted from B2.sw to C2.nw
pic line dotted from B3.se to C2.ne
pic line dotted from A3.sw to B4.nw
pic line dotted from A3.se to B5.ne
pic line dotted from B4.sw to C4.nw
pic line dotted from B5.se to C4.ne
pic line dotted from A4.sw to B6.nw
pic line dotted from A4.se to B7.ne
pic line dotted from B6.sw to C5.nw
pic line dotted from B7.se to C5.ne
.end dformat
.SUBSECTION "the STREAMINFO metadata packet"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-7-8 Packet Byte (0x7F)
    8-39-24 Signature `FLAC' (0x464C4143)
noname
    40-47-16 Major Version (0x1)
    48-55-16 Minor Version (0x0)
noname
    56-71-8 Header Packets
    72-103-24 FLAC Signature `fLaC' (0x664C6143)
noname
    104-104-8 Last Block (0)
    105-111-8 Block Type (0x0)
    112-135-16 Block Length
noname
    136-151-16 Minimum Block Size (in samples)
    152-167-16 Maximum Block Size (in samples)
noname
    168-191-16 Minimum Frame Size (in bytes)
    192-215-16 Maximum Frame Size (in bytes)
noname
    216-235-18 Sample Rate
    236-238-6 Channels
    239-243-8 Bits Per Sample
noname
    244-279-32 Total Samples
noname
    280-407-32 MD5 Sum of PCM Data
.end dformat
.SUBSECTION "the Metadata packets"
.PP
Subsequent FLAC metadata blocks are stored 1 per packet.
Each contains the 32-bit FLAC metadata block header
in addition to the metadata itself.
The VORBIS_COMMENT metadata block is required to immediately
follow the STREAMINFO block, but all others may appear in
any order.

