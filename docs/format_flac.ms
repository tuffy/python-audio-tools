.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "FLAC"
.PP
FLAC is the Fully Lossless Audio Codec.
It compresses PCM audio data losslessly using predictors and a residual.
FLACs are smaller than WAVEs, contain checksumming to verify their
integrity, contain comment tags for metadata and are streamable.
.PP
Except for the contents of the VORBIS_COMMENT metadata block, 
everything in FLAC is big-endian.

.SUBSECTION "the FLAC file stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
       0-31-24 Header (`fLaC' 0x664C6143)
  FD1: 32--8 @roman Metadata sub 1@
       --8 @roman Metadata sub 2@
       --8-dashed ...
       --8 @roman Frame sub 1@
       --8 @roman Frame sub 2@
       --8-dashed ...
noname
  FD2: 0-0-5 Last
       1-7-10 Block Type
       8-31-24 Block Length
  FD3: 32--24-dashed Block Data
pic line dotted from FD1.sw to FD2.nw
pic line dotted from FD1.se to FD3.ne
.end dformat
"Last" is 0 when there are additional metadata blocks and
1 when it is the final block before the the audio frames.
"Block Length" is the size of the metadata block data to follow,
not including the header.
.sp
.TS
tab(:);
| c s |
| c | c |
| r | l |.
_
Block Types
_
value:type
=
0:STREAMINFO
1:PADDING
2:APPLICATION
3:SEEKTABLE
4:VORBIS_COMMENT
5:CUESHEET
6:PICTURE
7-126:reserved
127:invalid
_
.TE
.bp
.SUBSECTION "FLAC metadata"

.SUBSUBSECTION "the PADDING metadata block"
.PP
Padding is simply a block full of NULL (0x00) bytes.
Its purpose is to provide extra metadata space within
the FLAC file.
By having a padding block, other metadata blocks can
be grown or shrunk without having to rewrite the entire
FLAC file by removing or adding space to the padding.

.SUBSUBSECTION "the APPLICATION metadata block"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
  0-31-16 Application ID
  32--48 Application Data
.end dformat
Application data is a general-purpose metadata block
used by a variety of different programs.
Its contents are defined by the ID.
.SUBSUBSECTION "the SEEKTABLE metadata block"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0
noname
  P1:  0-143-16 @ roman Seekpoint sub 1 @
       144-287-16 @ roman Seekpoint sub 2 @
       --16-dashed ...
       --16 @ roman Seekpoint sub n @
noname
       --64-invisible
noname
  P2:  0-63-64 Sample Number in Target Frame
noname
       64-127-64 Byte Offset to Frame Header
noname
       128-143-32 Samples in Target Frame
pic line dotted from P1.sw to P2.nw
pic line dotted from P1.se to P2.ne
.end dformat

.SUBSUBSECTION "the STREAMINFO metadata block"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-15-16 Minimum Block Size (in samples)
    16-31-16 Maximum Block Size (in samples)
noname
    32-55-16 Minimum Frame Size (in bytes)
    56-79-16 Maximum Frame Size (in bytes)
noname
    80-99-18 Sample Rate
    100-102-6 Channels
    103-107-8 Bits Per Sample
noname
    108-143-32 Total Samples
noname
    144-271-32 MD5 Sum of PCM Data
.end dformat

.bp

.KS
.SUBSUBSECTION "the VORBIS_COMMENT metadata block"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
  VS:  --16 Vendor String
       0-31-16 Total Comments
       --16 Comment @roman String sub 1@
  CS:  --16 Comment @roman String sub 2@
       --16-dashed ...
noname
  S1:  0-31-18 Vendor String Length
  S2:  32-?-18 Vendor String
       --6-invisible
  S3:  0-31-18 Comment String Length
  S4:  32-?-18 Comment String
pic line dotted from VS.sw to S1.nw
pic line dotted from VS.se to S2.ne
pic line dotted from CS.sw to S3.nw
pic line dotted from CS.se to S4.ne
.end dformat

.so format_vorbiscomment.ms
.KE

.KS
.SUBSUBSECTION "the PICTURE metadata block"
.PP
.begin dformat
style bitwid 0.05
style charwid 0
style recspread 0.3
noname
      0-31-16 Picture Type
 M1:  31--16 MIME
 S1:  --16 Description
      0-31-16 Width
      32-63-16 Height
      64-95-16 Color Depth
      96-127-16 Color Count
 D1:  128--16 Data
noname
 M2:  0-31-16 String Length
 M3:  32--16 String Data
      --8-invisible
 S2:  0-31-16 String Length
 S3:  32--16 String Data
      --8-invisible
 D2:  0-31-24 Picture Data Length
 D3:  32--24 Picture Data
pic line dotted from M1.sw to M2.nw
pic line dotted from M1.se to M3.ne
pic line dotted from S1.sw to S2.nw
pic line dotted from S1.se to S3.ne
pic line dotted from D1.sw to D2.nw
pic line dotted from D1.se to D3.ne
.end dformat

.ps 8
.TS
tab(:);
| c s s s | 
| r | l || r | l |.
_
Picture Types
_
value:type:value:type
=
0:Other:1:32x32 pixels `file icon' (PNG only)
2:Other file icon:3:Cover (front)
4:Cover (back):5:Leaflet page
6:Media (e.g. label side of CD):7:Lead artist / Lead performer / Soloist
8:Artist / Performer:9:Conductor
10:Band / Orchestra:11:Composer
12:Lyricist / Text writer:13:Recording location
14:During recording:15:During performance
16:Movie / Video screen capture:17:A bright coloured fish
18:Illustration:19:Band / Artist logotype
20:Publisher / Studio logotype
_
.TE
.ps 10
.KE

.SUBSUBSECTION "the CUESHEET metadata block"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
      0-1023-16 Catalog Number
      1024-1087-16 Lead-in Samples
      1088-1088-8 is CDDA
      1089-3159-12 NULL (0x00)
      3160-3167-12 Track Count
  T1: 3168--8 @ roman Track sub 1 @
      --8-dashed ...
noname
  T2: 0-63-12 Track Offset
      64-71-12 Track Number
      72-167-7 ISRC
      168-168-7 Type
      169-169-8 Pre-Emph.
      170-279-11 NULL (0x00)
      280-287-10 Index Points
  I1: 288--8 @roman Index sub 1 @
  T3: --8-dashed ...
noname
      --40-invisible
  I2: 0-63-12 Index Offset
      64-71-12 Index Number
  I3: 72-95-12 NULL (0x00)
pic line dotted from T1.sw to T2.nw
pic line dotted from T1.se to T3.ne
pic line dotted from I1.sw to I2.nw
pic line dotted from I1.se to I3.ne
.end dformat
.bp
.so codec_flac.ms
