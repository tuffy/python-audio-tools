.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SUBSUBSECTION "the Xing header"
.PP
An MP3 frame header contains the track's sampling rate,
bits-per-sample and number of channels.
However, because MP3 files are little more than
concatenated MPEG frames, there is no obvious place to
store the track's total length.
Since the length of each frame is a constant number of samples,
one can calculate the track length by counting the number of frames.
This method is the most accurate but is also quite slow.
.PP
For MP3 files in which all frames have the same bitrate
- also known as constant bitrate, or CBR files -
one can divide the total size of file (minus any ID3 headers/footers),
by the bitrate to determine its length.
If an MP3 file has no Xing header in its first frame,
one can assume it is CBR.
.PP
An MP3 file that does contain a Xing header in its first frame
can be assumed to be variable bitrate, or VBR.
In that case, the rate of the first frame cannot be used as a
basis to calculate the length of the entire file.
Instead, one must use the information from the Xing header
which contains that length.
.PP
All of the fields within a Xing header are big-endian.
.begin dformat
style bitwid 0.16
style recspread 0
noname
  0-31-32 Header `Xing' (0x58696E67)
noname
  32-63-32 Flags
noname
  64-95-32 Number of Frames
noname
  96-127-32 Bytes
noname
  128-135-8 TOC @roman Entry sub 1 @
  136-143-8 TOC @roman Entry sub 2 @
  144-919-8-dashed ...
  920-927-8 TOC @roman Entry sub 100 @
noname
  928-959-32 Quality
.end dformat
