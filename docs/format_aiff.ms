.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "AIFF"
.PP
AIFF is the Audio Interchange File Format.
It is popular on Apple computers and is a precursor to the more
widespread WAVE format.
All values in AIFF are stored as big-endian.
.SUBSECTION "the AIFF stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
       0-31-24 Chunk ID (`FORM' 0x464F524D)
       32-63-24 Chunk Size (file size - 8)
  WD1: 64--24  Chunk Data
noname
  WD2: 64-95-24 RIFF Type (`AIFF' 0x41494646)
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

.SUBSECTION "the COMM chunk"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-32 Chunk ID (`COMM' 0x434F4D4D)
noname
    32-63-32 Chunk Size (18)
noname
    64-79-8 Channels
    80-111-16 Total Sample Frames
    112-127-8 Sample Size
noname
    128-207-32 Sample Rate
.end

The Sample Rate field is an 80-bit IEEE Standard 754 floating point value
instead of the big-endian integers common to all the other fields.

.SUBSECTION "the SSND chunk"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-32 Chunk ID (`SSND' 0x53534E44)
noname
    32-63-32 Chunk Size
noname
    64--32 PCM Data
.end
