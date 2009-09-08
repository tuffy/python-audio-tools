.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.CHAPTER "MusicBrainz"
.PP
MusicBrainz is another CD metadata retrieval service similar to FreeDB.
It features the ability to query by release, track, artist and so forth.
All searches are HTTP GET queries to a MusicBrainz server which then
returns an XML file containing metadata.
.SECTION "Searching Releases"
.PP
This is analagous to FreeDB's search routine in which one calculates
a CD's disc ID, submits it to MusicBrainz and receives information such as
album name, artist name, track names and so forth.
.SUBSECTION "The Disc ID"
.PP
Calculating a MusicBrainz disc ID requires knowing a CD's first track number,
last track number, track offsets (in CD frames) and lead out track offset
(also in CD frames).
For example, given the following CD:
.PP
.TS
tab(~);
| c | s s s s s s |
| c | c s s || c s s |
| c | r r r || r r r |.
_
Example Audio Disc
_
Track~Length~Offset
Number~in Minutes:Seconds~in Seconds~in Frames~in Minutes:Seconds~in Seconds~in Frames
=
1~3:37~217~16340~0:02~2~150
2~3:23~203~15294~3:39~219~16490
3~3:37~217~16340~7:03~423~31784
4~3:20~200~15045~10:41~641~48124
_
.TE
.PP
The first track number is 1, the last track number is 4, the track offsets
are 150, 16490, 31784 and 48124, and the lead out track offset is
63169 (track 4's offset 48124 plus its length of 15045).
.PP
These numbers are then converted to 0-padded, big-endian hexadecimal strings
with the track numbers using 2 digits and the offsets using 8 digits.
In this example, the first track number becomes `01',
the last track number becomes `04',
the track offsets become `00000096', `0000406A', `00007C28' and `0000BBFC',
and the lead out track offset becomes `0000F6C1'.
.PP
These individual strings are then combined into a single 804 byte long string:
.begin dformat
style bitwid 0.10
style charwid 0
style recspread 0
noname
  0-15-12 First Track Number
  16-31-12 Last Track Number
  32-95-10 Lead Out Offset
  96-127-7 @roman Offset sub 1@
  128-191-7 @roman Offset sub 2@
  --7-dashed ...
  6368-6431-7 @roman Offset sub 99@
.end dformat
Excess track offsets are treated as having an offset value of 0,
or a string value of `00000000'.
Our string starts with `01040000F6C1000000960000406A00007C280000BBFC'
and is padded with an additional 760 `0' characters which I'll omit for brevity.
.PP
That string is then passed through the SHA-1 hashing algorithm\(dg
which results in a 20 byte long hash value.
Remember to use the binary hash value, not its 40 byte ASCII hexadecimal one.
To continue our example, this yields the hash
0xDA3D930462773DD57BBE43B535AD6A457138F079.
.PP
The resulting hash value is then encoded to a 28 byte Base64\(dd string.
However, unlike standard Base64, MusicBrainz's disc ID replaces the
characters `=', `+' and `/' with `-', `.' and `_' respectively to
make the value better suited to HTTP requests.
So to complete our example, the hash value becomes a disc ID of
`2j2TBGJ3PdV7vkO1Na1qRXE48Hk-'

.FS
\(dg This is described in RFC3174
.FE
.FS
\(dd This is described in RFC3548 and RFC4648
.FE
.bp
.SUBSECTION "Server Query"
.PP
MusicBrainz runs as a service on HTTP port 80.
To retrieve Release information, one can make a GET request to
\fC/ws/1/release\fR using the following fields:
.TS
tab(:);
| c | c |
| r | l |.
_
key:value
=
\fCtype\fR:\fCxml\fR
\fCdiscid\fR:\fC<disc ID string>\fR
_
.TE
For example, to retrieve the Release data for disc ID
`2jmj7l5rSw0yVb_vlWAYkK_YBwk-' one sends the GET query:
.br
.ft C
.ps 8
type=xml&discid=2jmj7l5rSw0yVb_vlWAYkK_YBwk-
.ps
.ft
.LP
Whether the Release is found in the MusicBrainz database or not,
an XML file will always be generated.
.SUBSECTION "Release XML"
.PP
