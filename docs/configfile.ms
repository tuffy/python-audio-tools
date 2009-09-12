.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "The Configuration File"
.PP
Because not all systems are alike, and hard-coding values into the
application is not pleasant for non-programmers, Python Audio Tools comes
with a small config file named \fCaudiotools.cfg\fR which contains
user-editable values.
These values include the default FreeDB server to use, the
default filename format for new tracks, the default
CD-ROM device to use for audio extraction/burning and, optionally,
alternative paths to required executables.
.PP
The format of this file is straightforward.
It consists of one or more sections.
Each section contains one or more \fCkey: value\fR pairs.
.TS
tab(:);
| c s s |
| c | c | c |
| r | r | l |.
_
\fCaudiotools.cfg\fR options
_
Section:Key:Value
=
\fC[MusicBrainz]\fR:\fCserver\fR:the default MusicBrainz server hostname
\^:\fCport\fR:the default MusicBrainz server port
_
\fC[FreeDB]\fR:\fCserver\fR:the default FreeDB server hostname
\^:\fCport\fR:the default FreeDB server port
_
\fC[System]\fR:\fCcdrom\fR:the default CD-ROM device to use for CD reading/writing
\^:\fCcdrom_read_offset\fR:the sample offset to apply when reading tracks
\^:\fCmaximum_jobs\fR:the maximum amount of processes to run simultaneously
\^:\^:when converting tracks
\^:\fCfs_encoding\fR:the filesystem's text encoding, for reading/writing filenames
\^:\fCio_encoding\fR:the terminal's text encoding, when generating screen output
_
\fC[Filenames]\fR:\fCformat\fR:the default filename template
_
\fC[Binaries]\fR:\fCflac\fR:the \fCflac\fR executable to use for encoding/decoding FLAC files
\^:\fClame\fR:the \fClame\fR executable to use for encoding/decoding MP3 files
\^:...:which executable to use other than the default
_
\fC[Thumbnail]\fR:\fCformat\fR:the image format to use for thumbnails, such as `jpeg' or `png'
\^:\fCsize\fR:the maximum size of each thumbnail in pixels
\^:\^:(e.g. a value of 100 results in a maximum size of 100\[mu]100 pixel thumbnails)
_
.TE

.SUBSECTION "Options precedence"
.PP
When Python Audio Tools needs an option, such as a FreeDB server name,
it looks in the following order:
.RS
.IP 1.
The command-line.
For example, specifying the \fB--freedb-server\fR command-line option
when executing a program overrides any values in config files.
.IP 2.
The \fC$(HOME)/.audiotools.cfg\fR config file.
This file has the same syntax as the system-wide \fC.audiotools.cfg\fR
file.
Since it need only contain the options that one wishes to override,
it may be smaller than the system-wide config file.
.IP 3.
The system-wide config file found in \fC/etc/audiotools.cfg\fR.
.RE
.PP
If no command-line option is given and no config files are found
Python Audio Tools will use some hard-coded default value, which may not
be what you want.
.bp
.SUBSECTION "The Filename Format"
.PP
The default filename format is a template string which contains
Python-style \fC%(key)s\fR wildcards which are replaced by actual values when
tracks are created or renamed.
Actual values are pulled from the file's own metadata or an external
XMCD file.
.TS
tab(:);
| c | c |
| l | l |.
_
Key:Value
=
\fC%(track_number)2.2d\fR:the track's number on the CD, from 01-99
\fC%(track_total)d\fR:the total number of tracks on the CD, from 01-99
\fC%(album_number)d\fR:the CD's album number, for multi-disc compilations
\fC%(album_total)d\fR:the total number of CDs in the set
\fC%(album_track_number)s\fR:a combination of album and track number as one field
:(e.g. an album number of 2 and track number of 13 has the value \fC213\fR
:but an empty album number and track number of 5 has the value \fC05\fR)

\fC%(track_name)s\fR:the track's name
\fC%(album_name)s\fR:the album's name
\fC%(artist_name)s\fR:the track's artist name
\fC%(performer_name)s\fR:the track's performer name
\fC%(composer_name)s\fR:the track's composer name
\fC%(conductor_name)s\fR:the track's conductor name
\fC%(media)s\fR:the track's source media
\fC%(ISRC)s\fR:the track's ISRC
\fC%(catalog)s\fR:the track's catalog number
\fC%(copyright)s\fR:the track's copyright information
\fC%(publisher)s\fR:the track's publisher
\fC%(year)s\fR:the track's publication year
\fC%(date)s\fR:the track's original recording date
\fC%(suffix)s\fR:the track's suffix, based on its file type
\^:(e.g. MP3 files will have the suffix \fCmp3\fR)
_
.TE
All other text in the format string is left as-is.
