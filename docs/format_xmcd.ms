.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "XMCD"
.PP
XMCD files are text files encoded either in UTF-8, ISO-8859-1 or
US-ASCII that begin with the string `# XMCD'.
Lines are delimited by either the 0x0A character
or the 0x0D 0x0A character pair.
All lines must be less than 256 characters long,
including delimiters.
Blank lines are prohibited.
Lines that begin with the `#' character are comments.
Curiously, the comments themselves are expected by FreeDB to contain
important information such as track offsets and disc length.
Fortunately, FreeDB clients can safely ignore such information
unless submitting a new disc entry.
.PP
What we are interested in are the \fCKEY=value\fR pairs in the
rest of the file.
.TS
tab(:);
| c | c |
| r | l |.
_
key:value
=
\fCDISCID\fR:a comma-separated list of 32-bit disc IDs
_
\fCDTITLE\fR:an artist name and album name, separated by ` / '
_
\fCDYEAR\fR:a 4 digit disc release year
_
\fCDGENRE\fR:the disc's FreeDB category string
_
\fCTITLE\fHx\fR:the track title, or
\^:the track artist name and track title, separated by ` / '
\^:\fHx\fR is an integer starting from 0
_
\fCEXTD\fR:extended data about the disc
_
\fCEXTT\fHx\fR:extended data about the track
\^:\fHx\fR is an integer starting from 0
_
\fCPLAYORDER\fR:a comma-separated list of track numbers
_
.TE
.PP
Multiple identical keys should have their values
concatenated (minus the newline delimiter), which allows
a single key to have a value longer than the
256 characters line length.
.PP
.SUBSECTION "BNF"
.br
.ft C
.ps 8
<XMCD file> ::= <header> <disc information> <file information> <blank> <data>
.br
<header> ::= "# xmcd" <EOL> "#" <EOL>
.br
<disc information> ::= "# Track frame offsets:" <EOL> <track offset>
.br
<track offset> ::= "# " <offset> <EOL> | "# " <offset> <EOL> <track offset>
.br
<offset> ::= [0-9]+
.br
<file information> ::= <disc length> <blank> <revision> <processed by> <submitted via>
.br
<disc length> ::= "# Disc length: " <seconds> " seconds" <EOL>
.br
<seconds> ::= [0-9]+
.br
<revision> ::= "# Revision: " <revision number> <EOL>
.br
<revision number> ::= [0-9]+
.br
<processed by> ::= "# Processed by: " <server name> <server version> <EOL>
.br
<submitted via> ::= "# Submitted via: " <client name> <client version> <EOL>
.br
<blank> ::= "#" <EOL> | "#" <EOL> <blank>
.br
<data> ::= <key> "=" <value> <EOL> | <key> "=" <value> <EOL> <data>
.br
<key> ::= [A-Z0-9]+
.br
<value> ::= [UTF-8 value]+
.ps
.ft
