.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Ogg Speex"
.PP
Ogg Speex is Speex audio in an Ogg container.
Speex is a lossy audio codec optimized for speech.
All of the fields within Ogg Speex are little-endian.
.PP
How Ogg containers break up data packets into segments and pages
has already been explained in the Ogg Vorbis section.
Therefore, I shall move directly to the Ogg Speex packets themselves.
.SUBSECTION "the Header packet"
.PP
The first packet within a Speex stream is the Header packet.
It contains the number of channels and sampling rate.
Like Vorbis, the number of bits per sample is generated during
decoding and the total number of samples is pulled from the
`Granule Position' field in the Ogg stream.
.begin dformat
style bitwid 0.16
style recspread 0
noname
    0-63-32 Speex String `Speex   ' (0x5370656578202020)
noname
    64-223-21 Speex Version
    224-255-11 Speex Version ID
noname
    256-287-11 Header Size
    288-319-10 Sampling Rate
    320-351-11 Mode
noname
    352-383-11 Mode Bitstream Version
    384-415-10 Number of Channels
    416-447-11 Bitrate
noname
    448-479-11 Frame Size
    480-511-10 VBR
    512-543-11 Frames Per Packet
noname
    544-575-11 Extra Headers
    576-607-10 @roman Reserved sub 1@
    608-639-11 @roman Reserved sub 2@
.end dformat
.bp
.SUBSECTION "the Comment packet"
.PP
The second packet within a Speex stream is the Comment packet.
.begin dformat
style bitwid 0.08
style charwid 0
style recspread 0.3
noname
  VS:  --16 Vendor String
       0-31-16 Total Comments
       --16 Comment @roman String sub 1@
  CS:  --16 Comment @roman String sub 2@
  EN:   --16-dashed ...
noname
  S1:  0-31-18 Vendor String Length
  S2:  32-?-18 Vendor String
       --6-invisible
  S3:  0-31-18 Comment String Length
  S4:  32-?-18 Comment String
pic line dotted from VS.sw to S1.nw
pic line dotted from VS.se to S2.ne
pic line dotted from CS.sw to S3.nw
pic line dotted from CS.se to S4.ne
.end dformat
.so format_vorbiscomment.ms
