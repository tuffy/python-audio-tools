.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.CHAPTER "Using the Tools"
.PP
These Python Audio Tools are command-line programs which allow the user
to extract audio from CDs, convert audio from one format to another,
rename audio tracks and burn audio back to CDs.
They are designed to provide a complete toolchain of audio handling
utilities, but also to interoperate well with other tools.
.PSPIC "usage.eps" 5.5i
.PP
Since Python Audio Tools is comprised of many small utilities, this example
diagram illustrates how one would go from physical media to encoded
audio files and back again.
It looks more complicated than it is.
Let's go through the process of ripping a CD as an example.
From a command-line prompt (indicated by `%'), run:
.LP
.ft C
% cd2track
.ft
.LP
This will access your CD and extract all the audio files on it
into the default audio format, resulting in files named 
`\fCtrack01.cdda.wav\fR', `\fCtrack02.cdda.wav\fR' and so forth.
But if you wanted MP3 files, there's more work to be done.
.LP
.ft C
% track2track -t mp3 *.wav
.ft
.LP
Will convert those \fC.wav\fR files to MP3 files
(indicated by the \fC-t mp3\fR flag which tells the program
what file type we want).
Unfortunately, that gives us raw, untagged MP3s without names.
That's where the XMCD data comes in.
XMCD files, retrieved from FreeDB, contain the information we need.
.LP
.ft C
% cd2xmcd -x album.xmcd
.br
% track2track -x album.xmcd -t mp3 *.wav
.ft
.LP
Fetches the data to a file called `\fCalbum.xmcd\fR' which we
then feed to \fCtrack2track\fR so it knows what to call our
new MP3 files.
Combining \fCcd2track\fR, \fCcd2xmcd\fR and \fCtrack2track\fR
is a nice way to rip audio in batches.
For instance, since ripping and converting happen at different speeds,
you could run each process in its own window to keep your computer
as busy as possible.
.PP
However, there is an easier way.
\fCcd2track\fR doesn't have to rip CDs to \fC.wav\fR files;
it can go directly to MP3s if you ask it to.
It still requires an XMCD file to know what to name those tracks,
but our ripping process can be reduced to:
.LP
.ft C
% cd2xmcd -x album.xmcd
.br
% cd2track -x album.xmcd -t mp3
.ft
.LP
If you don't like the names in \fCalbum.xmcd\fR, feel free to edit it
either with the \fCeditxmcd\fR program or a text editor.
.PP
Lossless audio is just as easy to work with.
Creating FLAC files from a CD is a almost identical:
.LP
.ft C
% cd2xmcd -x album.xmcd
.br
% cd2track -x album.xmcd -t flac
.ft
.LP
But since FLAC files are pretty big, you might want to convert
them for portable use:
.LP
.ft C
% track2track -t mp3 *.flac
.ft
.LP
Unlike going from \fC.wav\fR to \fC.mp3\fR, these FLAC files
are already tagged with information and so an XMCD file isn't required.

.bp
.SECTION "cd2xmcd"
.PSPIC -L cd2xmcd_man.eps 5.5i
.bp
.SECTION "cd2track"
.PSPIC -L cd2track_man.eps 5.5i
.bp
.SECTION "track2track"
.PSPIC -L track2track_man.eps 5.5i
.bp
.SECTION "track2xmcd"
.PSPIC -L track2xmcd_man.eps 5.5i
.bp
.SECTION "editxmcd"
.PSPIC -L editxmcd_man.eps 5.5i
.bp
.SECTION "tracktag"
.PSPIC -L tracktag_man.eps 5.5i
.bp
.SECTION "trackrename"
.PSPIC -L trackrename_man.eps 5.5i
.bp
.SECTION "track2cd"
.PSPIC -L track2cd_man.eps 5.5i
.bp
.SECTION "trackinfo"
.PSPIC -L trackinfo_man.eps 5.5i
.SECTION "tracklength"
.PSPIC -L tracklength_man.eps 5.5i
.bp
.SECTION "trackplay"
.PSPIC -L trackplay_man.eps 5.5i
.bp
.SECTION "trackcmp"
.PSPIC -L trackcmp_man.eps 5.5i
.bp
.SECTION "trackcat"
.PSPIC -L trackcat_man.eps 5.5i
.bp
.SECTION "coverview"
.PSPIC -L coverview_man.eps 5.5i
.bp
.SECTION "coverdump"
.PSPIC -L coverdump_man.eps 5.5i
.bp
