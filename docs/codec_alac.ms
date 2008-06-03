.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SUBSECTION "the Apple Lossless codec"
.PP
The Apple Lossless stream is made up of individual Apple Lossless
frames found in the `mdat' atom, which is typically the final atom
in the file.
.SUBSUBSECTION "the Frame Header"
.PP
.begin dformat
style bitwid 0.64
style recspread 0
noname
  0-2-2 Channels
  3-6-3 Unknown
  7-18-3 Unknown
noname
  19-19-2 Has Size
  20-21-4 Wasted Bytes
  22-22-2 Not Compressed
noname
  23-54-8-dashed Output Samples
.end dformat
If `Has Size' is not 0, there is a 32-bit `Output Samples'
value at the end of the frame header.
