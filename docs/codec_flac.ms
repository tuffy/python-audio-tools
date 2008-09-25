.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SUBSECTION "FLAC decoding"
.nr ZF \n%
.PP
A FLAC stream is made up of individual FLAC frames, as follows:
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0
noname
  0-13-42 Sync Code (0x3FFE)
  14-14-15 Reserved (0x0)
  15-15-15 Blocking Strategy
noname
  16-19-17 Block Size
  20-23-17 Sample Rate
  24-27-17 Channel Assignment
  28-30-14 Bits Per Sample
  31-31-7 Padding
noname
  32-39\[hy]87-20 Sample/Frame Number
  0-7/15-20-dashed Block Size
  0-7/15-20-dashed Sample Rate
  0-7-12 CRC-8
noname
 S1: --18 @roman Subframe sub 1@
      --18 @roman Subframe sub 2@
      --18-dashed ...
      --6-dashed Padding
      0-15-12 CRC-16
noname
  --72-invis
noname
 S2: 0-0-6 Padding
      1-6-46 Subframe Type
 S3: 7--20 Wasted Bits Per Sample
noname
     --72-dashed Subframe Data
pic line dotted from S1.sw to S2.nw
pic line dotted from S1.se to S3.ne
.end dformat
.ps 7
.TS
tab(:);
| c || c || c || c s || c |
| c || c || c || c l || c |
| c || l || l || c | l || c |.
_
Bits:Block Size:Sample Rate:Channel Assignment:Bits
\^:(in samples):\^:channels:assignment:\^
=
0000:get from STREAMINFO:get from STREAMINFO:1:mono:0000
0001:192:88200:2:left, right:0001
0010:576:176400:3:left, right, center:0010
0011:1152:192000:4:left, right, back left, back right:0011
0100:2304:8000:5:left, right, center, back left, back right:0100
0101:4608:16000:6:left, right, center, LFE, back left, back right:0101
0110:8 bit from end of header (+1):22050:7:undefined:0110
0111:16 bit from end of header (+1):24000:8:undefined:0111
1000:256:32000:2:0 left, 1 difference:1000
1001:512:44100:2:0 difference, 1 right:1001
1010:1024:48000:2:0 average, 1 difference:1010
1011:2048:96000::reserved:1011
1100:4096:get 8 bit from end of header (in kHz)::reserved:1100
1101:8192:get 16 bit from end of header (in Hz)::reserved:1101
1110:16384:get 16 bit from end of header (in 10s of Hz)::reserved:1110
1111:32768:invalid::reserved:1111
_
.TE
.ps
.2C
.ps 7
.KS
.TS
tab(:);
| c s |
| c | l |.
_
Bits Per Sample
_
bits:per sample
=
000:get from STREAMINFO
001:8
010:12
011:reserved
100:16
101:20
110:24
111:reserved
_
.TE
.KE
Sample/Frame Number is a UTF-8 coded value.
If the blocking strategy is 0, it decodes to a 32-bit frame number.
If the blocking strategy is 1, it decodes to a 36-bit sample number.
.br
There is one Subframe per channel.
.KS
.TS
tab(:);
| c s |
| c | l |.
_
Subframe Type
_
bits:type
=
000000:SUBFRAME_CONSTANT
000001:SUBFRAME_VERBATIM
00001x:reserved
0001xx:reserved
001xxx:SUBFRAME_FIXED (xxx = Predictor Order)
01xxxx:reserved
1xxxxx:SUBFRAME_LPC (xxxxx = LPC Order - 1)
_
.TE
.KE
`Wasted Bits Per Sample' is typically a single bit set to 0, indicating
no wasted bits per sample.  If set to 1, a unary-encoded value
follows which indicates how many bits are wasted per sample.
.br
Padding is added as needed between the final subframe and CRC-16
in order to byte-align frames.
.1C
.bp
.SUBSUBSECTION "the CONSTANT subframe"
.PP
This is the simplest possible subframe.
It consists of a single value whose size is equal to the frame's
`Bits Per Sample'.
For instance, a 16-bit frame would have CONSTANT subframes 16 bits in length.
The value of the subframe is the value of all samples the subframe
contains.
An obvious use of this subframe is to store an entire subframe's worth
of digital silence (samples with a value of 0) very efficiently.
.SUBSUBSECTION "the VERBATIM subframe"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0
noname
  0--14 @roman Sample sub 1@
  --14 @roman Sample sub 2@
  --14 @roman Sample sub 3@
  --14-dashed ...
  --14 @roman Sample sub n@
.end dformat
This subframe's length is equal to the `Bits Per Sample' multiplied
by the frame's `Block Size'.
Since it does no compression whatsoever and simply stores
audio samples as-is, this subframe is only suitable for especially
noisy portions of a track where no predictor can be found.
.SUBSUBSECTION "the FIXED subframe"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0
noname
  0--14 Warm\[hy]Up @roman Sample sub 1@
  --14 Warm\[hy]Up @roman Sample sub 2@
  --14-dashed ...
  --25 Residual
.end dformat
The number of warm-up samples equals the `Predictor Order'
(which is encoded in the `Subframe Type').
These samples are sent out as-is; they are the subframe's
`starting point' upon which further samples build when decompressing
the stream.
Determining the value of the current sample is then a matter of
looking backwards at previously decoded samples (or warm-up samples),
applying a simple formula on their values (which depends on the
Predictor Order) and adding the residual.
.KS
.TS
tab(:);
| c | c |
| c | c |
| c | l |.
_
Predictor:Calculation
Order:\^
=
0:@"Sample" sub i = "Residual" sub i@
1:@"Sample" sub i = "Sample" sub {i~-~1}~~+~~"Residual" sub i@
2:@"Sample" sub i = (2~\[mu]~"Sample" sub {i~-~1})~~-~~"Sample" sub {i~-~2}~~+~~"Residual" sub i@
3:@"Sample" sub i = (3~\[mu]~"Sample" sub {i~-~1})~~-~~(3~\[mu]~"Sample" sub {i~-~2})~~+~~"Sample" sub {i~-~3}~~+~~"Residual" sub i@
4:@"Sample" sub i = (4~\[mu]~"Sample" sub {i~-~1})~~-~~(6~\[mu]~"Sample" sub {i~-~2})~~+~~(4~\[mu]~"Sample" sub {i~-~3})~~-~~"Sample" sub {i~-~4}~~+~~"Residual" sub i@
_
.TE
.KE
.PP
Let's run through a simple example in which the Predictor Order is 1.
Note that residual does not apply to warm-up samples.
How to extract the encoded residual will be covered in a later section.
.TS
tab(:);
| c || c | c |
| c || r | r |.
_
Index:Residual:Sample
=
0::(warm-up) @bold 10@
1:1:@10 + 1 = mark bold 11@
2:2:@11 + 2 = lineup bold 13@
3:-2:@13 - 2 = lineup bold 11@
4:1:@11 + 1 = lineup bold 12@
5:-1:@12 - 1 = lineup bold 11@
_
.TE
.bp
.SUBSUBSECTION "the LPC subframe"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0
noname
  0--18 Warm\[hy]Up @roman Sample sub 1@
  --18 Warm\[hy]Up @roman Sample sub 2@
  --18-dashed ...
  --18 Warm\[hy]Up @roman Sample sub n@
noname
  0-3-14 QLP Precision
  4-8-16 QLP Shift Needed
  9-?-14 QLP @roman Coefficient sub 1@
  --14 QLP @roman Coefficient sub 2@
  --14-dashed ...
noname
  --72 Residual
.end dformat
The number of warm-up samples equals the `LPC Order'
(which is encoded in the `Subframe Type').
The size of each QLP Coefficient is equal to
`QLP Precision' number of bits, plus 1.
The value of each Coefficient is a signed two's-complement integer.
The number of Coefficients equals the `LPC Order'.
.EQ
"Sample" sub i =
{
{sum from {j = 0} to {Order~-~1}
{"QLP Coefficient" sub j}~\[mu]~"Sample" sub {i~-~j~-~1}}
} over {2 sup "QLP Shift Needed"}
~~+~~"Residual" sub i
.EN
Don't be intimidated by the \[*S] if you're not math-inclined.
It simply means we're taking the sum of the calculated values from
0 to Order - 1, bit-shifting that sum down and added the residual
when determining the current sample.
Much like the FIXED subframe, LPC subframes also contain warm-up
samples which serve as our calculation's starting point.
.PP
In this example, the LPC Order is 5, the QLP Shift Needed is 9
and the encoded Coefficients are as follows:
.KS
.TS
tab(:);
c r.
QLP @roman Coefficient sub 0@:1241
QLP @roman Coefficient sub 1@:-944
QLP @roman Coefficient sub 2@:14
QLP @roman Coefficient sub 3@:342
QLP @roman Coefficient sub 4@:-147
.TE
.KE

.TS
tab(:);
| c || c | c |
| c || r | r |.
_
Index:Residual:Sample
=
0::(warm-up) @bold 1053@
1::(warm-up) @bold 1116@
2::(warm-up) @bold 1257@
3::(warm-up) @bold 1423@
4::(warm-up) @bold 1529@
_
5:11:@(1241~\[mu]~1529) + (-944~\[mu]~1423) + (14~\[mu]~1257) + (342~\[mu]~1116) + (-147~\[mu]~1053) = 798656@
\^:\^:@(798656~/~2 sup 9 ) = 1559 + 11 = bold 1570@
_
6:79:@(1241~\[mu]~1570) + (-944~\[mu]~1529) + (14~\[mu]~1423) + (342~\[mu]~1257) + (-147~\[mu]~1116) = 790758@
\^:\^:@(790758~/~2 sup 9 ) = 1544 + 79 = bold 1623@
_
7:24:@(1241~\[mu]~1623) + (-944~\[mu]~1570) + (14~\[mu]~1529) + (342~\[mu]~1423) + (-147~\[mu]~1257) = 855356@
\^:\^:@(855356~/~2 sup 9 ) = 1670 + 24 = bold 1694@
_
8:-81:@(1241~\[mu]~1694) + (-944~\[mu]~1623) + (14~\[mu]~1570) + (342~\[mu]~1529) + (-147~\[mu]~1423) = 905859@
\^:\^:@(905859~/~2 sup 9 ) = 1769 - 81 = bold 1688@
_
9:-72:@(1241~\[mu]~1688) + (-944~\[mu]~1694) + (14~\[mu]~1623) + (342~\[mu]~1570) + (-147~\[mu]~1529) = 830571@
\^:\^:@(830571~/~2 sup 9 ) = 1622 - 72 = bold 1550@
_
.TE
.LP
In this instance, division should always round down and \fInot\fR towards zero.
For example: @-5~/~2 sup 1 = -3@

.bp
.SUBSUBSECTION "the Residual"
.PP
Though the FLAC format allows for different forms of
residual coding, two forms of partitioned Rice are the only ones
currently supported.
The difference between the two is that when `Coding Method' is 0,
the Rice Parameter in each partition is 4 bits.
When the `Coding Method' is 1, that parameter is 5 bits.
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.2
noname
     0-1-17 Coding Method
     2-5-17 Partition Order
 P1: 6--15 @roman Partition sub 1@
     --15 @roman Partition sub 2@
     --15-dashed ...
noname
     --11-invisible Method = 0
 P2: 0-3-19 Rice Parameter
     4-8-21-dashed Escape Code
 P3: --26 Encoded Residual
noname
     --11-invisible Method = 1
     0-4-21 Rice Parameter
     5-9-22-dashed Escape Code
     --23 Encoded Residual
pic line dotted from P1.sw to P2.nw
pic line dotted from P1.se to P3.ne
.end dformat
There are @2 sup {"Partition Order"}@ number of Partitions.
The number of decoded samples in a Partition depends on the
its position in the subframe.
The first partition in the subframe contains:
.EQ
"Total Samples" mark = left (
{"Frame's Block Size" over {2 sup {"Partition Order"}}}
right )~~-~~"Predictor Order"
.EN
Subsequent partitions contain:
.EQ
"Total Samples" lineup = {"Frame's Block Size" over {2 sup {"Partition Order"}}}
.EN
Unless, of course, the Partition Order is 0.
In that case:
.EQ
"Total Samples" lineup = "Frame's Block Size"~~-~~"Predictor Order"
.EN
since there is only one partition which takes up the entire block.
.PP
If all of the bits in `Rice Parameter' are set,
the partition is unencoded binary using `Escape Code' number of bits per
sample.
.bp
.SUBSUBSUBSECTION "Rice Encoding"
.PP
The residual uses Rice coding to compress lots of mostly small values
in a very small amount of space.
To decode it, one first needs the Rice parameter.
Take a unary-encoded value\(dg from the bit stream, which are our most
significant bits (MSB).
.FS
\(dg In this instance, unary-encoding is a simple matter of
counting the number of 0 bits before the next 1 bit.
The resulting sum is the value.
.FE
Then take `parameter' number of additional bits, which are our least
significant bits (LSB).
Combine the two sets into our new value,
making the MSB set as the high bits and the LSB set as the low bits.
Bit 0 of this new value is the sign bit.
If it is 0, the actual value is equal to the rest of the bits.
If it is 1, the actual value is equal to the rest of the bits,
multiplied by -1 and minus 1.
.PP
This is less complicated than it sounds, so let's run through an example
in which the Rice parameter is 1:
.PSPIC -L "rice1.eps" 4.5i
.sp 24pt
Now, let's run through another example in which the Rice parameter is 4:
.PSPIC -L "rice2.eps" 6i
.bp
.SUBSUBSECTION "Channels"
.PP
Since most audio has more than one channel, it is important to
understand how FLAC handles putting it back together.
When channels are stored independently, one simply interleaves
them together in the proper order.
Let's take an example of 2 channel, 16-bit audio stored this way:
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
 F1: --10 Subframe @roman 1 sub L@
     --10 Subframe @roman 2 sub L@
 F2: --10 Subframe @roman 3 sub L@
     --12-invis
 F3: --10 Subframe @roman 1 sub R@
     --10 Subframe @roman 2 sub R@
 F4: --10 Subframe @roman 3 sub R@
noname
     --6-invis
 S1: --10 Subframe @roman 1 sub L@
     --10 Subframe @roman 1 sub R@
 S2: --10 Subframe @roman 2 sub L@
 S3: --10 Subframe @roman 2 sub R@
     --10 Subframe @roman 3 sub L@
 S4: --10 Subframe @roman 3 sub R@
pic line dotted from F1.sw to S1.nw
pic line dotted from F4.se to S4.ne
pic line dotted from F2.se to S2.ne
pic line dotted from F3.sw to S3.nw
.end dformat
This is the simplest case.
However, in the case of difference channels, one subframe will
contain actual channel data and the other channel will contain
signed difference data which is applied to the first channel
in order to reconstruct both channels.
It's very important to remember that the difference channel
has 1 additional bit per sample which will be consumed during
reconstruction.
Why 1 additional bit?
Let's take an example where the left sample's value is -30000
and the right sample's value is +30000.
Storing this pair as left + difference means the left
sample remains -30000 and the difference is -60000
.br
(-30000 \- -60000 = +30000).
-60000 won't fit into a 16-bit signed integer.
Adding that 1 additional bit doubles our range of values
and that's just enough to cover any possible difference between
two samples.
.ps 9
.TS
tab(:);
| c s s s s |
| c || c | c || c | c |
| c || l | l || l | l |.
_
Channel Calculation
_
Assignment:Channel 0:Channel 1:Left Channel:Right Channel
=
1000:left:difference:left:left \- difference
1001:difference:right:right + difference:right
1010:mid:side:(((mid << 1) | (side & 1)) + side) >> 1:(((mid << 1) | (side & 1)) - side) >> 1
_
.TE
.ps 10
The mid channel case is another unusual exception.
We're prepending the mid channel with bit 0 from the
side channel, performing the addition/subtraction and then
discarding that bit before assigning the results to the left and
right channels.
.SUBSUBSECTION "Wasted bits per sample"
.PP
Though rare in practice, FLAC subframes support `wasted bits per sample'.
Put simply, these wasted bits are removed during subframe calculation
and restored to the subframe's least significant bits as zero value bits
when it is returned.
For instance, a subframe with 1 wasted bit per sample in a 16-bit FLAC
stream is treated as having only 15 bits per sample when reading
warm-up samples and then all through the rest of the subframe
calculation.
That wasted zero bit is then prepended to each sample prior to returning
the subframe.
.bp
.SUBSECTION "FLAC encoding"
.PP
For the purposes of discussing FLAC encoding,
we'll assume one has a stream of input PCM values along with the
stream's sample rate, number of channels and bits per sample.
Creating a valid FLAC file is then a matter of writing the proper
file header, metadata blocks and FLAC frames.
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.15
noname
       0-31-24 Header (`fLaC' 0x664C6143)
  FD1: 32--8 @roman Metadata sub 1@
       --8 @roman Metadata sub 2@
       --8-dashed ...
  FD2: --8 @roman Frame sub 1@
       --8 @roman Frame sub 2@
       --8-dashed ...
noname
  FD3: 0-31-16 Metadata Header
  FD4: 32--16-dashed Block Data
       --4-invis
  FD5: 0-48/128-14 Frame Header
  FD7: --8 @roman Subframe sub 1@
       --8 @roman Subframe sub 2@
       --4-dashed ...
  FD6: --6 CRC-16
noname
        --38-invis
  FD8:  0-7-16 Subframe Header
  FD9:  8--21 Subframe data
pic line dotted from FD1.sw to FD3.nw
pic line dotted from FD1.se to FD4.ne
pic line dotted from FD2.sw to FD5.nw
pic line dotted from FD2.se to FD6.ne
pic line dotted from FD7.sw to FD8.nw
pic line dotted from FD7.se to FD9.ne
.end dformat
.SUBSUBSECTION "Metadata header"
.PP
.TS
tab(:);
| c | c |
| r | l |.
_
bits:value
=
1:0 if addition metadata blocks follow, 1 if not
7:0 for STREAMINFO, 1 for PADDING, 4 for VORBIS_COMMENT, etc.
24:the length of the block data in bytes, not including the header
_
.TE
.SUBSUBSECTION "the STREAMINFO metadata block"
.PP
.TS
tab(:);
| c | c |
| r | l |.
_
bits:value
=
16:the minimum FLAC frame size, in PCM frames
16:the maximum FLAC frame size, in PCM frames
24:the minimum FLAC frame size, in bytes
24:the maximum FLAC frame size, in bytes
20:the stream's sample rate, in Hz
3:the stream's channel count, minus one
5:the stream's bit-per-sample, minus one
36:the stream's total number of PCM frames
128:an MD5 sum of the PCM stream's bytes
_
.TE
.PP
When encoding a FLAC file, many of these fields cannot be known in advance.
Instead, one must keep track of those values during encoding and then
rewrite the STREAMINFO block when finished.
.SUBSUBSECTION "the VORBIS_COMMENT metadata block"
.PP
.TS
tab(:);
| c | c |
| r | l |.
_
bits:value
=
32\[dd]:vendor string length, in bytes
string length \[mu] 8:vendor string data, as UTF-8 encoded text
32\[dd]:total number of comment strings
32\[dd]:comment @roman string sub 1@ length, in bytes
string length \[mu] 8:comment @roman string sub 1@, as UTF-8 encoded text
 ...:...
_
.TE
.PP
Fields marked with \[dd] are little-endian integers.
.SUBSUBSECTION "the PADDING metadata block"
.PP
This is simply an empty block full of \fC0x00\fR bytes.
.bp
.SUBSUBSECTION "Frame header"
.PP
.TS
tab(:);
| c | c |
| r | l |.
_
bits:value
=
14:\fC0x3FFE\fR sync code
1:\fC0\fR reserved
1:\fC0\fR if the header encodes the frame number, \fC1\fR if it encodes the sample number
4:this frame's block size, as encoded PCM frames\(dg
4:this frame's encoded sample rate\(dg
4:this frame's encoded channel assignment\(dg
3:this frame's encoded bits per sample\(dg
1:\fC0\fR padding
8-56:the frame number, or sample number, UTF-8 encoded and starting from 0
0/8/16:the number of PCM frames (minus one) in this FLAC frame, if block size is \fC0x6\fR (8 bits) or \fC0x7\fR (16 bits)
0/8/16:the sample rate of this FLAC frame, if sample rate is \fC0xC\fR (8 bits), \fC0xD\fR (16 bits) or \fC0xE\fR (16 bits)
8:the CRC-8 of all data from the beginning of the frame header
_
.TE
.FS
\(dg See table on page \n(ZF
.FE
.PP
The FLAC frame's block size in PCM frames
(called ``channel independent samples'' in FLAC's documentation)
is typically encoded in the 4 bit `block size' field.
But for odd-sized frames - which often occur at the end of the stream -
that value is stored as an 8 or 16 bit integer following the UTF-8 encoded
frame number.
.PP
In addition, odd sample rate values are stored as 8 bit (in kHz),
16 bit (in Hz) or 16 bit (in 10s of Hz) prior to the CRC-8,
should a predefined value not be available.
.PP
Up until this point, nearly all of these fields can be filled from
the PCM stream data.
Unless you're writing a variable block size encoder (which no one has),
one should encode the frame number starting from 0 in the frame header
and choose a predefined block size for as many FLAC frames as possible.
.SUBSUBSECTION "Channel assignment"
.PP
If the input stream has a number of channels other than 2,
one has no choice but to store them independently.
If the number of channels equals 2, one can try all four possible
assignments (left-difference, difference-right, mid-side and
independent) and use the one which takes the least amount of space.
.SUBSUBSECTION "Subframe header"
.PP
.TS
tab(:);
| c | c |
| r | l |.
_
bits:value
=
1:\fC0\fR padding
6:subframe type, with optional predictor order
1:\fC0\fR if no wasted bits per sample, \fC1\fR if a unary-encoded number follows
0+:the number of wasted bits per sample (minus one) encoded as unary
_
.TE
.TS
tab(:);
| c s |
| c | l |.
_
Subframe Type
_
bits:type
=
000000:SUBFRAME_CONSTANT
000001:SUBFRAME_VERBATIM
00001x:reserved
0001xx:reserved
001xxx:SUBFRAME_FIXED (xxx = Predictor Order)
01xxxx:reserved
1xxxxx:SUBFRAME_LPC (xxxxx = Predictor Order - 1)
_
.TE
.bp
.SUBSUBSECTION "the CONSTANT subframe"
.PP
If all the samples in a subframe are identical, one can encode them
using a CONSTANT subframe, which is essentially a single sample value
that gets duplicated `block size' number of times when decoded.
.SUBSUBSECTION "the VERBATIM subframe"
.PP
This subframe simply stores all the samples as-is,
with no compression whatsoever.
It is a `fallback' encoding method for when no other subframe makes one's
data any smaller.
.SUBSUBSECTION "the FIXED subframe"
.PP
This subframe consists of `predictor order' number of unencoded
warm-up samples followed by a residual.
Determining which predictor order to use on a given set of input samples
depends on their minimum delta sum.
This process is best explained by example:
.TS
tab(:);
| c | c | c | c | c | c | c |
| c | r | r | r | r | r | r |.
_
index:sample:@{\[*D] sup 0}@:@{\[*D] sup 1}@:@{\[*D] sup 2}@:@{\[*D] sup 3}@:@{\[*D] sup 4}@
=
0:-40:
1:-41:\fI-41\fR
2:-40:\fI-40\fR:\fI-1\fR
3:-39:\fI-39\fR:\fI-1\fR:\fI0\fR
4:-38:-38:\fI-1\fR:\fI0\fR:\fI0\fR
5:-38:-38:0:-1:1:-1
6:-35:-35:-3:3:-4:5
7:-35:-35:0:-3:6:-10
8:-39:-39:4:-4:1:5
9:-40:-40:1:3:-7:8
10:-40:-40:0:1:2:-9
11:-39:-39:-1:1:0:2
12:-38:-38:-1:0:1:-1
13:-37:-37:-1:0:0:1
14:-33:-33:-4:3:-3:3
15:-36:-36:3:-7:10:-13
16:-35:-35:-1:4:-11:21
17:-31:-31:-4:3:1:-12
18:-32:-32:1:-5:8:-7
19:-33:-33:1:0:-5:13
_
@|~{roman "sum"}~|@::579:26:38:60:111
_
.TE
.LP
Note that the numbers in italics play a part in the delta
calculation to their right, but do \fBnot\fR figure into the
delta's absolute value sum, below.
.PP
In this example, @\[*D] sup 1@'s value of 26 is the smallest.
Therefore, when compressing this set of samples in a FIXED subframe,
it's best to use a predictor order of 1.
.PP
The predictor order indicates how many warm-up samples to take from
the PCM stream.
Determining the residual values can then be done automatically
based on the current @"Sample" sub i@ and previously encoded samples, or
warm-up samples.
.TS
tab(:);
| c | c |
| c | c |
| c | l |.
_
Predictor:Calculation
Order:\^
=
0:@"Residual" sub i = "Sample" sub i@
1:@"Residual" sub i = "Sample" sub i~~-~~"Sample" sub {i~-~1}@
2:@"Residual" sub i = "Sample" sub i~~-~~((2~\[mu]~"Sample" sub {i~-~1})~~-~~"Sample" sub {i~-~2})@
3:@"Residual" sub i = "Sample" sub i~~-~~((3~\[mu]~"Sample" sub {i~-~1})~~-~~(3~\[mu]~"Sample" sub {i~-~2})~~+~~"Sample" sub {i~-~3})@
4:@"Residual" sub i = "Sample" sub i~~-~~((4~\[mu]~"Sample" sub {i~-~1})~~-~~(6~\[mu]~"Sample" sub {i~-~2})~~+~~(4~\[mu]~"Sample" sub {i~-~3})~~-~~"Sample" sub {i~-~4})@
_
.TE
.\"In this example, the residual values are: -1 1 1 1 0 3 0 -4 -1 0 1 1 1 4 -3 1 4 -1 -1
.bp
.SUBSUBSECTION "the LPC subframe"
.PP
Unlike the FIXED subframe which required only input samples and a
predictor order, LPC subframes also require a list of QLP coefficients,
a QLP precision value of those coefficients, and a QLP shift needed
value.
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0
noname
  0--18 Warm\[hy]Up @roman Sample sub 1@
  --18 Warm\[hy]Up @roman Sample sub 2@
  --18-dashed ...
  --18 Warm\[hy]Up @roman Sample sub n@
noname
  0-3-14 QLP Precision
  4-8-16 QLP Shift Needed
  9-?-14 QLP @roman Coefficient sub 1@
  --14 QLP @roman Coefficient sub 2@
  --14-dashed ...
noname
  --72 Residual
.end dformat
.LP
Determining these values for a given input PCM signal is a somewhat
complicated process which depends on whether one is performing an
exhaustive LP coefficient order search or not:
.LP
.mk
Non-exhaustive search
.br
.PSPIC -L "lpc_process.eps" 3i
.rt
.in +3in
Exhaustive search
.br
.PSPIC -R "lpc_process2.eps" 3i
\" .LP
\" .in +3.25i
\" `Input PCM' is the subframe input signal.
\" .br
\" `Max LPC Order' is a user-defined value from 1 to 33, typically in the
\" 6-12 range.
\" .in -3.25i
.bp
.SUBSUBSUBSECTION "Windowing"
.PP
The first step in LPC subframe encoding is `windowing' the input signal.
Put simply, this is a process of multiplying each input sample by
an equivalent value from the window, which are floats from 0.0 to 1.0.
In this case, the default is a Tukey window with a ratio of 0.5.
A Tukey window is a combination of the Hann and Rectangular windows.
The ratio of 0.5 means there's 0.5 samples in the Hann window per
sample in the Rectangular window.
.LP
.mk
.PSPIC -R "hann.eps" 2.5i
.PSPIC -R "rectangular.eps" 2.5i
.PSPIC -R "tukey.eps" 2.5i
.rt
.LP
.ll 3.25in
The Hann window is defined by the function:
.br
.sp
@{roman hann} (n) = \[12] ~ left ( 1~-~cos left ( {2 pi n} over {"sample count" - 1} right ) right )@
.br
.sp
.LP
.ll 3.25in
The Rectangular window is defined by the function:
.br
.sp
@{roman rectangle} (n) = 1.0@
.br
.sp
.LP
.ll 3.25in
The Tukey window is defined by taking a Hann window, splitting it at
the halfway point, and inserting a Rectangular window between the
two.
.LP
Let's run through a short example with 20 samples:
.TS
tab(:);
| c | c c c c c |
| c | c c c c c |
| r | r c r c r |.
_
index:input::Tukey::windowed
\^:sample::window::signal
=
0:-40:@\[mu]@:0.0000:@=@:0.00
1:-41:@\[mu]@:0.1464:@=@:-6.00
2:-40:@\[mu]@:0.5000:@=@:-20.00
3:-39:@\[mu]@:0.8536:@=@:-33.29
4:-38:@\[mu]@:1.0000:@=@:-38.00
5:-38:@\[mu]@:1.0000:@=@:-38.00
6:-35:@\[mu]@:1.0000:@=@:-35.00
7:-35:@\[mu]@:1.0000:@=@:-35.00
8:-39:@\[mu]@:1.0000:@=@:-39.00
9:-40:@\[mu]@:1.0000:@=@:-40.00
10:-40:@\[mu]@:1.0000:@=@:-40.00
11:-39:@\[mu]@:1.0000:@=@:-39.00
12:-38:@\[mu]@:1.0000:@=@:-38.00
13:-37:@\[mu]@:1.0000:@=@:-37.00
14:-33:@\[mu]@:1.0000:@=@:-33.00
15:-36:@\[mu]@:1.0000:@=@:-36.00
16:-35:@\[mu]@:0.8536:@=@:-29.88
17:-31:@\[mu]@:0.5000:@=@:-15.50
18:-32:@\[mu]@:0.1464:@=@:-4.68
19:-33:@\[mu]@:0.0000:@=@:0.00
_
.TE
.bp
.SUBSUBSUBSECTION "Computing autocorrelation"
.PP
Once our input samples have been converted to a windowed signal,
we then compute the autocorrelation values from that signal.
Each autocorrelation value is determined by multiplying the signal's
samples by the samples of a lagged version of that same signal,
and then taking the sum.
The lagged signal is simply the original signal with `lag' number of
samples removed from the beginning.
.PSPIC -L "lag.eps" 6i
.PP
The lagged sums from 0 to the maximum LPC order are our autocorrelation
values.  In this example, they are 14979.0, 13651.0 and 12405.0.
.bp
.SUBSUBSUBSECTION "LP coefficient calculation"
.PP
Calculating the LP coefficients uses the Levinson-Durbin recursive method.\(dg
.FS
\(dg This algorithm is taken from http://www.engineer.tamuk.edu/SPark/chap7.pdf
.FE
Our inputs are @M@, the maximum LPC order minus 1, and @r@ autocorrelation
values, from @r(0)@ to @r(M - 1)@.
Our outputs are @a@, a list of LP coefficient lists from
@a sub 11@ to @a sub {(M - 1)(M - 1)}@, and @E@, a list
of error values from @E sub 0@ to @E sub {(M - 1)}@.
@q sub m@ and @\[*k] sub m@ are temporary values.
.LP
Initial values:
.TS
tab(:);
l.
@E sub 0 mark = r(0)@
@a sub 11 lineup = \[*k] sub 1 = {r(1) over {E sub 0}}@
@E sub 1 lineup = E sub 0 {(1 - {{\[*k] sub 1} sup 2})}@
.TE
.LP
With @m \[>=] 2@, the following recursive algorithm is performed:
.TS
tab(:);
r l.
step 1.:@q sub m mark = r(m) - sum from {i = 1} to {m - 1} a sub {i (m - 1)} r(m - i)@
step 2.:@\[*k] sub m lineup = {q sub m} over {E sub {(m - 1)}}@
step 3.:@a sub mm lineup = \[*k] sub m@
step 4.:@a sub im lineup = a sub {i(m - 1)} - \[*k] sub m a sub {(m - i)(m - 1)}@ for @i = 1,i = 2,...,i = m - 1@
step 5.:@E sub m lineup = E sub {m - 1}( 1 - {\[*k] sub m} sup 2 )@
step 6.:If @m < M@ then increment @m@ to @m + 1@ and return to step 1.  If @m = M@ then stop.
.TE
.LP
Let's run through an example in which @M = 4@, @r(0) = 11018@, @r(1) = 9690@,
@r(2) = 8443@ and @r(3) = 7280@:
.br
.ps 8
@E sub 0 mark = r(0) = 11018@
.br
@a sub 11 lineup = \[*k] sub 1 = {r(1) over E sub 0} = {9690 over 11018} = 0.8795@
.br
@E sub 1 lineup = E sub 0 {(1 - {{\[*k] sub 1} sup 2})} = 11018(1 - 0.8795 sup 2 ) = 2495@
.br
@q sub 2 lineup = r(2) - sum from {i = 1} to 1 a sub i1 {r(2 - i)} = 8443 - (0.8795)(9690) = -79.35@
.br
@\[*k] sub 2 lineup = {{q sub 2} over {E sub 1}} = {-79.35 over 2495} = -0.0318@
.br
@a sub 22 lineup = \[*k] sub 2 = -0.0318@
.br
@a sub 12 lineup = a sub 11 - \[*k] sub 2 a sub 11 = 0.8795 - (-0.0318)(0.8795) = 0.9074@
.br
@E sub 2 lineup = E sub 1 (1 - {\[*k] sub 2} sup 2 ) = 2495(1 - {-0.0318 sup 2}) = 2492@
.br
@q sub 3 lineup = r(3) - sum from {i = 1} to 2 a sub i2 {r(3 - i)} = 7280 - ((0.9074)(8443) + (-0.0318)(9690)) = -73.04@
.br
@\[*k] sub 3 lineup = {q sub 3} over {E sub 2} = {-73.04 over 2492} = -0.0293@
.br
@a sub 33 lineup = \[*k] sub 3 = -0.0293@
.br
@a sub 13 lineup = a sub 12 - \[*k] sub 3 a sub 22 = 0.9074 - (-0.0293)(-0.0318) = 0.9065@
.br
@a sub 23 lineup = a sub 22 - \[*k] sub 3 a sub 12 = -0.0318 - (-0.0293)(0.9074) = -0.0052@
.br
@E sub 3 lineup = E sub 2 (1 - {\[*k] sub 3} sup 2 ) = 2492(1 - {-0.0293 sup 2}) = 2490@
.ps 10
.LP
@roman "Our final values are:"~~a sub 11 mark = 0.8795@
.br
@a sub 12 lineup = 0.9074~~~a sub 22 = -0.0318@
.br
@a sub 13 lineup = 0.9065~~~a sub 23 = -0.0052~~~a sub 33 = -0.0293@
.br
@E sub 1 lineup = 2495~~~E sub 2 = 2492~~~E sub 3 = 2490@
.LP
These values have been rounded to the nearest significant digit
and will not be an exact match to those generated by a computer.
.bp
.SUBSUBSUBSECTION "Best order estimation"
.PP
At this point, we have an array of prospective LP coefficient lists,
a list of error values and must decide which LPC order to use.
There are two ways to accomplish this:  we can either estimate
the total bits from the error values or perform an exhaustive search.
Making the estimation requires the total number of samples
in the subframe, the number of overhead bits per order (by default,
this is the number of bits per sample in the subframe, plus 5),
and an error scale constant in addition to the LPC error values:
.EQ
"Error Scale" mark = {{ln (2) sup 2}} over {2~\[mu]~"Total Samples"}
.EN
.LP
Once the error scale has been calculated, one can generate a
`Bits per Residual' estimation function which, given an LPC Error value,
returns what its name implies:
.EQ
{roman "Bits per Residual"} ("LPC Error") lineup = {ln ("Error Scale"~\[mu]~"LPC Error")} over {2~\[mu]~ln (2)}
.EN
With this function, we can estimate how many bits the entire LPC subframe
will take for each LPC Error value and its associated Order:
.ps 8
.EQ
{roman "Total Bits"} ("LPC Error","Order") = left ( {{roman "Bits per Residual"} ("LPC Error")~\[mu]~("Total Samples" - "Order")} right ) + left ( "Order"~\[mu]~"Overhead Bits per Order" right )
.EN
.ps
.LP
Picking the best LPC Order is then done exhaustively by calculating the
total estimated bits for each one and using the order which uses
the fewest.
.SUBSUBSUBSECTION "Best order exhaustive search"
.PP
In a curious bit of recursion, finding the best order for an LPC subframe
via an exhaustive search requires taking each list of LP Coefficients
calculated previously, quantizing them into a list of QLP Coefficients
and a QLP Shift Needed value,\(dg
.FS
\(dg Quantizing coefficients will be covered in the next section.
.FE
determining the total
amount of bits each hypothetical LPC subframe uses and using
the LPC order which uses the fewest.
.PP
Remember that building an LPC subframe requires the following values:
LPC Order, QLP Precision, QLP Shift Needed and QLP Coefficients along
with the subframe's samples and bits-per-sample.
For each possible LPC Order, the QLP Shift Needed and the QLP Coefficient
list values can be calculated by quantizing the LP Coefficients.
QLP Precision is the size of each QLP Coefficient list value in the
subframe header.
Simply choose the field with the largest number of bits in the
QLP Coefficient list for the QLP Precision value.
.PP
Finally, instead of writing these hypothetical LPC subframes directly to disk,
one only has to capture how many bits they
.I would
use.
The hypothetical LPC subframe that uses the fewest number of bits
is the one we should actually write to disk.
.bp
.SUBSUBSUBSECTION "Quantizing coefficients"
.PP
Quantizing coefficients is a process of taking a list of LP Coefficients
along with a QLP Coefficients Precision value and
returning a list of QLP Coefficients and a QLP Shift Needed value.
The first step is determining the upper and lower limits of the
QLP Coefficients:
.EQ
"QLP coefficient maximum" mark = {2 sup "precision"} - 1
.EN
.EQ
"QLP coefficient mininum" lineup = - {2 sup "precision"}
.EN
The next step is determining the maximum shift limit and minimum
shift limit constants, which are what their names imply:
.EQ
"max shift limit" mark = {2 sup {"QLP shift length" - 1}} - 1 = {2 sup {5 - 1}} - 1 = {2 sup 4} - 1 = 16 - 1 = 15
.EN
.EQ
"min shift limit" lineup = -({"max shift limit" - 1}) = -14
.EN
Now we determine the initial QLP Shift Needed value:
.EQ
"shift" = "precision" - {left ceiling {log ({roman max} (~|~"LP Coefficients"~|~)) } over {log (2) } right ceiling}
.EN
where `shift' is adjusted if necessary such that:
@"min shift limit" <= "shift" <= "max shift limit"@
.LP
Finally, we determine the QLP Coefficient values themselves via a small
recursive routine:
.EQ
X(i) mark = E(i - 1) + ({"LP Coefficient" sub i}~\[mu]~{2 sup "shift"})
.EN
.EQ
{"QLP Coefficient" sub i} lineup = {roman "round"} (X(i))
.EN
.EQ
E(i) lineup = X(i) - {"QLP Coefficient" sub i}
.EN
where @E(-1) = 0@ and each QLP Coefficient is adjusted
prior to calculating the next @E(i)@ value such that:
.br
@"QLP coefficient minimum" <= {"QLP Coefficient" sub i} <= "QLP coefficient maximum"@
.sp
.LP
The LPC Order, QLP Precision, QLP Shift Needed, and QLP Coefficients
make up the LPC subframe.
.bp
.SUBSUBSUBSECTION "Calculating Residual"
.PP
A number of warm-up samples equal to LPC Order are taken from the input PCM
and the subframe's residuals are calculated according to the following formula:
.EQ
"Residual" sub i
=
"Sample" sub i~~-~~
{
{sum from {j = 0} to {Order~-~1}
{"QLP Coefficient" sub j}~\[mu]~"Sample" sub {i~-~j~-~1}}
} over {2 sup "QLP Shift Needed"}
.EN
For example, given the samples
1053, 1116, 1257, 1423, 1529, 1570, 1623, 1694, 1688 and 1550,
.br
the coefficients:
.TS
tab(:);
c r.
QLP @roman Coefficient sub 0@:1241
QLP @roman Coefficient sub 1@:-944
QLP @roman Coefficient sub 2@:14
QLP @roman Coefficient sub 3@:342
QLP @roman Coefficient sub 4@:-147
.TE
and a QLP Shift Needed value of 9, our residuals are as follows:
.ps 9
.TS
tab(:);
| c || c | c |
| c || r | r |.
_
Index:Sample:Residual
=
0:(warm-up) 1053:
1:(warm-up) 1116:
2:(warm-up) 1257:
3:(warm-up) 1423:
4:(warm-up) 1529:
5:1570:@1570~-~{{(1241~\[mu]~1529) + (-944~\[mu]~1423) + (14~\[mu]~1257) + (342~\[mu]~1116) + (-147~\[mu]~1053)} over {2 sup 9}}~=~1570~-~{798656 over 512}~ mark =~bold 11~~@
\^::
6:1623:@1623~-~{{(1241~\[mu]~1570) + (-944~\[mu]~1529) + (14~\[mu]~1423) + (342~\[mu]~1257) + (-147~\[mu]~1116)} over {2 sup 9}}~=~1623-{790758 over 512}~ lineup =~bold 79@
\^::
7:1694:@1694~-~{{(1241~\[mu]~1623) + (-944~\[mu]~1570) + (14~\[mu]~1529) + (342~\[mu]~1423) + (-147~\[mu]~1257)} over {2 sup 9}}~=~1694-{855356 over 512}~ lineup =~bold 24@
\^::
8:1688:@1688~-~{{(1241~\[mu]~1694) + (-944~\[mu]~1623) + (14~\[mu]~1570) + (342~\[mu]~1529) + (-147~\[mu]~1423)} over {2 sup 9}}~=~1688-{905859 over 512}~ lineup =~bold -81@
\^::
9:1550:@1550~-~{{(1241~\[mu]~1688) + (-944~\[mu]~1694) + (14~\[mu]~1623) + (342~\[mu]~1570) + (-147~\[mu]~1529)} over {2 sup 9}}~=~1550-{830571 over 512}~ lineup =~bold -72@
_
.TE
.ps
.bp
.SUBSUBSECTION "the Residual"
.PP
Given a stream of residual values, one must place them in one or more
partitions, each with its own Rice parameter, and prepended with a
small header:
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.2
noname
     0-1-17 Coding Method
     2-5-17 Partition Order
 P1: 6--15 @roman Partition sub 1@
     --15 @roman Partition sub 2@
     --15-dashed ...
noname
     --11-invisible Method = 0
 P2: 0-3-19 Rice Parameter
     4-8-21-dashed Escape Code
 P3: --26 Encoded Residual
noname
     --11-invisible Method = 1
     0-4-21 Rice Parameter
     5-9-22-dashed Escape Code
     --23 Encoded Residual
pic line dotted from P1.sw to P2.nw
pic line dotted from P1.se to P3.ne
.end dformat

The residual's coding method is typically 0, unless one is encoding
audio with more than 16 bits-per-sample and one of the partitions
requests a Rice parameter higher than @2 sup 4@.
The residual's partition order is chosen exhaustively, which means
trying all of them within a certain range (e.g. 0 to 5) such that
the residuals can be divided evenly between them and then the partition
order which uses the smallest estimated amount of space is chosen.
.PP
Choosing the best Rice parameter is a matter of selecting the smallest
value of `x' such that:
.EQ
"sample count"~\[mu]~{2 sup x}~~>~~{sum from {i = 0} to {"residual count"~-~1}
|{"residual" sub i}|}
.EN
.LP
Again, this is easier to understand with a block of example residuals,
19 in total:
.TS
tab(:);
| c | c | c |
| c | r | r |.
_
index:@residual sub i@:@|~{residual sub i}~|@
=
0:-1:1
1:1:1
2:1:1
3:1:1
4:0:0
5:3:3
6:0:0
7:-4:4
8:-1:1
9:0:0
10:1:1
11:1:1
12:1:1
13:4:4
14:-3:3
15:1:1
16:4:4
17:-1:1
18:-1:1
_
@|~{roman "sum"}~|@::29
_
.TE
@19~\[mu]~{2 sup 0}@ is not larger than 29.
.br
@19~\[mu]~{2 sup 1}@ is larger than 29, so the best Rice parameter
for this block of residuals is 1.
.PP
Remember that the Rice parameter's maximum value is limited to
@2 sup 4@ using coding method 0, or @2 sup 5@ using coding method 1.
.SUBSECTION "the Checksums"
.PP
Calculating the frame header's CRC-8 and frame footer's CRC-16 is necessary
both for FLAC encoders and decoders, but the process is the same for each.
.SUBSUBSECTION "CRC-8"
.PP
CRC-8 is used to checksum FLAC frame headers.
Given a byte of input and the previous CRC-8 checksum,
or 0 as an initial value,
the current checksum can be calculated as follows:
.EQ
{checksum sub i}~=~{roman "CRC8"} ( byte~{roman "xor"}~{checksum sub {i - 1}} )
.EN
.ps 7
.ft C
.TS
tab(:);
| c s s s s s s s s s s s s s s s s |
| r || c | c | c | c | c | c | c | c | c | c | c | c | c | c | c | c |
| r || r | r | r | r | r | r | r | r | r | r | r | r | r | r | r | r |.
_
.ps 8
.ft R
CRC8
.ft C
.ps 7
_
:0x?0:0x?1:0x?2:0x?3:0x?4:0x?5:0x?6:0x?7:0x?8:0x?9:0x?A:0x?B:0x?C:0x?D:0x?E:0x?F
=
0x0?:0x00:0x07:0x0E:0x09:0x1C:0x1B:0x12:0x15:0x38:0x3F:0x36:0x31:0x24:0x23:0x2A:0x2D
0x1?:0x70:0x77:0x7E:0x79:0x6C:0x6B:0x62:0x65:0x48:0x4F:0x46:0x41:0x54:0x53:0x5A:0x5D
0x2?:0xE0:0xE7:0xEE:0xE9:0xFC:0xFB:0xF2:0xF5:0xD8:0xDF:0xD6:0xD1:0xC4:0xC3:0xCA:0xCD
0x3?:0x90:0x97:0x9E:0x99:0x8C:0x8B:0x82:0x85:0xA8:0xAF:0xA6:0xA1:0xB4:0xB3:0xBA:0xBD
0x4?:0xC7:0xC0:0xC9:0xCE:0xDB:0xDC:0xD5:0xD2:0xFF:0xF8:0xF1:0xF6:0xE3:0xE4:0xED:0xEA
0x5?:0xB7:0xB0:0xB9:0xBE:0xAB:0xAC:0xA5:0xA2:0x8F:0x88:0x81:0x86:0x93:0x94:0x9D:0x9A
0x6?:0x27:0x20:0x29:0x2E:0x3B:0x3C:0x35:0x32:0x1F:0x18:0x11:0x16:0x03:0x04:0x0D:0x0A
0x7?:0x57:0x50:0x59:0x5E:0x4B:0x4C:0x45:0x42:0x6F:0x68:0x61:0x66:0x73:0x74:0x7D:0x7A
0x8?:0x89:0x8E:0x87:0x80:0x95:0x92:0x9B:0x9C:0xB1:0xB6:0xBF:0xB8:0xAD:0xAA:0xA3:0xA4
0x9?:0xF9:0xFE:0xF7:0xF0:0xE5:0xE2:0xEB:0xEC:0xC1:0xC6:0xCF:0xC8:0xDD:0xDA:0xD3:0xD4
0xA?:0x69:0x6E:0x67:0x60:0x75:0x72:0x7B:0x7C:0x51:0x56:0x5F:0x58:0x4D:0x4A:0x43:0x44
0xB?:0x19:0x1E:0x17:0x10:0x05:0x02:0x0B:0x0C:0x21:0x26:0x2F:0x28:0x3D:0x3A:0x33:0x34
0xC?:0x4E:0x49:0x40:0x47:0x52:0x55:0x5C:0x5B:0x76:0x71:0x78:0x7F:0x6A:0x6D:0x64:0x63
0xD?:0x3E:0x39:0x30:0x37:0x22:0x25:0x2C:0x2B:0x06:0x01:0x08:0x0F:0x1A:0x1D:0x14:0x13
0xE?:0xAE:0xA9:0xA0:0xA7:0xB2:0xB5:0xBC:0xBB:0x96:0x91:0x98:0x9F:0x8A:0x8D:0x84:0x83
0xF?:0xDE:0xD9:0xD0:0xD7:0xC2:0xC5:0xCC:0xCB:0xE6:0xE1:0xE8:0xEF:0xFA:0xFD:0xF4:0xF3
_
.TE
.LP
For example, given the header bytes: 0xFF, 0xF8, 0xCC, 0x1C, 0x00 and 0xC0,
the header's CRC-8 can be calculated as follows:
.EQ
{checksum sub 0}~mark =~{roman "CRC8"} ( {roman "0xFF"}~{roman "xor"}~0 )~=~{roman "CRC8"} ( {roman "0xFF"} )~=~{roman "0xF3"}
.EN
.EQ
{checksum sub 1}~lineup =~{roman "CRC8"} ( {roman "0xF8"}~{roman "xor"}~{roman "0xF3"} )~=~{roman "CRC8"} ( {roman "0x0B"} )~=~{roman "0x31"}
.EN
.EQ
{checksum sub 2}~lineup =~{roman "CRC8"} ( {roman "0xCC"}~{roman "xor"}~{roman "0x31"} )~=~{roman "CRC8"} ( {roman "0xFD"} )~=~{roman "0xFD"}
.EN
.EQ
{checksum sub 3}~lineup =~{roman "CRC8"} ( {roman "0x1C"}~{roman "xor"}~{roman "0xFD"} )~=~{roman "CRC8"} ( {roman "0xE1"} )~=~{roman "0xA9"}
.EN
.EQ
{checksum sub 4}~lineup =~{roman "CRC8"} ( {roman "0x00"}~{roman "xor"}~{roman "0xA9"} )~=~{roman "CRC8"} ( {roman "0xA9"} )~=~{roman "0x56"}
.EN
.EQ
{checksum sub 5}~lineup =~{roman "CRC8"} ( {roman "0xC0"}~{roman "xor"}~{roman "0x56"} )~=~{roman "CRC8"} ( {roman "0x96"} )~=~{roman "0xEB"}
.EN
.LP
Thus, the next byte after the header should be 0xEB.
Furthermore, when the checksum byte itself is run through the
checksumming procedure, as follows:
.EQ
{checksum sub 6}~lineup =~{roman "CRC8"} ( {roman "0xEB"}~{roman "xor"}~{roman "0xEB"} )~=~{roman "CRC8"} ( {roman "0x00"} )~=~{roman "0x00"}
.EN
the result will always be 0.
This is a handy way to verify a frame header's checksum since the
checksum of the header's bytes along with the header's checksum itself will
always result in 0.
.bp
.ps
.ft R
.SUBSUBSECTION "CRC-16"
.PP
CRC-16 is used the checksum the entire FLAC frame, including the header.
Given a byte input and the previous CRC-16 checksum,
or 0 as an initial value, the current checksum can be calculated as follows:
.EQ
{checksum sub i}~=~{roman "CRC16"} ( byte~{roman "xor"}~({checksum sub {i - 1}} >> 8 ) )~{roman "xor"}~({checksum sub {i - 1}} << 8)
.EN
the checksum is then truncated to 16-bits.
.ps 5
.ft C
.TS
tab(:);
| c s s s s s s s s s s s s s s s s |
| r || c | c | c | c | c | c | c | c | c | c | c | c | c | c | c | c |
| r || r | r | r | r | r | r | r | r | r | r | r | r | r | r | r | r |.
_
.ps 8
.ft R
CRC-16
.ps 5
.ft C
_
:0x?0:0x?1:0x?2:0x?3:0x?4:0x?5:0x?6:0x?7:0x?8:0x?9:0x?A:0x?B:0x?C:0x?D:0x?E:0x?F
=
0x0?:0x0000:0x8005:0x800f:0x000a:0x801b:0x001e:0x0014:0x8011:0x8033:0x0036:0x003c:0x8039:0x0028:0x802d:0x8027:0x0022
0x1?:0x8063:0x0066:0x006c:0x8069:0x0078:0x807d:0x8077:0x0072:0x0050:0x8055:0x805f:0x005a:0x804b:0x004e:0x0044:0x8041
0x2?:0x80c3:0x00c6:0x00cc:0x80c9:0x00d8:0x80dd:0x80d7:0x00d2:0x00f0:0x80f5:0x80ff:0x00fa:0x80eb:0x00ee:0x00e4:0x80e1
0x3?:0x00a0:0x80a5:0x80af:0x00aa:0x80bb:0x00be:0x00b4:0x80b1:0x8093:0x0096:0x009c:0x8099:0x0088:0x808d:0x8087:0x0082
0x4?:0x8183:0x0186:0x018c:0x8189:0x0198:0x819d:0x8197:0x0192:0x01b0:0x81b5:0x81bf:0x01ba:0x81ab:0x01ae:0x01a4:0x81a1
0x5?:0x01e0:0x81e5:0x81ef:0x01ea:0x81fb:0x01fe:0x01f4:0x81f1:0x81d3:0x01d6:0x01dc:0x81d9:0x01c8:0x81cd:0x81c7:0x01c2
0x6?:0x0140:0x8145:0x814f:0x014a:0x815b:0x015e:0x0154:0x8151:0x8173:0x0176:0x017c:0x8179:0x0168:0x816d:0x8167:0x0162
0x7?:0x8123:0x0126:0x012c:0x8129:0x0138:0x813d:0x8137:0x0132:0x0110:0x8115:0x811f:0x011a:0x810b:0x010e:0x0104:0x8101
0x8?:0x8303:0x0306:0x030c:0x8309:0x0318:0x831d:0x8317:0x0312:0x0330:0x8335:0x833f:0x033a:0x832b:0x032e:0x0324:0x8321
0x9?:0x0360:0x8365:0x836f:0x036a:0x837b:0x037e:0x0374:0x8371:0x8353:0x0356:0x035c:0x8359:0x0348:0x834d:0x8347:0x0342
0xA?:0x03c0:0x83c5:0x83cf:0x03ca:0x83db:0x03de:0x03d4:0x83d1:0x83f3:0x03f6:0x03fc:0x83f9:0x03e8:0x83ed:0x83e7:0x03e2
0xB?:0x83a3:0x03a6:0x03ac:0x83a9:0x03b8:0x83bd:0x83b7:0x03b2:0x0390:0x8395:0x839f:0x039a:0x838b:0x038e:0x0384:0x8381
0xC?:0x0280:0x8285:0x828f:0x028a:0x829b:0x029e:0x0294:0x8291:0x82b3:0x02b6:0x02bc:0x82b9:0x02a8:0x82ad:0x82a7:0x02a2
0xD?:0x82e3:0x02e6:0x02ec:0x82e9:0x02f8:0x82fd:0x82f7:0x02f2:0x02d0:0x82d5:0x82df:0x02da:0x82cb:0x02ce:0x02c4:0x82c1
0xE?:0x8243:0x0246:0x024c:0x8249:0x0258:0x825d:0x8257:0x0252:0x0270:0x8275:0x827f:0x027a:0x826b:0x026e:0x0264:0x8261
0xF?:0x0220:0x8225:0x822f:0x022a:0x823b:0x023e:0x0234:0x8231:0x8213:0x0216:0x021c:0x8219:0x0208:0x820d:0x8207:0x0202
_
.TE
.bp
.ps
.ft R
.LP
For example, given the frame bytes:
0xFF, 0xF8, 0xCC, 0x1C, 0x00, 0xC0, 0xEB, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00 and 0x00, the frame's CRC-16 can be calculated as
follows:
.EQ
{checksum sub 0}~ mark =~{roman "CRC16"} ( {roman "0xFF"}~{roman "xor"}~(0 >> 8 ) )~{roman "xor"}~(0 << 8)~=~{roman "CRC16"} ( {roman "0xFF"} )~{roman "xor"}~0~=~{roman "0x0202"}
.EN
.EQ
{checksum sub 1}~ lineup =~{roman "CRC16"} ( {roman "0xF8"}~{roman "xor"}~({roman "0x0202"} >> 8 ) )~{roman "xor"}~({roman "0x0202"} << 8)~=~{roman "CRC16"} ( {roman "0xFA"} )~{roman "xor"}~{roman "0x0200"}~=~{roman "0x001C"}
.EN
.EQ
{checksum sub 2}~ lineup =~{roman "CRC16"} ( {roman "0xCC"}~{roman "xor"}~({roman "0x001C"} >> 8 ) )~{roman "xor"}~({roman "0x001C"} << 8)~=~{roman "CRC16"} ( {roman "0xCC"} )~{roman "xor"}~{roman "0x1C00"}~=~{roman "0x1EA8"}
.EN
.EQ
{checksum sub 3}~ lineup =~{roman "CRC16"} ( {roman "0x1C"}~{roman "xor"}~({roman "0x1EA8"} >> 8 ) )~{roman "xor"}~({roman "0x1EA8"} << 8)~=~{roman "CRC16"} ( {roman "0x02"} )~{roman "xor"}~{roman "0xA800"}~=~{roman "0x280F"}
.EN
.EQ
{checksum sub 4}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x280F"} >> 8 ) )~{roman "xor"}~({roman "0x280F"} << 8)~=~{roman "CRC16"} ( {roman "0x28"} )~{roman "xor"}~{roman "0x0F00"}~=~{roman "0x0FF0"}
.EN
.EQ
{checksum sub 5}~ lineup =~{roman "CRC16"} ( {roman "0xC0"}~{roman "xor"}~({roman "0x0FF0"} >> 8 ) )~{roman "xor"}~({roman "0x0FF0"} << 8)~=~{roman "CRC16"} ( {roman "0xCF"} )~{roman "xor"}~{roman "0xF000"}~=~{roman "0xF2A2"}
.EN
.EQ
{checksum sub 6}~ lineup =~{roman "CRC16"} ( {roman "0xEB"}~{roman "xor"}~({roman "0xF2A2"} >> 8 ) )~{roman "xor"}~({roman "0xF2A2"} << 8)~=~{roman "CRC16"} ( {roman "0x19"} )~{roman "xor"}~{roman "0xA200"}~=~{roman "0x2255"}
.EN
.EQ
{checksum sub 7}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x2255"} >> 8 ) )~{roman "xor"}~({roman "0x2255"} << 8)~=~{roman "CRC16"} ( {roman "0x22"} )~{roman "xor"}~{roman "0x5500"}~=~{roman "0x55CC"}
.EN
.EQ
{checksum sub 8}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x55CC"} >> 8 ) )~{roman "xor"}~({roman "0x55CC"} << 8)~=~{roman "CRC16"} ( {roman "0x55"} )~{roman "xor"}~{roman "0xCC00"}~=~{roman "0xCDFE"}
.EN
.EQ
{checksum sub 9}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0xCDFE"} >> 8 ) )~{roman "xor"}~({roman "0xCDFE"} << 8)~=~{roman "CRC16"} ( {roman "0xCD"} )~{roman "xor"}~{roman "0xFE00"}~=~{roman "0x7CAD"}
.EN
.EQ
{checksum sub 10}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x7CAD"} >> 8 ) )~{roman "xor"}~({roman "0x7CAD"} << 8)~=~{roman "CRC16"} ( {roman "0x7C"} )~{roman "xor"}~{roman "0xAD00"}~=~{roman "0x2C0B"}
.EN
.EQ
{checksum sub 11}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x2C0B"} >> 8 ) )~{roman "xor"}~({roman "0x2C0B"} << 8)~=~{roman "CRC16"} ( {roman "0x2C"} )~{roman "xor"}~{roman "0x0B00"}~=~{roman "0x8BEB"}
.EN
.EQ
{checksum sub 12}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x8BEB"} >> 8 ) )~{roman "xor"}~({roman "0x8BEB"} << 8)~=~{roman "CRC16"} ( {roman "0x8B"} )~{roman "xor"}~{roman "0xEB00"}~=~{roman "0xE83A"}
.EN
.EQ
{checksum sub 13}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0xE83A"} >> 8 ) )~{roman "xor"}~({roman "0xE83A"} << 8)~=~{roman "CRC16"} ( {roman "0xE8"} )~{roman "xor"}~{roman "0x3A00"}~=~{roman "0x3870"}
.EN
.EQ
{checksum sub 14}~ lineup =~{roman "CRC16"} ( {roman "0x00"}~{roman "xor"}~({roman "0x3870"} >> 8 ) )~{roman "xor"}~({roman "0x3870"} << 8)~=~{roman "CRC16"} ( {roman "0x38"} )~{roman "xor"}~{roman "0x7000"}~=~{roman "0xF093"}
.EN
Thus, the next two bytes after the final subframe should be 0xF0 and 0x93.
Again, when the checksum bytes are run through the checksumming procedure,
as follows:
.EQ
{checksum sub 15}~ lineup =~{roman "CRC16"} ( {roman "0xF0"}~{roman "xor"}~({roman "0xF093"} >> 8 ) )~{roman "xor"}~({roman "0xF093"} << 8)~=~{roman "CRC16"} ( {roman "0x00"} )~{roman "xor"}~{roman "0x9300"}~=~{roman "0x9300"}
.EN
.EQ
{checksum sub 16}~ lineup =~{roman "CRC16"} ( {roman "0x93"}~{roman "xor"}~({roman "0x9300"} >> 8 ) )~{roman "xor"}~({roman "0x9300"} << 8)~=~{roman "CRC16"} ( {roman "0x00"} )~{roman "xor"}~{roman "0x0000"}~=~{roman "0x0000"}
.EN
the result will also always be 0, just as in the CRC-8.

