.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSUBSECTION "ID3v2.4"

.SUBSUBSUBSECTION "the ID3v2.4 Header"
.PP
.begin dformat
style bitwid 0.15
style recspread 0
noname
    0-23-24 ID (`ID3' 0x494433)
    24-39-16 Version (0x0400)
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

.SUBSUBSUBSECTION "an ID3v2.4 Frame"
.PP
.begin dformat
style bitwid 0.15
style recspread 0
noname
    0-31-40 Frame ID
noname
    32-32-3 0x00
    33-39-7 Size
    40-40-3 0x00
    41-47-7 Size
    48-48-3 0x00
    49-55-7 Size
    56-56-3 0x00
    57-63-7 Size
noname
    64-64-5 0x00
    65-65-5 Tag Alter
    66-66-5 File Alter
    67-67-5 Read Only
    68-71-20 0x00
noname
    72-72-5 0x00
    73-73-5 Grouping
    74-75-10 0x00
    76-76-5 Compression
    77-77-5 Encryption
    78-78-5 Unsync
    79-79-5 Data Length
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
    32-32-3 0x00
    33-39-7 Size
    40-40-3 0x00
    41-47-7 Size
    48-48-3 0x00
    49-55-7 Size
    56-56-3 0x00
    57-63-7 Size
noname
    64-64-5 0x00
    65-65-5 Tag Alter
    66-66-5 File Alter
    67-67-5 Read Only
    68-71-20 0x00
noname
    72-72-5 0x00
    73-73-5 Grouping
    74-75-10 0x00
    76-76-5 Compression
    77-77-5 Encryption
    78-78-5 Unsync
    79-79-5 Data Length
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
\fC0x01\fR:UTF-16
\fC0x02\fR:UTF-16BE
\fC0x03\fR:UTF-8
.TE

.bp

.SUBSUBSUBSECTION "ID3v2.4 Frame IDs"
.PP
.ps 8
.TS
tab(:);
c | l || c | l.
ID:Description:ID:Description
=
\fCAENC\fR:Audio encryption:\fCAPIC\fR:Attached picture
\fCASPI\fR:Audio seek point index:\fCCOMM\fR:Comments
\fCCOMR\fR:Commercial frame:\fCENCR\fR:Encryption method registration
\fCEQU2\fR:Equalisation (2):\fCETCO\fR:Event timing codes
\fCGEOB\fR:General encapsulated object:\fCGRID\fR:Group identification registration
\fCLINK\fR:Linked information:\fCMCDI\fR:Music CD identifier
\fCMLLT\fR:MPEG location lookup table:\fCOWNE\fR:Ownership frame
\fCPRIV\fR:Private frame:\fCPCNT\fR:Play counter
\fCPOPM\fR:Popularimeter:\fCPOSS\fR:Position synchronisation frame
\fCRBUF\fR:Recommended buffer size:\fCRVA2\fR:Relative volume adjustment (2)
\fCRVRB\fR:Reverb:\fCSEEK\fR:Seek frame
\fCSIGN\fR:Signature frame:\fCSYLT\fR:Synchronised lyric/text
\fCSYTC\fR:Synchronised tempo codes:\fCTALB\fR:Album/Movie/Show title
\fCTBPM\fR:BPM (beats per minute):\fCTCOM\fR:Composer
\fCTCON\fR:Content type:\fCTCOP\fR:Copyright message
\fCTDEN\fR:Encoding time:\fCTDLY\fR:Playlist delay
\fCTDOR\fR:Original release time:\fCTDRC\fR:Recording time
\fCTDRL\fR:Release time:\fCTDTG\fR:Tagging time
\fCTENC\fR:Encoded by:\fCTEXT\fR:Lyricist/Text writer
\fCTFLT\fR:File type:\fCTIPL\fR:Involved people list
\fCTIT1\fR:Content group description:\fCTIT2\fR:Title/songname/content description
\fCTIT3\fR:Subtitle/Description refinement:\fCTKEY\fR:Initial key
\fCTLAN\fR:Language(s):\fCTLEN\fR:Length
\fCTMCL\fR:Musician credits list:\fCTMED\fR:Media type
\fCTMOO\fR:Mood:\fCTOAL\fR:Original album/movie/show title
\fCTOFN\fR:Original filename:\fCTOLY\fR:Original lyricist(s)/text writer(s)
\fCTOPE\fR:Original artist(s)/performer(s):\fCTOWN\fR:File owner/licensee
\fCTPE1\fR:Lead performer(s)/Soloist(s):\fCTPE2\fR:Band/orchestra/accompaniment
\fCTPE3\fR:Conductor/performer refinement:\fCTPE4\fR:Interpreted, remixed, or otherwise modified by
\fCTPOS\fR:Part of a set:\fCTPRO\fR:Produced notice
\fCTPUB\fR:Publisher:\fCTRCK\fR:Track number/Position in set
\fCTRSN\fR:Internet radio station name:\fCTRSO\fR:Internet radio station owner
\fCTSOA\fR:Album sort order:\fCTSOP\fR:Performer sort order
\fCTSOT\fR:Title sort order:\fCTSRC\fR:ISRC (international standard recording code)
\fCTSSE\fR:Software/Hardware and settings used for encoding:\fCTSST\fR:Set subtitle
\fCTXXX\fR:User defined text information frame:\fCUFID\fR:Unique file identifier
\fCUSER\fR:Terms of use:\fCUSLT\fR:Unsynchronised lyric/text transcription
\fCWCOM\fR:Commercial information:\fCWCOP\fR:Copyright/Legal information
\fCWOAF\fR:Official audio file webpage:\fCWOAR\fR:Official artist/performer webpage
\fCWOAS\fR:Official audio source webpage:\fCWORS\fR:Official Internet radio station homepage
\fCWPAY\fR:Payment:\fCWPUB\fR:Publishers official webpage
\fCWXXX\fR:User defined URL link frame
.TE
.ps 10
