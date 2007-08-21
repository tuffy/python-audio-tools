.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "Musepack"
.PP
Musepack is a lossy audio format based on MP2 and designed for
transparency.
All of its fields are little-endian.
.SUBSECTION "the Musepack file stream"
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
       0-223-20 Musepack header
       224--16 @roman Frame sub 1@
       --16 @roman Frame sub 2@
       --16-dashed ...
       --16 APEv2 tag
.end dformat
.bp
.SUBSECTION "the Musepack header"
.PP
.begin dformat
style bitwid 0.32
style recspread 0
noname
  0-23-12 Signature (`MP+' 0x4D502B)
  24-31-4 Version (0x07)
noname
  32-63-16 Frame Count
noname
  64-79-16 Max Level
noname
  80-83-8 Profile
  84-85-4 Link
  86-87-4 Sample Rate
noname
  88-88-3 Intensity Stereo
  89-89-3 Midside Stereo
  90-95-10 Max Band
noname
  96-111-8 Title Gain
  112-127-8 Title Peak
noname
  128-143-8 Album Gain
  144-159-8 Album Peak
noname
  160-175-16 Unusued (0x00)
noname
  176-179-8 Last Frame Samples (low)
  180-180-3 True Gapless
  181-183-5 Unusued (0x00)
noname
  184-184-3 Fast Seeking
  185-191-13 Last Frame Samples (high)
noname
  192-215-10 Unknown
  216-223-6 Encoder Version
.end dformat
Each frame contains 1152 samples per channel.
Therefore:
.br
@"Total Samples" = (("Frame Count" - 1) * 1152) + "Last Frame Samples"@
.br
Musepack files always have exactly 2 channels and always have
16 bits per sample.
.2C
.TS
tab(:);
| c s |
| c | c |
| c | r |.
_
Sampling Rate
_
bits:rate
=
00:44100
01:48000
10:37800
11:32000
_
.TE
.KS
.TS
tab(:);
| c s |
| c | c |
| c | l |.
_
Profile
_
bits:used profile
=
0000:no profile
0001:Unstable/Experimental
0010:unused
0011:unusued
0100:unusued
0101:below Telephone
0110:below Telephone
0111:Telephone
1000:Thumb
1001:Radio
1010:Standard
1011:Xtreme
1100:Insane
1101:Braindead
1110:above Braindead
1111:above Braindead
_
.TE
.KE
.1C
