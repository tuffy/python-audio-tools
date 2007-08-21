.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "Apple Lossless"
.PP
Apple Lossless compresses PCM audio data losslessly in a QuickTime
container.
How a QuickTime container is separated into atoms and sub-atoms
has already been covered in the M4A section, so I will continue
directly to Apple Lossless' atoms.
Everything in it is big-endian.

.bp

.SUBSECTION "the alac atom"
.PP
The \fCalac\fR atom contains information about the Apple Lossless
stream including the sample rate, sample size and residual decoding
parameters.
It is found in the stsd atom.

.PS
define atom {box ht 0.25}
lineht = 0.050;
con_atom "moov";
move to last box .s;
line down then right->;
con_atom "trak";
move to last box .s;
line down then right->;
con_atom "mdia";
move to last box .s;
line down then right->;
con_atom "minf";
move to last box .s;
line down then right->;
con_atom "stbl";
move to last box .s;
line down then right->;
atom "stsd";
.PE

.begin dformat
style bitwid 0.16
style recspread 0
noname
     0-31-6 stsd Length
     32-63-8 `stsd' (0x73747364)
     64-71-3 Version
     72-95-3 Flags
     96-127-8 Total Entries (0x1)
 E1: 128--4-dashed @roman Entry sub 1@
     --4-dashed Sub Atom
noname
     --36-invisible
noname
 E2: 0-31-6 atom Length
     32-63-8 `alac' (0x616C6163)
     64-111-14 Reserved (0x000000000000)
 E3: 112-127-8 Version (0x0000)
noname
     128-143-10 Revision Level (0x0000)
     144-175-16 Vendor (0x00000000)
     176-191-10 Reserved (0x0000)
noname
     192-207-12 Channels
     208-223-12 Sample Size
     224-239-12 Compression ID (0x0000)
noname
     240-255-12 Packet Size
     256-271-12 Sample Rate
     272-287-12 Reserved (0x0000)
noname
     --36-invisible
noname
     0-31-6 atom Length
     32-63-8 `alac' (0x616C6163)
     64-95-10 Reserved
     96-127-12 Maximum Samples per Frame
noname
     128-135-7 7A (0x0)
     136-143-7 Sample Size
     144-151-8 History Multiplier
     152-159-7 Initial History
     160-167-7 Rice Modifier
noname
     168-175-7 7F (0x0)
     176-191-7 80 (0xFF)
     192-223-8 82 (0x4004)
     224-255-7 86
     256-287-7 8A Rate
pic line dotted from E1.sw to E2.nw
pic line dotted from E1.se to E3.ne
.end dformat

.bp

.so codec_alac.ms
