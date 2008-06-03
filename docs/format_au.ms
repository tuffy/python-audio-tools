.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Sun AU"
.PP
The AU file format was invented by Sun Microsystems
and also used on NeXT systems.
All values in AU are stored as big-endian.
It supports a wide array of data formats, including µ-law logarithmic
encoding, but can also be used as a PCM container.
.SUBSECTION "the AU stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
    0-191-16 Header
    192--16 Info
    --48-dashed Data
.end dformat

.SUBSECTION "the AU header"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-24 Magic Number (`.snd' 0x2e736e64)
noname
    32-63-24 Data Offset
noname
    64-95-24 Data Size
noname
    96-127-24 Encoding Format
noname
    128-159-24 Sample Rate
noname
    160-191-24 Channels
.end dformat

.TS
tab(:);
| c s |
| c | c |
| r | l |.
_
Encoding Formats
_
value:format
=
1:8-bit G.711 µ-law
2:8-bit linear PCM
3:16-bit linear PCM
4:24-bit linear PCM
5:32-bit linear PCM
6:32-bit IEEE floating point
7:64-bit IEEE floating point
8:Fragmented sample data
9:DSP program
10:8-bit fixed point
11:16-bit fixed point
12:24-bit fixed point
13:32-bit fixed point
18:16-bit linear with emphasis
19:16-bit linear compressed
20:16-bit linear with emphasis and compression
21:Music kit DSP commands
23:4-bit ISDN u-law compressed using the ITU-T G.721 ADPCM voice data encoding scheme
24:ITU-T G.722 ADPCM
25:ITU-T G.723 3-bit ADPCM
26:ITU-T G.723 5-bit ADPCM
27:8-bit G.711 A-law
_
.TE
