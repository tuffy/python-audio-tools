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
Python 2.5.0		
http://www.python.org
.IP \(bu
Construct (included)	
http://construct.wikispaces.com
.IP \(bu
libcdio			
http://www.gnu.org/software/libcdio
.IP \(bu
FLAC 			
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
Nero AAC Codec		
http://www.nero.com/enu/downloads-nerodigital-nero-aac-codec.php
.IP \(bu
WavPack			
http://www.wavpack.com
.IP \(bu
CDRecord			
http://cdrecord.berlios.de/old/private/cdrecord.html
.IP \(bu
cdrdao			
http://cdrdao.sourceforge.net/
.RE
.PP
Python 2.5.0 or higher, libcdio and Construct 2.00 or higher are required.
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
RIFF WAVE:\fC.wav\fR:Python:Python:N/A:N/A:N/A
AIFF:\fC.aiff\fR:Python:Python:N/A:N/A:N/A
Sun AU:\fC.au\fR:Python:Python:N/A:N/A:N/A
_
FLAC:\fC.flac\fR:flac:flac:Python:Python:metaflac
Ogg FLAC:\fC.oga\fR:flac:flac:Python:Python:N/A
WavPack:\fC.wv\fR:wvunpack:wavpack:Python:Python:wvgain
_
MP3:\fC.mp3\fR:lame / mpg123:lame:Python:Python:N/A
MP2:\fC.mp2\fR:lame / mpg123:twolame:Python:Python:N/A
Ogg Vorbis:\fC.ogg\fR:oggdec:oggenc:Python:Python:vorbisgain
Ogg Speex:\fC.spx\fR:speexdec:speexenc:Python:Python:N/A
M4A:\fC.m4a\fR:faad / neroAacDec:faac / neroAacEnc:Python:Python:N/A
Musepack:\fC.mpc\fR:mpcdec:mpcenc:Python:Python:N/A
_
.TE
.PP

