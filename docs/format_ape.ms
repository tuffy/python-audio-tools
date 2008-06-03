.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Monkey's Audio"
.PP
Monkey's Audio is a lossless RIFF WAVE compressor.
Unlike FLAC, which is a PCM compressor, Monkey's Audio also stores
IFF chunks and reproduces the original WAVE file in its entirety rather
than storing only the data it contains.
All of its fields are little-endian.

.SUBSECTION "the Monkey's Audio stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
noname
       0-415-12 APE Descriptor
       416-607-12 APE Header
       --10-dashed Seektable
       --10-dashed Header Data
       --8 @roman Frame sub 1@
       --8 @roman Frame sub 2@
       --8-dashed ...
       --12 APEv2 Tag
.end dformat

.SUBSECTION "the APE Descriptor"
.PP
.begin dformat
style bitwid 0.16
style charwid 0
style recspread 0
noname
  0-31-16 ID (`MAC ' 0x4D414320)
  32-63-16 Version
noname
  64-95-16 Descriptor Bytes
  96-127-16 Header Bytes
noname
  128-159-16 Seektable Bytes
  160-191-16 Header Data Bytes
noname
  192-223-16 Frame Data Bytes
  224-255-16 Frame Data Bytes (High)
noname
  256-287-32 Terminating Data Bytes
noname
  288-415-32 MD5 Sum
.end dformat
Version is the encoding software's version times 1000.
i.e. Monkey's Audio 3.99 = 3990

.SUBSECTION "the APE Header"
.PP
.begin dformat
style bitwid 0.16
style charwid 0
style recspread 0
noname
  0-15-16 Compression Level
  16-31-16 Format Flags
noname
  32-63-32 Blocks Per Frame
noname
  64-95-32 Final Frame Blocks
noname
  96-127-32 Total Frames
noname
  128-143-16 Bits Per Sample
  144-159-16 Channels
noname
  160-191-32 Sample Rate
.end dformat
`Bits Per Sample', `Channels' and `Sample Rate' are self-explanatory.
A `block' refers to a group of samples to be sent across all channels
at any one instant.
For instance, a file with a sample rate of 44100 has exactly 44100 blocks
per second, regardless of the number of channels or bits per sample.
Calculating the total length of the file is a matter of multiplying
the number of frames by the number of blocks per frame and adding
any remaining blocks in the final frame.
.sp 1
@ "Length in Seconds" = {(("Total Frames" - 1)~\[mu]~"Blocks Per Frame") + "Final Frame Blocks"} over "Sample Rate" @

.bp

.KS
.SUBSECTION "the APEv2 tag"
.PP
The APEv2 tag is a little-endian metadata tag appended to Monkey's Audio files.
.begin dformat
style bitwid 0.16
style recspread 0
noname
     0-255-8 Header
 I1: 0--7 @roman Item sub 1@
     --7 @roman Item sub 2@
     --7-dashed ...
     0-255-8 Footer
noname
     --32-invisible
noname
 I2: 0-31-32 Item Value Length
noname
     32-63-32 Flags
noname
     64-?-24 Item Key
     0-7-8 NULL (0x00)
noname
    --32-dashed Item Value
pic line dotted from I1.sw to I2.nw
pic line dotted from I1.se to I2.ne
.end dformat
.PP
Item Key is an ASCII string from the range 0x20 to 0x7E.
Item Value is typically a UTF-8 encoded string, but may
also be binary depending on the Flags.
.ps 8
.TS
tab(:);
| c s s s |
| r | l || r | l |.
_
Item Keys
_
key:value:key:value
=
Abstract:Abstract:Album:album name
Artist:performing artist:Bibliography:Bibliography/Discography
Catalog:catalog number:Comment:user comment
Composer:original composer:Conductor:conductor
Copyright:copyright holder:Debut album:debut album name
Dummy:place holder:EAN/UPC:EAN-13/UPC-A bar code identifier
File:file location:Genre:genre
Index:indexes for quick access:Introplay:characteric part of piece for intro playing
ISBN:ISBN number with check digit:ISRC:International Standard Recording Number
Language:used Language(s) for music/spoken words:LC:Label Code
Media:source media:Publicationright:publication right holder
Publisher:record label or publisher:Record Date:record date
Record Location:record location:Related:location of related information
Subtitle:track subtitle:Title:track title
Track:track number:Year:release date
_
.TE
.ps 10
.KE

.bp

.KS
.SUBSECTION "the APEv2 tag header/footer"
.PP
.begin dformat
style bitwid 0.18
style recspread
noname
    0-63-32 Preamble (`APETAGEX' 0x4150455441474558)
noname
    64-95-16 Version (0xD0070000)
    96-127-16 Tag Size
noname
    128-159-16 Item Count
    160-191-16 Flags
noname
    192-255-32 Reserved
.end dformat
.KE
The format of the APEv2 header and footer are identical
except for one of the flags.
`Version' is typically 2000 (stored little-endian).
`Tag Size' is the size of the entire APEv2 tag, including the
footer but excluding the header.
`Item Count' is the number of individual tag items.

.SUBSECTION "the APEv2 flags"
.PP
The `Flags' field is used by both the APEv2 header/footer and the
individual tag items.
.begin dformat
style bitwid 0.64
style recspread 0
noname
  0-4-5 Undefined (0x00)
  5-6-2 Encoding
  7-7-1 Read-Only
noname
  8-15-8 Undefined (0x00)
noname
  16-23-8 Undefined (0x00)
noname
  24-24-2 Container Header
  25-25-2  Contains no Footer
  26-26-2 Is Header
  27-31-2 Undefined (0x00)
.end dformat

.TS
tab(:);
| c s |
| c | l |.
_
Encoding
_
bits:value
=
00:UTF-8
01:Binary
10:External Link
11:Reserved
_
.TE
