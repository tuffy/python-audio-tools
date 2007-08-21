.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSUBSECTION "ID3v2.3"

.SUBSUBSUBSECTION "the ID3v2.3 Header"
.PP
.begin dformat
style bitwid 0.15
style recspread 0
noname
    0-23-24 ID (`ID3' 0x494433)
    24-39-16 Version (0x0300)
noname
    40-40-5 Unsync
    41-41-5 Extended
    42-42-5 Experimental
    43-43-5 Footer
    44-47-20 NULL (0x00)
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

.SUBSUBSUBSECTION "an ID3v2.3 Frame"
.PP
.begin dformat
style bitwid 0.15
style recspread 0
noname
    0-31-40 Frame ID
noname
    32-63-40 Size
noname
    64-64-5 Tag Alter
    65-65-5 File Alter
    66-66-5 Read Only 
    67-71-25 0x00
noname
    72-72-5 Compression
    73-73-5 Encryption
    74-74-5 Grouping
    75-79-25 0x00
noname
    80--40-dashed Frame Data
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
    0-31-40 Frame ID `TXXX' (0x54XXXXXX)
noname
    32-63-40 Size
noname
    64-64-5 Tag Alter
    65-65-5 File Alter
    66-66-5 Read Only 
    67-71-25 0x00
noname
    72-72-5 Compression
    73-73-5 Encryption
    74-74-5 Grouping
    75-79-25 0x00
noname
    80-87-10 Encoding
    88--30-dashed Text
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

.SUBSUBSUBSECTION "ID3v2.3 Frame IDs"
.PP
.ps 8
.TS
tab(:);
c | l || c | l.
ID:Description:ID:Description
=
\fCAENC\fR:Audio encryption:\fCAPIC\fR:Attached picture
\fCCOMM\fR:Comments:\fCCOMR\fR:Commercial frame
\fCENCR\fR:Encryption method registration:\fCEQUA\fR:Equalization
\fCETCO\fR:Event timing codes:\fCGEOB\fR:General encapsulated object
\fCGRID\fR:Group identification registration:\fCIPLS\fR:Involved people list
\fCLINK\fR:Linked information:\fCMCDI\fR:Music CD identifier
\fCMLLT\fR:MPEG location lookup table:\fCOWNE\fR:Ownership frame
\fCPRIV\fR:Private frame:\fCPCNT\fR:Play counter
\fCPOPM\fR:Popularimeter:\fCPOSS\fR:Position synchronisation frame
\fCRBUF\fR:Recommended buffer size:\fCRVAD\fR:Relative volume adjustment
\fCRVRB\fR:Reverb:\fCSYLT\fR:Synchronized lyric/text
\fCSYTC\fR:Synchronized tempo codes:\fCTALB\fR:Album/Movie/Show title
\fCTBPM\fR:BPM (beats per minute):\fCTCOM\fR:Composer
\fCTCON\fR:Content type:\fCTCOP\fR:Copyright message
\fCTDAT\fR:Date:\fCTDLY\fR:Playlist delay
\fCTENC\fR:Encoded by:\fCTEXT\fR:Lyricist/Text writer
\fCTFLT\fR:File type:\fCTIME\fR:Time
\fCTIT1\fR:Content group description:\fCTIT2\fR:Title/songname/content description
\fCTIT3\fR:Subtitle/Description refinement:\fCTKEY\fR:Initial key
\fCTLAN\fR:Language(s):\fCTLEN\fR:Length
\fCTMED\fR:Media type:\fCTOAL\fR:Original album/movie/show title
\fCTOFN\fR:Original filename:\fCTOLY\fR:Original lyricist(s)/text writer(s)
\fCTOPE\fR:Original artist(s)/performer(s):\fCTORY\fR:Original release year
\fCTOWN\fR:File owner/licensee:\fCTPE1\fR:Lead performer(s)/Soloist(s)
\fCTPE2\fR:Band/orchestra/accompaniment:\fCTPE3\fR:Conductor/performer refinement
\fCTPE4\fR:Interpreted, remixed, or otherwise modified by:\fCTPOS\fR:Part of a set
\fCTPUB\fR:Publisher:\fCTRCK\fR:Track number/Position in set
\fCTRDA\fR:Recording dates:\fCTRSN\fR:Internet radio station name
\fCTRSO\fR:Internet radio station owner:\fCTSIZ\fR:Size
\fCTSRC\fR:ISRC (international standard recording code):\fCTSSE\fR:Software/Hardware and settings used for encoding
\fCTYER\fR:Year:\fCTXXX\fR:User defined text information frame
\fCUFID\fR:Unique file identifier:\fCUSER\fR:Terms of use
\fCUSLT\fR:Unsychronized lyric/text transcription:\fCWCOM\fR:Commercial information
\fCWCOP\fR:Copyright/Legal information:\fCWOAF\fR:Official audio file webpage
\fCWOAR\fR:Official artist/performer webpage:\fCWOAS\fR:Official audio source webpage
\fCWORS\fR:Official internet radio station homepage:\fCWPAY\fR:Payment
\fCWPUB\fR:Publishers official webpage:\fCWXXX\fR:User defined URL link frame
.TE
.ps 10
