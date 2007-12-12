.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSECTION "the FLAC codec"
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
0001:192:reserved:2:left, right:0001
0010:576:reserved:3:left, right, center:0010
0011:1152:reserved:4:left, right, back left, back right:0011
0100:2304:8000:5:left, right, center, back left, back right:0100
0101:4608:16000:6:left, right, center, LFE, back left, back right:0101
0110:get 8 bit from end of header:22050:7:undefined:0110
0111:get 16 bit from end of header:24000:8:undefined:0111
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
