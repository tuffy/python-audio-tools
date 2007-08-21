.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.CHAPTER "FreeDB"
.PP
Because compact discs do not usually contain metadata about
track names, album names and so forth, that information
must be retrieved from an external source.
FreeDB is a service which allows users to submit CD
metadata and to retrieve the meta-data submitted by others.
Both actions require a category and a 32-bit disc ID number,
which combine to form a unique identifier for a particular CD.
.PP
The 32-bit disc ID is calculated from the total number of tracks,
the track offsets (in CD sectors) and the total length of the CD
(in seconds).
.PP
In the case of CD submission, the genre is decided by the submitter.
In the case of CD retrieval, the user must choose from a list
of possible choices when there is a collision between 32-bit disc ID
numbers.
.PP
The actual metadata is stored as XMCD files.

.2C

.SECTION "Native Protocol"
.PP
FreeDB's native protocol runs as a service on TCP port 8880.
After connecting, the client and server exchange a handshake using
the `hello' command.
The server will not do anything without this handshake.
.PP
Next the client changes to protocol level 6 with the `proto' command.
This is necessary because only the highest protocol supports
UTF-8 text encoding.
Without this, any characters not in the latin-1 set will not be
sent properly.
.PP
Once that is accomplished, the client should calculate the 32-bit
disc ID from the track information.
.PP
One then sends the 32-bit disc ID and additional disc information
to the server with the `query' command to retrieve a list of
matching disc IDs, genres and titles.
If there are multiple matches, the user must be prompted to
choose one of the matches.
.PP
When our match is known, the client uses the `read' command
to retrieve the actual XMCD data.
.PP
Finally, the `close' command is used to sever the connection
and complete the transaction.

.PSPIC -L "freedb-sequence.eps" 2i
.1C
.bp

.SUBSECTION "The Disc ID"
.PP
FreeDB uses a big-endian 32-bit disc ID to differentiate 
one disc from another.
.begin dformat
style bitwid 0.10
style charwid 0
style recspread 0
noname
  0-7-18 Offset Seconds Digit Sum
  8-23-18 Total Length in Seconds
  24-31-12 Track Count
.end dformat
.PP
`Track Count' is self-explanatory.
`Total Length' is the total length of all the tracks, not
counting the initial 2 second lead-in.
`Offset Seconds Digit Sum' is the sum of the digits of all
the disc's track offsets, in seconds, and truncated to 8 bits.
Remember to count the initial 2 second/150 frame lead-in when calculating
offsets.
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
In this example, `Track Count' is 4.
`Total Length' is @{{16340 + 15294 + 16340 + 15045} over 75} = 840@
.br
There are 75 frames per second, but one must remember to count
fractions of seconds when calculating the total disc length.
The `Offset Seconds Digit Sum' is calculated by looking at the 
`Offset in Seconds' column.
Those values are 2, 219, 423 and 641.
One must take all of those digits and add them, which works out to
@2 + 2 + 1 + 9 + 4 + 2 + 3 + 6 + 4 + 1 = 34@
.PP
This means our three values are 34, 840 and 4.
In hexadecimal, they are 0x22, 0x0348 and 0x04.
Combining them into a single value yields 0x22034804.
Thus, our FreeDB disc ID is `22034804'.
.bp

.KS
.SUBSECTION "Initial Greeting"

.BEGIN_FROMSERVER
.FROMSERVER "<code> <host> CDDBP server <version> ready at <datetime>"
.TS
tab(~);
r | r l.
\fC<code>\fR~\fC200\fR~OK, reading/writing allowed
\^~\fC201\fR~OK, read-only
\^~\fC432\fR~No connections allowed: permission denied
\^~\fC433\fR~No connections allowed: X users allowed, Y currently active
\^~\fC434\fR~No connections allowed: system load too high
\fC<hostname>\fR~the server's host name
\fC<version>\fR~the server's version
\fC<datetime>\fR~the current date and time
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "Client-Server Handshake"

.BEGIN_TOSERVER
.TOSERVER "cddb hello <username> <hostname> <clientname> <version>"
.TS
tab(~);
r | r l.
\fC<username>\fR~login name of user
\fC<hostname>\fR~host name of client
\fC<clientname>\fR~name of client program
\fC<version>\fR~version of client program
.TE
.END_TOSERVER

.BEGIN_FROMSERVER
.FROMSERVER "<code> hello and welcome <username>\@<hostname> running <clientname> <version>"
.TS
tab(~);
r | r l.
\fC<code>\fR~\fC200\fR~handshake successful
\^~\fC402\fR~already shook hands
\^~\fC431\fR~handshake unsuccessful, closing connection
\fC<username>\fR~login name of user
\fC<hostname>\fR~host name of client
\fC<clientname>\fR~name of client program
\fC<version>\fR~version of client program
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "Set Protocol Level"

.BEGIN_TOSERVER
.TOSERVER "proto [level]"
.TS
tab(~);
r | r l.
\fC<level>~\fRprotocol level as integer (optional)
.TE
.END_TOSERVER

.BEGIN_FROMSERVER
.FROMSERVER "<code> CDDB protocol level: <current>, supported <supported>"
.SERVER_OR
.br
.FROMSERVER "<code> OK, protocol version now:  <current>"
.TS
tab(~);
r | r l.
\fC<code>~\fC200~\fRdisplaying current protocol level
\^~\fC201~\fRprotocol level set
\^~\fC501~\fRillegal protocol level
\^~\fC502~\fRprotocol level already at \fC<current>\fR
\fC<current>~\fRthe current protocol level of this connection
\fC<supported>~\fRthe maximum supported protocol level
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "Calculate Disc ID"

.BEGIN_TOSERVER
.TOSERVER "discid <track count> <offset 1> ... <offset n> <total seconds>"
.TS
tab(~);
r | r l.
\fC<track count>~\fRnumber of tracks in CD
\fC<offset>~\fRframe offset of each track
\fC<total seconds>~\fRtotal length of CD in seconds
.TE
.END_TOSERVER


.BEGIN_FROMSERVER
.FROMSERVER "<code> Disc ID is <disc id>"
.TS
tab(~);
r | r l.
\fC<code>~\fC200~\fRdisc ID calculated
\^~\fC500~\fRsyntax error
\fC<disc id>~\fR32-bit disc ID
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "Query Database"

.BEGIN_TOSERVER
.TOSERVER "cddb query <disc id> <track count> <offset 1> ... <offset n> <total seconds>"
.TS
tab(~);
r | r l.
\fC<disc id>~\fR32-bit disc ID
\fC<track count>~\fRnumber of tracks in CD
\fC<offset>~\fRframe offset of each track
\fC<total seconds>~\fRtotal length of CD in seconds
.TE
.END_TOSERVER


.BEGIN_FROMSERVER
.FROMSERVER "<code> <category> <disc id> <disc title>"
.SERVER_OR
.br
.FROMSERVER "<code> close matches found"
.FROMSERVER "<category> <disc id> <disc title>"
.FROMSERVER "<category> <disc id> <disc title>"
.FROMSERVER "<...>"
.FROMSERVER "."
.SERVER_OR
.br
.FROMSERVER "<code> exact matches found"
.FROMSERVER "<category> <disc id> <disc title>"
.FROMSERVER "<category> <disc id> <disc title>"
.FROMSERVER "<...>"
.FROMSERVER "."
.TS
tab(~);
r | r l.
\fC<code>~\fC200~\fRFound exact match
\^~\fC211~\fRFound inexact matches, list follows
\^~\fC202~\fRNo match found
\^~\fC210~\fRFound exact matches, list follows
\^~\fC403~\fRDatabase entry corrupt
\^~\fC409~\fRNo handshake
\fC<category>~\fRcategory string
\fC<disc id>~\fR32-bit disc ID
\fC<disc title>~\fRdisc title string
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "Read XMCD Data"

.BEGIN_TOSERVER
.TOSERVER "cddb read <category> <disc id>"

.TS
tab(~);
r | r l.
\fC<category>~\fRcategory string
\fC<disc id>~\fR32-bit disc ID
.TE
.END_TOSERVER


.BEGIN_FROMSERVER
.FROMSERVER "<code> <category> <disc id>"
.FROMSERVER "# XMCD file data"
.FROMSERVER "# ..."
.FROMSERVER "."
.TS
tab(~);
r | r l.
\fC<code>~\fC210~\fRXMCD data follows
\^~\fC401~\fRXMCD data not found
\^~\fC402~\fRserver error
\^~\fC403~\fRdatabase entry corrupt
\^~\fC409~\fRno handshake
\fC<category>~\fRcategory string
\fC<disc id>~\fR32-bit disc ID
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "Close Connection"

.BEGIN_TOSERVER
.TOSERVER "quit"
.END_TOSERVER

.BEGIN_FROMSERVER
.FROMSERVER "<code> <hostname> <message>"
.TS
tab(~);
r | r l.
\fC<code> <message>~\fC230~Closing connection.  Goodbye.
\^~530~error, closing connection.
\fC<hostname>~\fRserver's host name
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "List Genres"

.BEGIN_TOSERVER
.TOSERVER "cddb lscat"
.END_TOSERVER

.BEGIN_FROMSERVER
.FROMSERVER "<code> Okay category list follows (until terminating marker)"
.FROMSERVER "<category>"
.FROMSERVER "<category>"
.FROMSERVER "<...>"
.FROMSERVER "."
.TS
tab(~);
r | r l.
\fC<code>~\fC210~\fRokay
\fC<category>~\fRcategory string
.TE
.END_FROMSERVER
.KE

.KS
.SUBSECTION "List Mirrors"

.BEGIN_TOSERVER
.TOSERVER "sites"
.END_TOSERVER

.BEGIN_FROMSERVER
.FROMSERVER "<code> OK, site information follows (until terminating `.')"
.FROMSERVER "<site> <protocol> <port> <address> <latitude> <longitude> <description>"
.FROMSERVER "<...>"
.FROMSERVER "."
.TS
tab(~);
r | r l.
\fC<code>~\fC210~\fRsite information follows
\^~\fC401~\fRno site information available
\fC<site>~\fRinternet address of site
\fC<protocol>~\fRthe protocol level supported by the site
\fC<port>~\fRinternet port of site
\fC<address>~\fRadditional addressing required, or `-' if none necessary
\fC<latitude>~\fRlatitude of site
\fC<longitude>~\fRlongitude of site
\fC<description>~\fRshort text description of site
.TE
.END_FROMSERVER
.KE

.bp

.SECTION "Web Protocol"
.PP
FreeDB's web protocol runs as a service on HTTP port 80.
A web client POSTs data to a location, typically: \fC~cddb/cddb.cgi\fR
and retrieves results.
This method is similar to the native protocol and the returned
data is identical.
However, since HTTP POST requests are stateless,
there is no separate `hello', `proto' and `quit' commands;
these are issued along with the primary server command or are
implied.
.TS
tab(:);
| c s | 
| c | c |
| r | l |.
_
POST Arguments
_
key:value
=
\fChello\fR:\fC<username> <hostname> <clientname> <version>\fR
\fCproto\fR:\fC<protocol level>\fR
\fCcmd\fR:\fC<server command>\fR
_
.TE
For example, to execute the `read' command on disc ID `AABBCCDD'
in the `soundtrack' category, one can post the following string:
.br
.ft C
.ps 8
cmd=read+soundtrack+aabbccdd&hello=username+hostname+audiotools+1.0&proto=6
.ps
.ft

.bp

.so format_xmcd.ms
