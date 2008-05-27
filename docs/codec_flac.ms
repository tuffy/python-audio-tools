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
no wasted bits per sample.  Otherwise, it is a unary-encoded value
indicating how many bits are wasted per sample.
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
2:@"Sample" sub i = (2 * "Sample" sub {i~-~1})~~-~~"Sample" sub {i~-~2}~~+~~"Residual" sub i@
3:@"Sample" sub i = (3 * "Sample" sub {i~-~1})~~-~~(3 * "Sample" sub {i~-~2})~~+~~"Sample" sub {i~-~3}~~+~~"Residual" sub i@
4:@"Sample" sub i = (4 * "Sample" sub {i~-~1})~~-~~(6 * "Sample" sub {i~-~2})~~+~~(4 * "Sample" sub {i~-~3})~~-~~"Sample" sub {i~-~4}~~+~~"Residual" sub i@
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
  0-3-14 LPC Precision
  4-8-16 LPC Shift Needed
  9-?-14 @roman Coefficient sub 1@
  --14 @roman Coefficient sub 2@
  --14-dashed ...
noname
  --72 Residual
.end dformat
The number of warm-up samples equals the `LPC Order'
(which is encoded in the `Subframe Type').
The size of each Coefficient is equal to
`LPC Precision' number of bits, plus 1.
The value of each Coefficient is a signed two's-complement integer.
The number of Coefficients equals the `LPC Order'.
.EQ
"Sample" sub i =
{
{sum from {j = 0} to {Order~-~1}
{"Coefficient" sub j} * "Sample" sub {i~-~j~-~1}}
} over {2 sup "LPC Shift Needed"}
~~+~~"Residual" sub i
.EN
Don't be intimidated by the \[*S] if you're not math-inclined.
It simply means we're taking the sum of the calculated values from
0 to Order - 1, bit-shifting that sum down and added the residual
when determining the current sample.
Much like the FIXED subframe, LPC subframes also contain warm-up
samples which serve as our calculation's starting point.
.PP
In this example, the LPC Order is 5, the LPC Shift Needed is 9
and the encoded Coefficients are as follows:
.KS
.TS
tab(:);
c r.
@roman Coefficient sub 0@:1241
@roman Coefficient sub 1@:-944
@roman Coefficient sub 2@:14
@roman Coefficient sub 3@:342
@roman Coefficient sub 4@:-147
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
5:11:@(1241 * 1529) + (-944 * 1423) + (14 * 1257) + (342 * 1116) + (-147 * 1053) = 798656@
\^:\^:@(798656~/~2 sup 9 ) = 1559 + 11 = bold 1570@
_
6:79:@(1241 * 1570) + (-944 * 1529) + (14 * 1423) + (342 * 1257) + (-147 * 1116) = 790758@
\^:\^:@(790758~/~2 sup 9 ) = 1544 + 79 = bold 1623@
_
7:24:@(1241 * 1623) + (-944 * 1570) + (14 * 1529) + (342 * 1423) + (-147 * 1257) = 855356@
\^:\^:@(855356~/~2 sup 9 ) = 1670 + 24 = bold 1694@
_
8:-81:@(1241 * 1694) + (-944 * 1623) + (14 * 1570) + (342 * 1529) + (-147 * 1423) = 905859@
\^:\^:@(905859~/~2 sup 9 ) = 1769 - 81 = bold 1688@
_
9:-72:@(1241 * 1688) + (-944 * 1694) + (14 * 1623) + (342 * 1570) + (-147 * 1529) = 830571@
\^:\^:@(830571~/~2 sup 9 ) = 1622 - 72 = bold 1550@
_
.TE
.LP
In this instance, division should always round down and \fInot\fR towards zero.
For example: @-5~/~2 sup 1 = -3@

.bp
.SUBSUBSECTION "the Residual"
.nr ZR \n%
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
string length * 8:vendor string data, as UTF-8 encoded text
32\[dd]:total number of comment strings
32\[dd]:comment @roman string sub 1@ length, in bytes
string length * 8:comment @roman string sub 1@, as UTF-8 encoded text
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
(called ``channel independent samples'' in FLAC's documention)
is typically encoded in the 4 bit `block size' field.
But for odd-sized frames - which often occur at the end of the stream -
that value is stored as an 8 or 16 bit integer following UTF-8 encoded
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
Determing which predictor order to use on a given set of input samples
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
2:@"Residual" sub i = "Sample" sub i~~-~~((2 * "Sample" sub {i~-~1})~~-~~"Sample" sub {i~-~2})@
3:@"Residual" sub i = "Sample" sub i~~-~~((3 * "Sample" sub {i~-~1})~~-~~(3 * "Sample" sub {i~-~2})~~+~~"Sample" sub {i~-~3})@
4:@"Residual" sub i = "Sample" sub i~~-~~((4 * "Sample" sub {i~-~1})~~-~~(6 * "Sample" sub {i~-~2})~~+~~(4 * "Sample" sub {i~-~3})~~-~~"Sample" sub {i~-~4})@
_
.TE
.\"In this example, the residual values are: -1 1 1 1 0 3 0 -4 -1 0 1 1 1 4 -3 1 4 -1 -1
.bp
.SUBSUBSECTION "the LPC subframe"
.PP
Unlike the FIXED subframe which required only input samples and a
predictor order, LPC subframes also require a list of coefficients,
an LPC precision value of those coefficients, and an LPC shift needed
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
  0-3-14 LPC Precision
  4-8-16 LPC Shift Needed
  9-?-14 @roman Coefficient sub 1@
  --14 @roman Coefficient sub 2@
  --14-dashed ...
noname
  --72 Residual
.end dformat
.\"FIXME - need to figure out how to determine the best predictor order
.SUBSUBSUBSECTION "Autocorrelation values"
.PP
TODO: explain what these are used for.
.2C
.KS
.TS
tab(:);
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r s s s r |.
_
sample::@roman lag sub 0@::value
=
-39:\[mu]:-39:\[eq]:1521
-38:\[mu]:-38:\[eq]:1444
-37:\[mu]:-37:\[eq]:1369
-33:\[mu]:-33:\[eq]:1089
-36:\[mu]:-36:\[eq]:1296
-35:\[mu]:-35:\[eq]:1225
-31:\[mu]:-31:\[eq]:961
-32:\[mu]:-32:\[eq]:1024
-33:\[mu]:-33:\[eq]:1089
_
@roman lag sub 0@ sum:11018
_
.TE
.KE
.KS
.TS
tab(:);
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r s s s r |.
_
sample::@roman lag sub 1@::value
=
-39:\[mu]:-38:\[eq]:1482
-38:\[mu]:-37:\[eq]:1406
-37:\[mu]:-33:\[eq]:1221
-33:\[mu]:-36:\[eq]:1188
-36:\[mu]:-35:\[eq]:1260
-35:\[mu]:-31:\[eq]:1085
-31:\[mu]:-32:\[eq]:992
-32:\[mu]:-33:\[eq]:1056
_
@roman lag sub 1@ sum:9690
_
.TE
.KE
.KS
.TS
tab(:);
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r s s s r |.
_
sample::@roman lag sub 2@::value
=
-39:\[mu]:-37:\[eq]:1443
-38:\[mu]:-33:\[eq]:1254
-37:\[mu]:-36:\[eq]:1332
-33:\[mu]:-35:\[eq]:1155
-36:\[mu]:-31:\[eq]:1116
-35:\[mu]:-32:\[eq]:1120
-31:\[mu]:-33:\[eq]:1023
_
@roman lag sub 2@ sum:8443
_
.TE
.KE
.KS
.TS
tab(:);
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r s s s r |.
_
sample::@roman lag sub 3@::value
=
-39:\[mu]:-33:\[eq]:1287
-38:\[mu]:-36:\[eq]:1368
-37:\[mu]:-35:\[eq]:1295
-33:\[mu]:-31:\[eq]:1023
-36:\[mu]:-32:\[eq]:1152
-35:\[mu]:-33:\[eq]:1155
_
@roman lag sub 3@ sum:7280
_
.TE
.KE
.KS
.TS
tab(:);
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r c r c r |
| r s s s r |.
_
sample::@roman lag sub 4@::value
=
-39:\[mu]:-36:\[eq]:1404
-38:\[mu]:-35:\[eq]:1330
-37:\[mu]:-31:\[eq]:1147
-33:\[mu]:-32:\[eq]:1056
-36:\[mu]:-33:\[eq]:1188
_
@roman lag sub 4@ sum:6125
_
.TE
.KE
.1C
.SUBSUBSUBSECTION "LP coefficient calculation"
.PP
Calculating the LP coefficients uses the Levinson-Durbin recursive method.\(dg
.FS
\(dg This algorithm is taken from http://www.engineer.tamuk.edu/SPark/chap7.pdf
.FE
Our inputs are @M@, the maximum LPC order minus 1, and @r@ autocorrelation
values, from @r(0)@ to @r(M - 1)@.
Our ouputs are @a@, a list of LP coefficient lists from
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
Let's run through an example in which @r(0) = 11018@, @r(1) = 9690@,
@r(2) = 8443@ and @r(3) = 7280@:
.br
.ps 8
@E sub 0 mark = 11018@
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
.SUBSUBSECTION "the Residual"
.PP
Given a stream of residual values, one must place them in one or more
partitions, each with its own Rice parameter, and prepended with a
small header.\(dg
.FS
\(dg See page \n(ZR for full details of how the residual is organized.
.FE
The residual's coding method is typically 0, unless one is encoding
audio with more than 16 bits-per-sample and one of the partitions
requests a Rice parameter higher than @2 sup 4@.
The residual's partition order is chosen exhaustively, which means
trying all of them within a certain range (e.g. 0 to 5) such that
the residuals can be divided evenly between them and then the partiton
order which uses the smallest estimated amount of space is chosen.
.PP
Choosing the best Rice parameter is a matter of selecting the smallest
value of `x' such that:
.EQ
"sample count" * {2 sup x}~~>~~{sum from {i = 0} to {"residual count"~-~1}
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
@19 * {2 sup 0}@ is not larger than 29.
.br
@19 * {2 sup 1}@ is larger than 29, so the best Rice parameter
for this block of residuals is 1.
.PP
Remember that the Rice parameter's maximum value is limited to
@2 sup 4@ using coding method 0, or @2 sup 5@ using coding method 1.
