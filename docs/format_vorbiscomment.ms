.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
The length fields are all little-endian.
The Vendor String and Comment Strings are all UTF-8 encoded.
Keys are not case-sensitive and may occur multiple times,
indicating multiple values for the same field.
For instance, a track with multiple artists may have
more than one \fCARTIST\fR.
.ps 8
.TS
tab(:);
| c s s s |
| r | l || r | l |.
_
Comment Strings
_
key:value:key:value
=
ALBUM:album name:ARTIST:artist name, band name, composer, author, etc.
CATALOGNUMBER\(dg:CD spine number:COMPOSER\(dg:the work's author
CONDUCTOR\(dg:performing ensemble's leader:COPYRIGHT:copyright attribution
DATE:recording date:DESCRIPTION:a short description
ENGINEER\(dg:the recording masterer:ENSEMBLE\(dg:performing group
GENRE:a short music genre label:GUEST ARTIST\(dg:collaborating artist
ISRC:ISRC number for the track:LICENSE:license information
LOCATION:recording location:OPUS\(dg:number of the work
ORGANIZATION:record label:PART\(dg:track's movement title
PERFORMER:performer name, orchestra, actor, etc.:PRODUCER\(dg:person responsible for the project
PRODUCTNUMBER\(dg:UPC, EAN, or JAN code:PUBLISHER\(dg:album's publisher
RELEASE DATE\(dg:date the album was published:REMIXER\(dg:person who created the remix
SOURCE ARTIST\(dg:artist of the work being performed:SOURCE MEDIUM\(dg:CD, radio, cassette, vinyl LP, etc.
SOURCE WORK\(dg:a soundtrack's original work:SPARS\(dg:DDD, ADD, AAD, etc.
SUBTITLE\(dg:for multiple track names in a single file:TITLE:track name
TRACKNUMBER:track number:VERSION:track version
VOLUME\(dg:disc number for multi-volume work
_
.TE
.ps
.FS
\(dg These are proposed extension fields and not part of the official Vorbis comment specification.
.FE
