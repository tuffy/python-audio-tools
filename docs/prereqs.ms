.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Prerequisites"
.PP
.RS
.IP \(bu
Python 2.4.4				
http://www.python.org
.IP \(bu
Construct (included)			
http://construct.wikispaces.com
.IP \(bu
libcdio					
http://www.gnu.org/software/libcdio
.IP \(bu
FLAC 1.1.0					
http://flac.sourceforge.net
.IP \(bu
LAME					
http://lame.sourceforge.net
.IP \(bu
TwoLAME					
http://www.twolame.org
.IP \(bu
mpg123					
http://www.mpg123.de/
.IP \(bu
vorbis-tools					
http://www.xiph.org
.IP \(bu
Speex						
http://www.speex.org
.IP \(bu
Musepack					
http://www.musepack.net
.IP \(bu
FAAC/FAAD2				
http://www.audiocoding.com
.IP \(bu
WavPack					
http://www.wavpack.com
.IP \(bu
CDRecord					
http://cdrecord.berlios.de/old/private/cdrecord.html
.RE
.PP
Python 2.4.4 or higher, libcdio and Construct 2.00 or higher are required.
The rest are optional but recommended in order to get the most out of
these tools.
.TS
tab(:);
| c s s s s s s |
| r | l | l | l | l | l | l |.
_
Python Audio Tools Prerequisites, by Format
_
Format:Suffix:Decoding:Encoding:Metadata:Metadata:ReplayGain
\^:\^:\^:\^:Reading:Writing:\^
=
RIFF WAVE:.wav:Python:Python:N/A:N/A:N/A
AIFF:.ape:Python:Python:N/A:N/A:N/A
Sun AU:.au:Python:Python:N/A:N/A:N/A
_
FLAC:.flac:flac:flac:Python:Python:metaflac
Ogg FLAC:.oga:flac:flac:Python:Python:N/A
WavPack:.wv:wvunpack:wavpack:Python:Python:wvgain
_
MP3:.mp3:mpg123:lame:Python:Python:N/A
MP2:.mp2:mpg123:twolame:Python:Python:N/A
Ogg Vorbis:.ogg:oggdec:oggenc:Python:vorbiscomment:vorbisgain
Ogg Speex:.spx:speexdec:speexenc:Python:Python:N/A
M4A:.m4a:faad:faac:Python:Python:N/A
Musepack:.mpc:mppdec:mppenc:Python:Python:N/A
_
.TE
.PP

