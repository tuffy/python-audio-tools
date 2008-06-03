.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SUBSECTION "the ID3v1 tag"
.PP
ID3v1 tags are very simple metadata tags appended to an MP3 file.
All of the fields are fixed length and the text encoding is
undefined.
There are two versions of ID3v1 tags.
ID3v1.1 has a track number field as a 1 byte value
at the end of the comment field.
If the byte just before the end is not null (0x00),
assume we're dealing with a classic ID3v1 tag without a
track number.
.PP
Obviously, ID3v1 tags are insufficient for any nontrivial
metadata.
They are often still added for compatibility reasons, however.

.SUBSUBSECTION "ID3v1"
.PP
.begin dformat
style bitwid 0.18
style recspread 0
noname
     0-23-15 Header (`TAG' 0x544147)
noname
     24-263-30 Track Title
noname
     264-503-30 Artist Name
noname
     504-743-30 Album Name
noname
     744-775-10 Year
noname
     776-1015-30 Comment
noname
     1016-1023-10 Genre
.end dformat

.SUBSUBSECTION "ID3v1.1"
.PP
.begin dformat
style bitwid 0.18
style recspread 0
noname
     0-23-15 Header (`TAG' 0x544147)
noname
     24-263-30 Track Title
noname
     264-503-30 Artist Name
noname
     504-743-30 Album Name
noname
     744-775-10 Year
noname
     776-999-20 Comment
     1000-1007-5 NULL (0x00)
     1008-1015-5 Track Number
noname
     1016-1023-10 Genre
.end dformat
