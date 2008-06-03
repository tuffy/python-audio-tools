.\"This work is licensed under the
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to
.\"Creative Commons,
.\"171 Second Street, Suite 300,
.\"San Francisco, California, 94105, USA.
.SECTION "Basics"
.PP
This section covers the basics for parsing binary files.
.so format_basics_hex.ms
.bp
.SUBSECTION "Endianness"
.PP
You will need to know about endianness anytime a single value spans
multiple bytes.
As an example, let's take the first 16 bytes of a small RIFF WAVE file:

\fC52 49 46 46 54 9b 12 00  57 41 56 45 66 6d 74 20\fR

The first four bytes are the ASCII string `RIFF' (0x52 0x49 0x46 0x46).
The next four bytes are a 32-bit unsigned integer which is a size value.
Reading from left to right, that value would be 0x549B1200.
That's almost 1.5 gigabytes.
Since this file is nowhere near that large, we're clearly not
reading those bytes correctly.
.PP
The key is that RIFF WAVE files are `little endian'.
In plain English, that means we have to read in those bytes
from right to left.
Thus, the value is actually 0x00129B54.
That's a little over 1 megabyte, which is closer to our expectations.
.PP
Remember that little endian reverses the bytes, not the hexadecimal
digits.  Simply reversing the string to 0x0021B945 is not correct.

.SUBSECTION "Character Encodings"
.PP
Many audio formats store metadata, which contains information about
the song's name, artist, album and so forth.
This information is stored as text, but it's important to know what
sort of text in order to read it and display it properly.
.PP
As an example, take the simple character `é'.
In latin-1 encoding, it is stored as a single byte 0xE9.
In UTF-8 encoding, it is stored as the bytes 0xC3A9.
In UTF-16BE encoding, it is stored as the bytes 0x00E9.
.PP
Although decoding and encoding text is a complex subject beyond
the scope of this document, you must always be aware that
track metadata may not be 7-bit ASCII text and should handle
it properly in whatever encoding is supported by the metadata
formats.
Look to your programming tools for libraries to assist in Unicode
text handling.
.bp
.so format_basics_pcm.ms
