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
CONTACT:contact information:COPYRIGHT:copyright attribution
DATE:recording date:DESCRIPTION:a short description
GENRE:a short music genre label:ISRC:ISRC number for the track
LICENSE:license information:LOCATION:recording location
ORGANIZATION:record label:PERFORMER:performer name, orchestra, actor, etc.
TITLE:track name:TRACKNUMBER:the track number
VERSION:track version
_
.TE
.ps
