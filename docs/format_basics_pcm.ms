.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSECTION "PCM"
.PP
Pulse-Code Modulation is a method for transforming an analog
audio signal into a digital representation.
It takes that signal, `samples' its intensity at
discrete intervals and yields a stream of signed integer
values.
By replaying those values to a speaker at the same
speed and intensity, a close approximation of the
original signal is produced.
.PSPIC -L "pcm.eps" 4i

Let's take some example bytes from a CD-quality PCM stream:

\fC1B 00 43 FF  1D 00 45 FF  1C 00 4E FF  1E 00 59 FF\fR

CD-quality is 16-bit, 2 channel, 44100Hz.
16-bit means those bytes are split into 16-bit signed, little-endian samples.
Therefore, our bytes are actually the integer samples:

\fC27 -189 29 -187 28 -178 30 -167\fR

The number of channels indicates how many speakers the signal
supports.
2 channels means the samples are sent to 2 different speakers.
PCM interleaves its samples, sending one sample to
each channel simultaneously before moving on to the next set.
In the case of 2 channels, the first sample is sent to the 
left speaker and the second is sent to the right speaker.
So, our stream of data now looks like:
.TS
tab(:);
r | l.
left speaker:right speaker
_
\fC27:-189
29:-187
28:-178
30:-167\fR
.TE
44100Hz means those pairs of samples are sent at the rate of
44100 per second.
Thus, our set of samples takes precisely 1/11025th of a second
when replayed.
.PP
A channel-independent block of samples is commonly referred to
as a `frame'.
In this example, we have a total of 4 PCM frames.
However, the term `frame' appears a lot in digital audio.
It is important not to confuse a PCM frame with a CD frame
(a block of audio 1/75th of a second long), an MP3 frame,
a FLAC frame or any other sort of frame.
