.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "WavPack"
.PP
WavPack is a lossless audio format.
It is a sequence of WavPack audio blocks followed by
an optional APEv2 tag.
All of its fields are little-endian.

.SUBSECTION "the WavPack file stream"
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
  0--16 WavPack @roman Block sub 1@
  --16 WavPack @roman Block sub 2@
  --16-dashed ...
  --16 WavPack @roman Block sub n@
  --16-dashed APEv2 Tag
.end dformat

.bp

.SUBSECTION "a WavPack block"
.PP
.begin dformat
style bitwid 0.64
style recspread 0
noname
  0-31-8 Block ID `wvpk' (0x7776706B)
noname
  32-63-8 Block Size
noname
  64-79-4 Version
  80-87-2 Track Number
  88-95-2 Index Number
noname
  96-127-8 Total Samples
noname
  128-159-8 Block Index
noname
  160-191-8 Block Samples
noname
  192-192-2 Floating Point Data
  193-193-2 Hybrid Noise Shaping
  194-194-2 Channel Decorrelation
  195-195-2 Joint Stereo
noname
  196-196-2 Hybrid Mode
  197-197-2 Mono Output
  198-199-4 Bits-per-Sample
noname
  200-202-6 Left Shift Data (low)
  203-203-2 Final Block
noname
  204-204-2 Initial Block
  205-205-2 Hbd. Noise Balanced
  206-206-2 Hbd. Controls Bitrate
  207-207-2 Extended Size Integers
noname
  208-208-2 Sampling Rate (low)
  209-211-6 Maximum Magnitude
noname
  212-213-4 Maximum Magnitude (cont.)
  214-215-4 Left Shift Data (high)
noname
  216-216-2 Reserved
  217-217-2 False Stereo
  218-218-2 Use IIR
  219-219-2 Reserved
noname
  220-220-2 Reserved
  221-223-6 Sampling Rate (high)
noname
  224-255-8 CRC
.end dformat

.PP
.2C
.KS
.TS
tab(:);
| c s |
| c | r |.
_
Bits-per-Sample
_
bits:per-sample
=
00:8
01:16
10:24
11:32
_
.TE
.KE
.KS
.TS
tab(:);
| c s s s |
| c | r || c | r |.
_
Sampling Rate
_
bits:rate:bits:rate
=
0000:6000:1000:32000
0001:8000:1001:44100
0010:9600:1010:48000
0011:11025:1011:64000
0100:12000:1100:88200
0101:16000:1101:96000
0110:22050:1110:192000
0111:24000:1111:reserved
_
.TE
.KE
.KS
.PP
.ps 8
The `flags' field is stored as a little-endian 32-bit integer.
Since some fields cross byte boundaries, their high and low bits
will be far apart when written in this format where the bits are
ordered the way they appear in the file.
.ps
.KE
.KS
.PP
.ps 8
The `Mono Output' bit indicates the channel count.
If 1, this block has 1 channel.
If 0, this block has 2 channels. 
For an audio stream with more than 2 channels,
check the `Initial Block' and `Final Block' bits to indicate
the start and end of the channels.  As an example:
.ps
.KE
.ps 8
.TS
tab(:);
c | c | c | c
c | c | c | c
c | c | c | c
c | c | c | c
c | c | c | c
r s s | c.
Initial Block:Final Block:Mono Output:Channels
=
1:0:0:2
0:0:1:1
0:0:1:1
0:1:0:2
_
Total:6
.TE
.1C
