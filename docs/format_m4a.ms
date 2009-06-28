.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "M4A"
.PP
M4A is typically AAC audio in a QuickTime container stream, though
it may also contain other formats such as MPEG-1 audio.


.SUBSECTION "the QuickTime file stream"
.PP
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
       0--12 @roman Atom sub 1@
  A1:   --12 @roman Atom sub 2@
       --12 @roman Atom sub 3@
       --12 @roman Atom sub 4@
  A2:  --12 @roman Atom sub 5@
       --12-dashed ...
noname
  B1:  --12 @roman Atom sub 2 sub 1@
       --12 @roman Atom sub 2 sub 2@
  B2:  --12-dashed ...
       --8-invisible
  B3:  --12 @roman Atom sub 5 sub 1@
  B4:  --12 @roman Atom sub 5 sub 2@
  B5:  --12-dashed ...
noname
       --16-invisible
  C1:  --12 @roman Atom sub 5 sub 2 sub 1@
       --12 @roman Atom sub 5 sub 2 sub 2@
       --12 @roman Atom sub 5 sub 2 sub 3@
       --12 @roman Atom sub 5 sub 2 sub 4@
  C2:  --12-dashed ...
pic line dotted from A1.sw to B1.nw
pic line dotted from A1.se to B2.ne
pic line dotted from A2.sw to B3.nw
pic line dotted from A2.se to B5.ne
pic line dotted from B4.sw to C1.nw
pic line dotted from B4.se to C2.ne
.end dformat
Unlike other chunked formats such as RIFF WAVE, QuickTime's atom chunks
may be containers for other atoms.  All of its fields are big-endian.

.SUBSECTION "a QuickTime atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 Atom Length
    32-63-16 Atom Type
noname
    64--32-dashed Atom Data
.end dformat
Atom Type is an ASCII string.
Atom Length is the length of the entire atom, including the header.
If Atom Length is 0, the atom continues until the end of the file.
If Atom Length is 1, the atom has an extended size.  This means
there is a 64-bit length field immediately after the header which is
the atom's actual size.
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 False Atom Length (0x01)
    32-63-16 Atom Type
noname
    64-127-32 Atom Length
noname
    128--32-dashed Atom Data
.end dformat

.SUBSECTION "Container atoms"
.PP
There appears to be no flag or field to tell a QuickTime parser which
of its atoms are containers and which ones are not.
Instead, one must check against a table of known container atom types.
If an atom is known to be a container, one can treat its Atom Data
as a QuickTime stream and parse it in a recursive fashion.
.TS
tab(:);
c s s s s s s s
l l l l l l l l.
_
Known Container Atoms
=
dinf:edts:imag:imap:mdia:mdra:minf:moov
rmra:stbl:trak:tref:udta:vnrp::
_
.TE

.SUBSECTION "M4A atoms"
.PP
.mk
.PSPIC -R "m4a-atoms.eps" 2.25i
.rt
.PP
.ll 4in
A typical M4A begins with an `ftyp' atom indicating its file type,
followed by a `moov' atom containing a copious amount of file metadata,
an optional `free' atom with nothing but empty space
(so that metadata can be resized, if necessary) and an `mdat' atom
containing the song data itself.

.SUBSUBSECTION "the ftyp atom"
.PP
.ll 4in
.begin dformat
style bitwid 0.12
style recspread 0
noname
    0-31-16 ftyp Length
    32-63-16 `ftyp' (0x66747970)
noname
    64-95-16 Major Brand
    96-127-16 Major Brand Version
noname
    128-159-16-dashed Compatible @roman Brand sub 1@
    160--16-dashed ...
.end dformat
.PP
.ll 4in
The `Major Brand' and `Compatible Brand' fields are ASCII strings.
`Major Brand Version' is an integer.

.SUBSUBSECTION "the mvhd atom"
.PP
.ll 4in
.begin dformat
style bitwid 0.12
style recspread 0
noname
    0-31-16 mvhd Length
    32-63-16 `mvhd' (0x6D766864)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127/159-16 Created Mac UTC Date
    128/160-159/223-16 Modified Mac UTC Date
noname
    160/224-191/255-16 Time Scale
    192/256-223/319-16 Duration
noname
    224/320-255/351-16 Playback Speed
    256/352-271/367-8 User Volume
    272/368-351/447-8 Reserved (0)
noname
    352/448-383/479-8 WGM value A
    384/480-415/511-8 WGM value B
    416/512-447/543-8 WGM value U
    448/544-479/575-8 WGM value C
noname
    480/576-511/607-8 WGM value D
    512/608-543/639-8 WGM value V
    544/640-575/671-8 WGM value X
    576/672-607/703-8 WGM value Y
noname
    608/704-639/735-8 WGM value W
    640/736-703/799-24 Quicktime Preview
noname
    704/800-735/831-16 Quicktime Still Poster
    736/832-799/895-16 Quicktime selection time
noname
    800/896-831/927-16 Quicktime current time
    832/928-863/959-16 next/new track ID
.end dformat
.PP
.ll 4in
If `Version' is 0, `Created Mac UTC Date', `Modified Mac UTC Date' and
`Duration' are 32-bit fields.  If it is 1, they are 64-bit fields.

.bp

.SUBSUBSECTION "the tkhd atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 tkhd Length
    32-63-16 `tkhd' (0x746B6864)
noname
    64-71-3 Version
    72-91-5 Reserved (0)
    92-92-6 Track in Poster
    93-93-6 Track in Preview
    94-94-6 Track in Movie
    95-95-6 Track Enabled
noname
    96-127/159-16 Created Mac UTC Date
    128/160-159/223-16 Modified Mac UTC Date
noname
    160/224-191/255-8 Track ID
    192/256-255/319-24 Reserved (0)
noname
    256/320-287/383-16 Duration
    288/384-319/415-16 Reserved (0)
noname
    320/415-335/431-8 Video Layer
    336/432-351/447-8 Quicktime Alt/Other
    352/448-367/463-8 Audio Volume
    368/464-383/479-8 Reserved (0)
noname
    384/480-415/511-8 VGM value A
    416/512-447/543-8 VGM value B
    448/544-479/575-8 VGM value U
    480/576-511/607-8 VGM value C
noname
    512/608-543/639-8 VGM value D
    544/640-575/671-8 VGM value V
    576/672-607/703-8 VGM value X
    608/704-639/735-8 VGM value Y
noname
    640/736-671/767-8 VGM value W
    672/768-735/831-24 Video Frame Size
.end dformat
.PP
As with `mvhd', if `Version' is 0, `Created Mac UTC Date',
`Modified Mac UTC Date' and `Duration' are 32-bit fields.
If it is 1, they are 64-bit fields.


.SUBSUBSECTION "the mdhd atom"
.PP
The \fCmdhd\fR atom contains track information such as samples-per-second,
track length and creation/modification times.

.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 mdhd Length
    32-63-16 `mdhd' (0x6D646864)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127/159-16 Created Mac UTC Date
    128/60-159/223-16 Modified Mac UTC Date
noname
    160/224-191/255-16 Sample Rate
    192/256-223/319-16 Track Length
noname
    224/320-224/320-4 Pad
    225/321-239/335-12 Language
    240/336-255/351-16 Quality
.end dformat
.PP
As with `mvhd', if `Version' is 0, `Created Mac UTC Date',
`Modified Mac UTC Date' and `Track Length' are 32-bit fields.
If it is 1, they are 64-bit fields.

.bp

.SUBSUBSECTION "the hdlr atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 hdlr Length
    32-63-16 `hdlr' (0x68646C72)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-16 Quicktime type
    128-159-16 Subtype/media type
noname
    160-191-32 Quicktime manufacturer
noname
    192-223-16 Quicktime flags
    224-255-16 Quicktime flags mask
noname
    256-263-10 Component Name Length
    264--22-dashed Component Name
.end dformat
.PP
`Quicktime flags', `Quicktime flags mask' and `Component Name Length'
are integers.  The rest are ASCII strings.

.SUBSUBSECTION "the smhd atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 smhd Length
    32-63-16 `smhd' (0x736D6864)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-111-16 Audio Balance
    112-127-16 Reserved (0x0000)
.end dformat

.SUBSUBSECTION "the dref atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 dref Length
    32-63-16 `dref' (0x64726566)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-8 Number of References
    128--8-dashed Reference @roman Atom sub 1@
    --8-dashed Reference @roman Atom sub 2@
    --8-dashed ...
.end dformat

.SUBSUBSECTION "the stsd atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 stsd Length
    32-63-16 `stsd' (0x73747364)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-9 Number of Descriptions
    128--8-dashed Description @roman Atom sub 1@
    --8-dashed Description @roman Atom sub 2@
    --7-dashed ...
.end dformat

.bp

.SUBSUBSECTION "the mp4a atom"
.PP
The \fCmp4a\fR atom contains information such as the number of channels
and bits-per-sample.  It can be found in the \fCstsd\fR atom.

.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 mp4a Length
    32-63-16 `mp4a' (0x6D703461)
noname
    64-111-16 Reserved (0x000000000000)
    112-127-16 Reference Index
noname
    128-143-16 Quicktime Version
    144-159-16 Quicktime Revision Level
noname
    160-191-32 Quicktime Audio Encoding Vendor
noname
    192-207-16 Channels
    208-223-16 Bits Per Sample
noname
    224-239-16 Quicktime Compression ID
    240-255-16 Audio Packet Size
noname
     256-287-16 Audio Sample Rate
 M4: 288--16 `esds' atom
noname
    --32-invis
noname
 E1: 0-31-16 esds Length
 E2: 32-63-16 `esds' (0x65736473)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96--32 ESDS Atom Data
pic line dotted from M4.sw to E1.nw
pic line dotted from M4.se to E2.ne
.end dformat

.bp

.SUBSUBSECTION "the stts atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 stts Length
    32-63-16 `stts' (0x73747473)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-32 Number of Times
noname
    128-159-16 Frame @roman Count sub 1@
    160-191-16 @roman Duration sub 1@
noname
    192-223-16 Frame @roman Count sub 2@
    224-255-16 @roman Duration sub 2@
noname
    256--32-dashed ...
.end dformat

.SUBSUBSECTION "the stsc atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 stsc Length
    32-63-16 `stsc' (0x73747363)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-32 Number of Blocks
noname
    128-159-10 First @roman Chunk sub 1@
    160-191-11 Samples per @roman Chunk sub 1@
    192-223-11 Sample Duration @roman Index sub 1@
noname
    224-255-10 First @roman Chunk sub 2@
    256-287-11 Samples per @roman Chunk sub 2@
    288-319-11 Sample Duration @roman Index sub 2@
noname
    320--32-dashed ...
.end dformat


.SUBSUBSECTION "the stsz atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 stsz Length
    32-63-16 `stsz' (0x7374737A)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-32 Number of Block Sizes
noname
    128-159-10 Block @roman Size sub 1@
    160-191-11 Block @roman Size sub 2@
    192--11-dashed ...
.end dformat

.bp

.SUBSUBSECTION "the stco atom"
.PP
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 stco Length
    32-63-16 `stco' (0x7374636F)
noname
    64-71-8 Version
    72-95-24 Flags (0x000000)
noname
    96-127-32 Number of Offsets
noname
    128-159-10 @roman Offset sub 1@
    160-191-11 @roman Offset sub 2@
    192--11-dashed ...
.end dformat
.PP
Offsets point to the absolute position in the M4A file of AAC data in
the `mdat' atom, the first of which is the first non-NULL byte after the
`mdat' header.  Therefore, if the `moov' atom size changes
(which can happen by writing new metadata in its `meta' child atom)
the `mdat' atom may move and these obsolute offsets will change.
In that instance, they
.B
must
.R
be re-adjusted in the `stco' atom or the file may become unplayable.

.SUBSUBSECTION "the meta atom"
.PP
.mk
.PSPIC -R "m4a-meta.eps" 1.75i
.rt
.PP
.ll 4.5in
.begin dformat
style bitwid 0.14
style recspread 0
noname
       0-31-16 Meta Length
       32-63-16 `meta' (0x6D657461)
noname
       64-71-8 Version
       72-95-24 Flags (0x000000)
noname
       96--8 `ftyp' atom
       --8 `ilst' atom
       --8 `free' atom
       --8-dashed ...
.end dformat
.PP
.ll 4.5in
The atoms within \fCilst\fR are all containers, each with a
\fCdata\fR atom of its own.  Notice that many of \fCilst\fR's sub-atoms
begin with the non-ASCII 0xA9 byte.

.bp

.ps 8
.TS
tab(:);
| c s s s s s |
| r | c | l || r | c | l |.
_
Known \fCmeta\fR Sub-Atoms
_
Atom Type:Hex:Description:Atom Type:Hex:Description
=
aaid:\fC0x61616964\fR:Artist Name:alb:\fC0xA9616C62\fR:Album Name
akid:\fC0x616B6964\fR:Alternative ID ?:apid:\fC0x61706964\fR:Apple ID
ART:\fC0xA9415254\fR:Performer Name:cmt:\fC0xA9636D74\fR:Comment
com:\fC0xA9636F6D\fR:Composer:covr:\fC0x636F7672\fR:Cover Image
cpil:\fC0x6370696C\fR:Compilation:cprt:\fC0x63707274\fR:Copyright ?
day:\fC0xA9646179\fR:Date:disk:\fC0x6469736B\fR:Disc X of Y
geid:\fC0x67656964\fR:iTMS ID ?:gnre:\fC0x676E7265\fR:Genre
grp:\fC0xA9677270\fR:Group ?:nam:\fC0xA96E616D\fR:Track Name
plid:\fC0x706C6964\fR:Purchase ID ?:rtng:\fC0x72746E67\fR:Rating
stik:\fC0x7374696B\fR:Movie Type:tmpo:\fC0x746D706F\fR:Tempo
too:\fC0xA9746F6F\fR:Encoder:trkn:\fC0x74726B6E\fR:Track Number
wrt:\fC0xA9777274\fR:Composer:----:\fC0x2D2D2D2D\fR:iTunes-specific
_
.TE
.ps 10

The \fCdata\fR sub-atoms contain the actual metadata, naturally,
but that data is preceded by 8 bytes of additional information.

.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-31-16 Data Length
    32-63-16 `data' (0x64617461)
noname
    64-127-32 Flags
noname
    128--32-dashed Data
.end dformat

.bp

.SUBSUBSECTION "the trkn sub-atom"
.PP
\fCtrkn\fR is a binary sub-atom of \fCmeta\fR which contains
the track number.

.begin dformat
style bitwid 0.16
style recspread 0
noname
     0-31-8 trkn Length
     32-63-8 `trkn' (0x74726B6E)
 M1: 64--8-dashed Data Atom
noname
    --32-invisible
noname
 M2: 0-31-16 data Length
 M3: 32-63-16 `data' (0x64617461)
noname
    64-127-32 Flags (0x00000000)
noname
    128-143-8 NULL (0x0000)
    144-159-8 Track Number
    160-175-8 Total Tracks
    176-191-8 NULL (0x0000)
pic line dotted from M1.sw to M2.nw
pic line dotted from M1.se to M3.ne
.end dformat

.SUBSUBSECTION "the disk sub-atom"
.PP
\fCdisk\fR is a binary sub-atom of \fCmeta\fR which contains
the disc number.
For example, if the track belongs to the first disc in a set of
two discs, the sub-atom will contain that information.

.begin dformat
style bitwid 0.16
style recspread 0
noname
     0-31-8 trkn Length
     32-63-8 `disk' (0x6469736B)
 M1: 64--8-dashed Data Atom
noname
    --32-invisible
noname
 M2: 0-31-16 data Length
 M3: 32-63-16 `data' (0x64617461)
noname
    64-127-32 Flags (0x00000000)
noname
    128-143-10 NULL (0x0000)
    144-159-11 Disc Number
    160-175-11 Total Discs
pic line dotted from M1.sw to M2.nw
pic line dotted from M1.se to M3.ne
.end dformat
