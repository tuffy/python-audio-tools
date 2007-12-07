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
.PP
The basic premise is that each output sample is derived from multiplying
`order' number of previous input samples by certain values (which
depend on the filter) \fIand\fR `order' number of previous output
samples by a different set of values (also depending on the filter)
and then combining the results.
.bp
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r | r | r |.
_
AYule
_
Sample,Sample Rate
Multiplier,48000Hz,44100Hz,32000Hz
=
@Input sub i@,@*@,1.0,1.0,1.0
@Input sub {i~-~1}@,@*@,-3.8466461711806699,-3.4784594855007098,-2.3789883497308399
@Input sub {i~-~2}@,@*@,7.81501653005538,6.3631777756614802,2.84868151156327
@Input sub {i~-~3}@,@*@,-11.341703551320419,-8.5475152747187408,-2.6457717022982501
@Input sub {i~-~4}@,@*@,13.055042193275449,9.4769360780128,2.2369765745171302
@Input sub {i~-~5}@,@*@,-12.28759895145294,-8.8149868137015499,-1.67148153367602
@Input sub {i~-~6}@,@*@,9.4829380631978992,6.8540154093699801,1.0059595480854699
@Input sub {i~-~7}@,@*@,-5.8725786177599897,-4.3947099607955904,-0.45953458054982999
@Input sub {i~-~8}@,@*@,2.7546586187461299,2.1961168489077401,0.16378164858596
@Input sub {i~-~9}@,@*@,-0.86984376593551005,-0.75104302451432003,-0.050320777171309998
@Input sub {i~-~10}@,@*@,0.13919314567432001,0.13149317958807999,0.023478974070199998
_
.TE
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r  | r | r |.
_
BYule
_
Sample,Sample Rate
Multiplier,48000Hz,44100Hz,32000Hz
=
@Output sub i@,@*@,0.038575994352000001,0.054186564064300002,0.15457299681924
@Output sub {i~-~1}@,@*@,-0.021603671841850001,-0.029110078089480001,-0.093310490563149995
@Output sub {i~-~2}@,@*@,-0.0012339531685100001,-0.0084870937985100006,-0.062478801536530001
@Output sub {i~-~3}@,@*@,-9.2916779589999993e-05,-0.0085116564546900003,0.021635418887979999
@Output sub {i~-~4}@,@*@,-0.016552603416190002,-0.0083499090493599996,-0.05588393329856
@Output sub {i~-~5}@,@*@,0.02161526843274,0.022452932533390001,0.047814766749210001
@Output sub {i~-~6}@,@*@,-0.02074045215285,-0.025963385129149998,0.0022231259774300001
@Output sub {i~-~7}@,@*@,0.0059429806512499997,0.016248649629749999,0.031740925400489998
@Output sub {i~-~8}@,@*@,0.0030642802319099998,-0.0024087905158400001,-0.013905894218979999
@Output sub {i~-~9}@,@*@,0.00012025322027,0.0067461368224699999,0.00651420667831
@Output sub {i~-~10}@,@*@,.0028846368391600001,-0.00187763777362,-0.0088136273383899993
_
.TE
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r | r | r |.
_
AButter
_
Sample,Sample Rate
Multiplier,48000Hz,44100Hz,32000Hz
=
@Input sub i@,@*@,1.0,1.0,1.0
@Input sub {i~-~1}@,@*@,-1.9722337291952701,-1.96977855582618,-1.9583538097539801
@Input sub {i~-~2}@,@*@,0.97261396931305999,0.97022847566350001,0.95920349965458995
_
.TE
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r | r | r |.
_
BButter
_
Sample,Sample Rate
Multiplier,48000Hz,44100Hz,32000Hz
=
@Output sub i@,@*@,0.98621192462707996,0.98500175787241995,0.97938932735214002
@Output sub {i~-~1}@,@*@,-1.9724238492541599,-1.9700035157448399,-1.95877865470428
@Output sub {i~-~2}@,@*@,0.98621192462707996,0.98500175787241995,0.97938932735214002
_
.TE
