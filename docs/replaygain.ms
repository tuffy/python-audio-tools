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
In purely mathematical terms, the filter looks like this:
.EQ
"Output" sub i = 
left ({sum from {j = i-order} to i
{{"Input" sub j} * {"Input Filter" sub j}}} right )
~~-~~
left ({sum from {k = i-order} to {i~-~1}
{{"Output" sub k} * {"Output Filter" sub k}}} right )
.EN
`Input Filter' and `Output Filter' are lists of predefined values.
`Order' refers to the size of those lists.
When filtering at the start of the stream, treat any samples
before the beginning as 0.
.PP
Since this explanation is getting vague and theoretical, let's move on
to the filter values themselves and an example of how to apply them.
.bp
.SUBSUBSECTION "the Yule Filter"
.PP
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r  | r | r |.
_
Yule Input Filter
_
Sample to,Sample Rate
Multiply,48000Hz,44100Hz,32000Hz
=
@Input sub i@,@*@,0.038575994352000001,0.054186564064300002,0.15457299681924
@Input sub {i~-~1}@,@*@,-0.021603671841850001,-0.029110078089480001,-0.093310490563149995
@Input sub {i~-~2}@,@*@,-0.0012339531685100001,-0.0084870937985100006,-0.062478801536530001
@Input sub {i~-~3}@,@*@,-9.2916779589999993e-05,-0.0085116564546900003,0.021635418887979999
@Input sub {i~-~4}@,@*@,-0.016552603416190002,-0.0083499090493599996,-0.05588393329856
@Input sub {i~-~5}@,@*@,0.02161526843274,0.022452932533390001,0.047814766749210001
@Input sub {i~-~6}@,@*@,-0.02074045215285,-0.025963385129149998,0.0022231259774300001
@Input sub {i~-~7}@,@*@,0.0059429806512499997,0.016248649629749999,0.031740925400489998
@Input sub {i~-~8}@,@*@,0.0030642802319099998,-0.0024087905158400001,-0.013905894218979999
@Input sub {i~-~9}@,@*@,0.00012025322027,0.0067461368224699999,0.00651420667831
@Input sub {i~-~10}@,@*@,.0028846368391600001,-0.00187763777362,-0.0088136273383899993
_
.TE
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r | r | r |.
_
Yule Output Filter
_
Sample to,Sample Rate
Multiply,48000Hz,44100Hz,32000Hz
=
@Output sub {i~-~1}@,@*@,-3.8466461711806699,-3.4784594855007098,-2.3789883497308399
@Output sub {i~-~2}@,@*@,7.81501653005538,6.3631777756614802,2.84868151156327
@Output sub {i~-~3}@,@*@,-11.341703551320419,-8.5475152747187408,-2.6457717022982501
@Output sub {i~-~4}@,@*@,13.055042193275449,9.4769360780128,2.2369765745171302
@Output sub {i~-~5}@,@*@,-12.28759895145294,-8.8149868137015499,-1.67148153367602
@Output sub {i~-~6}@,@*@,9.4829380631978992,6.8540154093699801,1.0059595480854699
@Output sub {i~-~7}@,@*@,-5.8725786177599897,-4.3947099607955904,-0.45953458054982999
@Output sub {i~-~8}@,@*@,2.7546586187461299,2.1961168489077401,0.16378164858596
@Output sub {i~-~9}@,@*@,-0.86984376593551005,-0.75104302451432003,-0.050320777171309998
@Output sub {i~-~10}@,@*@,0.13919314567432001,0.13149317958807999,0.023478974070199998
_
.TE
.SUBSUBSECTION "the Butter Filter"
.PP
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r | r | r |.
_
Butter Input Filter
_
Sample to,Sample Rate
Multiply,48000Hz,44100Hz,32000Hz
=
@Input sub i@,@*@,0.98621192462707996,0.98500175787241995,0.97938932735214002
@Input sub {i~-~1}@,@*@,-1.9724238492541599,-1.9700035157448399,-1.95877865470428
@Input sub {i~-~2}@,@*@,0.98621192462707996,0.98500175787241995,0.97938932735214002
_
.TE
.TS
tab(,);
| c s s s s |
| c s | c s s |
| c s | r r r |
| l c r | r | r |.
_
Butter Output Filter
_
Sample to,Sample Rate
Multiply,48000Hz,44100Hz,32000Hz
=
@Output sub {i~-~1}@,@*@,-1.9722337291952701,-1.96977855582618,-1.9583538097539801
@Output sub {i~-~2}@,@*@,0.97261396931305999,0.97022847566350001,0.95920349965458995
_
.TE
.bp
.SUBSUBSECTION "a Filtering Example"
.PP
When performing ReplayGain calculations, we'll start by converting
all our samples to floating-point values between -1.0 and 1.0.
This is a simple matter of dividing each sample by @2 sup {"bits-per-sample"~-~1}@.
So for 16-bit samples, divide each one by 32768.
.PP
Next, let's assume we have a 44100Hz stream and 
our previous input and output samples are as follows:
.TS
tab(,);
| c | c | c |
| r | r | r |.
_
Sample,Input,Output
=
89,-0.001007080078125,-0.00045495715387008651
90,-0.0009765625,-0.00045569008938487577
91,-0.001068115234375,-0.00044710087844377787
92,-0.0009765625,-0.00044127330865733358
93,-0.00091552734375,-0.00043189463254365861
94,-0.0009765625,-0.00041441662610518335
95,-0.001007080078125,-0.00040230590245440639
96,-0.00091552734375,-0.0004015602553121536
97,-0.00091552734375,-0.00040046613041640292
98,-0.00091552734375,-0.00039336026519054979
99,-0.0009765625,-0.00039087401794557448
_
.TE
If the value of sample 100 from the input stream is 
-0.00091552734375 (@-30 / {2 sup 15}@), here's how we calculate
output sample 100:
.ps 8
.TS
tab(,);
| c | c s c s c |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r   s s s c r |.
_
Sample,Input Value,Yule Input Filter,Result
=
90,-0.0009765625,*,-0.00187763777362,@=@,1.8336306383007813e-06
91,-0.001068115234375,*,0.0067461368224699999,@=@,-7.2056515132583621e-06
92,-0.0009765625,*,-0.0024087905158400001,@=@,2.3523344881250001e-06
93,-0.00091552734375,*,0.016248649629749999,@=@,-1.4876083035049437e-05
94,-0.0009765625,*,-0.025963385129149998,@=@,2.5354868290185545e-05
95,-0.001007080078125,*,0.022452932533390001,@=@,-2.2611901049861755e-05
96,-0.00091552734375,*,-0.0083499090493599996,@=@,7.6445700525146477e-06
97,-0.00091552734375,*,-0.0085116564546900003,@=@,7.7926542248748791e-06
98,-0.00091552734375,*,-0.0084870937985100006,@=@,7.770166441506958e-06
99,-0.0009765625,*,-0.029110078089480001,@=@,2.8427810634257813e-05
100,\fB-0.00091552734375\fR,*,0.054186564064300002,@=@,-4.9609281064727785e-05
_
Input Values Sum,@=@,-1.3126881893131719e-05
_
.TE
.ps
.ps 8
.TS
tab(,);
| c | c s c s c |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r   s s s c r |.
_
Sample,Output Value,Yule Output Filter,Result
=
90,-0.00045569008938487577,*,0.13149317958807999,@=@,-5.9920138759993691e-05
91,-0.00044710087844377787,*,-0.75104302451432003,@=@,0.00033579199600942429
92,-0.00044127330865733358,*,2.1961168489077401,@=@,-0.00096908774811563594
93,-0.00043189463254365861,*,-4.3947099607955904,@=@,0.0018980516436537679
94,-0.00041441662610518335,*,6.8540154093699801,@=@,-0.002840417941224044
95,-0.00040230590245440639,*,-8.8149868137015499,@=@,0.0035463212252098944
96,-0.0004015602553121536,*,9.4769360780128,@=@,-0.0038055608710637796
97,-0.00040046613041640292,*,-8.5475152747187408,@=@,0.0034229903667417111
98,-0.00039336026519054979,*,6.3631777756614802,@=@,-0.0025030212972888127
99,-0.00039087401794557448,*,-3.4784594855007098,@=@,0.0013596394353585582
_
Output Values Sum,@=@,0.00038478667052108985
_
.TE
.ps 8
-1.3126881893131719e-05 (input values sum) - 
0.00038478667052108985 (output value sum) =
.br
\fB-0.00039791355241422158\fR (output sample 100).
.PP
We're not quite done yet.
Remember, ReplayGain's equal loudness filter requires both
a Yule \fIand\fR Butter filter, in that order.
.TS
tab(,);
| c | c | c |
| r | r | r |.
_
Sample,Input,Output
=
97,-0.00040046613041640292,1.2422165031560971e-05
98,-0.00039336026519054979,1.8657680223143899e-05
99,-0.00039087401794557448,2.0148828330135515e-05
_
.TE
Notice how Butter's input samples are Yule's output samples.
Thus, our next input sample to the Butter filter is -0.00039791355241422158.
Calculating sample 100 is now a similar process:
.ps 8
.TS
tab(,);
| c | c s c s c |
| r | r c r c r |
| r | r c r c r |
| r | r c r c r |
| r   s s s c r |.
_
Sample,Input Value,Butter Input Filter,Result
=
98,-0.00039336026519054979,*,0.98500175787241995,@=@,-0.00038746055268985282
99,-0.00039087401794557448,*,-1.9700035157448399,@=@,0.0007700231895660934
100,\fB-0.00039791355241422158\fR,*,0.98500175787241995,@=@,-0.0003919455486092676
_
Input Values Sum,@=@,-9.38291173302702e-06
_
.TE
.ps
.ps 8
.TS
tab(,);
| c | c s c s c |
| r | r c r c r |
| r | r c r c r |
| r   s s s c r |.
_
Sample,Output Value,Butter Output Filter,Result
=
98,1.8657680223143899e-05,*,0.97022847566350001,@=@,1.8102212642317936e-05
99,2.0148828330135515e-05,*,-1.96977855582618,@=@,-3.968872996972396e-05
_
Output Values Sum,@=@,-2.1586517327406024e-05
_
.TE
-9.38291173302702e-06 (input values sum) - -2.1586517327406024e-05 (output values sum) =
.br
\fB1.2203605594379004e-05\fR (output sample 100).
