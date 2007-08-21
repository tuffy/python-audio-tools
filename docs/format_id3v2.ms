.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSECTION "the ID3v2 tag"
.PP
The ID3v2 tag was invented to address the deficiencies in the original
ID3v1 tag.
All of its fields are big-endian.
.SUBSUBSECTION "the ID3v2 stream"
.PP
.begin dformat
style bitwid 0.06
style charwid 0
style recspread 0.3
noname
       0-79-16 Header
       --16-dashed Extended
       --16 ID3v2 @roman Frame sub 1@
       --16 ID3v2 @roman Frame sub 2@
       --16-dashed ...
       --16-dashed Padding
.end dformat
.so format_id3v2_2.ms
.bp
.so format_id3v2_3.ms
.bp
.so format_id3v2_4.ms
