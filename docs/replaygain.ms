.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.CHAPTER "ReplayGain"
.PP
The ReplayGain standard is designed to address the problem of
highly variable music loudness.
For example, let's assume we have two audio tracks, A and B, and that
track B is much louder than A.
If played in sequence, the listener will have to scramble for the volume
control once B starts in order to have a comfortable experience.
ReplayGain solves this problem by calculating the overall loudness of a
track as a delta (some positive or negative number of decibels, in
relation to a reference loudness value).
This delta is then applied during playback, which has the same effect
as turning the volume up or down so that the user doesn't have to.
.PP
ReplayGain requires four floating-point values which are typically
stored as metadata in each audio track:
`track gain', a positive or negative number of decibels representing
the loudness delta of this particular track,
`track peak', the highest sample value of this particular track 
from a range of 0.0 to 1.0,
`album gain', a positive or negative number of decibels representing
the loudness delta of the track's entire album
and `album peak', the highest sample value of the track's entire album 
from a range of 0.0 to 1.0.
.SECTION "Applying ReplayGain"
.PP
The user will be expected to choose whether to apply `album gain'
or `track gain' during playback.
When listening to audio on an album-by-album basis, album gain
keeps quiet tracks quiet and loud tracks loud within the context of
that album.
When listening to audio on a track-by-track basis, perhaps as 
a randomly shuffled set, track gain keeps them all to roughly the same
loudness.
So from an implementation perspective, a program only needs to apply
the given gain and peak value to the stream being played back.
Applying the gain value to each input PCM sample is quite simple:
.EQ
"Output" sub i = {"Input" sub i}~*~{10 sup {gain / 20}} 
.EN
For example, if the gain is -2.19, each sample should be multiplied by
@10 sup {-2.19 / 20}@ or about @0.777@.
.PP
If the gain is negative, the PCM stream gets quieter than it was
originally.
If the gain is positive, the PCM stream gets louder.
However, increasing the value of each sample may cause a problem
if doing so sends any samples beyond the maximum value the stream
can hold.
For example, if the gain indicates we should be multiplying each sample
by 1.28 and we encounter a 16-bit input sample with a value of 32000,
the resulting output sample of 34560 is outside of the stream's 
16-bit signed range (-32678 to 32767).
That will result in `clipping' the audio peaks, which doesn't sound good.
.PP
Preventing this is what ReplayGain's peak value is for;
it's the highest PCM value in the stream and no multiplier should push
that value beyond 1.0.
Thus, if the peak value of a stream is 0.9765625, no ReplayGain value
should generate a multiplier higher than 1.024 (@0.9765625 * 1.024 = 1.0@).
.bp
.SECTION "Calculating ReplayGain"
.PP
As explained earlier, ReplayGain requires a peak and gain value
which are split into `track' and `album' varieties for a total of four.
The `track' values require the PCM data for the particular track
we're generating data for.
The `album' values require the PCM data for the entire album,
concatenated together into a single stream.
.PP
Determining the peak value is very straightforward.
We simply convert each sample's value to the range of 0.0 to 1.0
and find the highest value which occurs in the stream.
For signed samples, the conversion process is also simple:
.EQ
"Output" sub i = {|~{"Input" sub i}~|} over {2 sup {"bits per sample"~-~1}}
.EN
.PP
Determining the gain value is a more complicated process.
It involves running the input stream through an equal loudness filter,
breaking that stream into 50 millisecond long blocks, and then
determining a final value based on the value of those blocks.
.SUBSECTION "the Equal Loudness Filter"
.PP
Because people don't perceive all frequencies of sounds as having
equal loudness, ReplayGain runs audio through a filter which
emphasizes ones we hear as loud and deemphasizes ones we hear as quiet.
This equal loudness filtering is actually comprised of two separate
filters: Yule and Butter (these are Infinite Impulse Response filters
named after their creators).
Each works on a similar principle.

