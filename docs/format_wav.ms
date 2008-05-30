.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "RIFF WAVE"
.PP
RIFF WAVE is the most common form of PCM container.
What that means is that the file is mostly PCM data with a
small amount of header data to tell applications what format the
PCM data is in.
Since RIFF WAVE originated on Intel processors, everything in it
is little-endian.
.SUBSECTION "the RIFF WAVE stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
       0-31-24 Chunk ID (`RIFF' 0x52494646)
       32-63-24 Chunk Size (file size - 8)
  WD1: 64--24 Chunk Data
noname
  WD2: 64-95-24 RIFF Type (`WAVE' 0x57415645)
  WC1: 96--16 @roman Chunk sub 1@
       --16 @roman Chunk sub 2@
  WD3: --16-dashed ...
noname
  WC2: 0-31-24 Chunk ID (ASCII Text)
       32-63-24 Chunk Size
  WC3: 64--24-dashed Chunk Data
pic line dotted from WD1.sw to WD2.nw
pic line dotted from WD1.se to WD3.ne
pic line dotted from WC1.sw to WC2.nw
pic line dotted from WC1.se to WC3.ne
.end dformat

`Chunk Size' is the total size of the chunk, minus
8 bytes for the chunk header.

.SUBSECTION "the fmt chunk"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-32 Chunk ID (`fmt ' 0x666D7420)
noname
    32-63-32 Chunk Size (16 + extra)
noname
    64-79-16 Compression Code (0x0001)
    80-95-16 Number of Channels
noname
    96-127-32 Sample Rate
noname
    128-159-32 Average Bytes Per Second
noname
    160-175-16 Block Align
    176-191-16 Bits Per Sample
noname
    192-207-16-dashed Extra Format Byte Count
    208--16-dashed Extra Format Bytes
.end

.ps 8
@ "Average Bytes Per Second" = "Sample Rate"~\[mu]~"Number of Channels"~\[mu]~"Bits Per Sample"~\[di]~8 @
.br
@ "Block Align" = "Number of Channels"~\[mu]~"Bits Per Sample"~\[di]~8 @
.ps

.SUBSECTION "the data chunk"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-32 Chunk ID (`data' 0x64617461)
noname
    32-63-32 Chunk Size
noname
    64--32 PCM Data
.end

`PCM Data' is a stream of PCM samples stored in little-endian format.
