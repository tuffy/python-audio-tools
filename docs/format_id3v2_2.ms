.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSUBSECTION "ID3v2.2"

.SUBSUBSUBSECTION "the ID3v2.2 Header"
.PP
.begin dformat
style bitwid 0.15
style recspread 0
noname
    0-23-24 ID (`ID3' 0x494433)
    24-39-16 Version (0x0200)
noname
    40-40-5 Unsync
    41-41-5 Compression
    42-47-30 NULL (0x00)
noname
    48-48-3 0x00
    49-55-7 Size
    56-56-3 0x00
    57-63-7 Size
    64-64-3 0x00
    65-71-7 Size
    72-72-3 0x00
    73-79-7 Size
.end dformat
The single Size field is split by NULL (0x00) bytes in order to make
it `sync-safe'.  That is, no possible size value will result in a false
MP3 frame sync (11 bits set in a row).

.SUBSUBSUBSECTION "an ID3v2.2 Frame"
.PP
.begin dformat
style bitwid 0.15
style recspread 0
noname
  0-23-30 Frame ID
noname
  24-47-30 Size
noname
  48--30-dashed Frame Data
.end dformat
Frame ID's that begin with the letter `T' (0x54) are text frames.
These have an additional text encoding byte before the actual
text data.
All text strings are terminated by a null character
(0x00 or 0x0000, depending on the encoding).
.begin dformat
style bitwid 0.15
style recspread 0
noname
  0-23-30 Frame ID `TXX' (0x54XXXX)
noname
  24-47-30 Size
noname
  48-55-5 Encoding
  56--25-dashed Text
.end dformat
.TS
tab(:);
r | l.
Encoding Byte:Text Encoding
_
\fC0x00\fR:ISO-8859-1
\fC0x01\fR:UCS-16
.TE


.bp

.SUBSUBSUBSECTION "ID3v2.2 Frame IDs"
.PP
.ps 8
.TS
tab(:);
c | l || c | l.
ID:Description:ID:Description
=
\fCBUF\fR:Recommended buffer size:\fCCNT\fR:Play counter
\fCCOM\fR:Comments:\fCCRA\fR:Audio encryption
\fCCRM\fR:Encrypted meta frame:\fCETC\fR:Event timing codes
\fCEQU\fR:Equalization:\fCGEO\fR:General encapsulated object
\fCIPL\fR:Involved people list:\fCLNK\fR:Linked information
\fCMCI\fR:Music CD Identifier:\fCMLL\fR:MPEG location lookup table
\fCPIC\fR:Attached picture:\fCPOP\fR:Popularimeter
\fCREV\fR:Reverb:\fCRVA\fR:Relative volume adjustment
\fCSLT\fR:Synchronized lyric/text:\fCSTC\fR:Synced tempo codes
\fCTAL\fR:Album/Movie/Show title:\fCTBP\fR:BPM (Beats Per Minute)
\fCTCM\fR:Composer:\fCTCO\fR:Content type
\fCTCR\fR:Copyright message:\fCTDA\fR:Date
\fCTDY\fR:Playlist delay:\fCTEN\fR:Encoded by
\fCTFT\fR:File type:\fCTIM\fR:Time
\fCTKE\fR:Initial key:\fCTLA\fR:Language(s)
\fCTLE\fR:Length:\fCTMT\fR:Media type
\fCTOA\fR:Original artist(s)/performer(s):\fCTOF\fR:Original filename
\fCTOL\fR:Original Lyricist(s)/text writer(s):\fCTOR\fR:Original release year
\fCTOT\fR:Original album/Movie/Show title:\fCTP1\fR:Lead artist(s)/Lead performer(s)/Soloist(s)/Performing group
\fCTP2\fR:Band/Orchestra/Accompaniment:\fCTP3\fR:Conductor/Performer refinement
\fCTP4\fR:Interpreted, remixed, or otherwise modified by:\fCTPA\fR:Part of a set
\fCTPB\fR:Publisher:\fCTRC\fR:ISRC (International Standard Recording Code)
\fCTRD\fR:Recording dates:\fCTRK\fR:Track number/Position in set
\fCTSI\fR:Size:\fCTSS\fR:Software/hardware and settings used for encoding
\fCTT1\fR:Content group description:\fCTT2\fR:Title/Songname/Content description
\fCTT3\fR:Subtitle/Description refinement:\fCTXT\fR:Lyricist/text writer
\fCTXX\fR:User defined text information frame:\fCTYE\fR:Year
\fCUFI\fR:Unique file identifier:\fCULT\fR:Unsychronized lyric/text transcription
\fCWAF\fR:Official audio file webpage:\fCWAR\fR:Official artist/performer webpage
\fCWAS\fR:Official audio source webpage:\fCWCM\fR:Commercial information
\fCWCP\fR:Copyright/Legal information:\fCWPB\fR:Publishers official webpage
\fCWXX\fR:User defined URL link frame
.TE
.ps 10
.bp
.SUBSUBSUBSECTION "the PIC Frame"
.PP
`PIC' frames are attached pictures.
This allows an ID3v2.2 tag to contain a JPEG or PNG image,
typically of album artwork which can be displayed to the user
when the track is played.
.begin dformat
style bitwid 0.15
style recspread 0
noname
  0-23-30 Frame ID `PIC' (0x504943)
noname
  24-47-30 Size
noname
  48-55-10 Text Encoding
  56-79-20 Image Format
noname
  80-87-10 Picture Type
  88-?-20-dashed Description
noname
  --30-dashed Picture Data
.end dformat
Text Encoding is the encoding of the Description field.
Its value is either ISO-8859-1 or UCS-16 - the same as in
text frames.
Image Format is a 3 byte string indicating the format of the image,
typically `JPG' for JPEG images or 'PNG' for PNG images.
Description is a NULL-terminated C-style string which contains
a text description of the image.
.TS
tab(:);
| c s s s | 
| r | l || r | l |.
_
Picture Types
_
value:type:value:type
=
0:Other:1:32x32 pixels `file icon' (PNG only)
2:Other file icon:3:Cover (front)
4:Cover (back):5:Leaflet page
6:Media (e.g. label side of CD):7:Lead artist / Lead performer / Soloist
8:Artist / Performer:9:Conductor
10:Band / Orchestra:11:Composer
12:Lyricist / Text writer:13:Recording location
14:During recording:15:During performance
16:Movie / Video screen capture:17:A bright coloured fish
18:Illustration:19:Band / Artist logotype
20:Publisher / Studio logotype
_
.TE
