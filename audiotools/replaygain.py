#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007  Brian Langenberger

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


#This is a module for ReplayGain calculation of a given PCM stream.
#It is included as a reference implementation and not as a substitute
#for external ReplayGain calculators.

#The first problem with it is that the results are not identical
#to those of external calculators, by about a 100th of a dB or so.
#This is probably because the C-based implementations use floats
#while Python uses doubles.  Thus the difference in rounding errors.

#The second problem with it is it's very, very slow.
#Python is ill-suited to these kinds of rolling loop calculations
#involving thousands of samples per second, so the Python-based
#approach is several times slower than real-time.


import audiotools
import audiotools.pcmstream
from itertools import izip

ABYule = (
    (0.03857599435200, -3.84664617118067, -0.02160367184185,  7.81501653005538, -0.00123395316851,-11.34170355132042, -0.00009291677959, 13.05504219327545, -0.01655260341619,-12.28759895145294,  0.02161526843274,  9.48293806319790, -0.02074045215285, -5.87257861775999,  0.00594298065125,  2.75465861874613,  0.00306428023191, -0.86984376593551,  0.00012025322027,  0.13919314567432,  0.00288463683916 ),
    (0.05418656406430, -3.47845948550071, -0.02911007808948,  6.36317777566148, -0.00848709379851, -8.54751527471874, -0.00851165645469,  9.47693607801280, -0.00834990904936, -8.81498681370155,  0.02245293253339,  6.85401540936998, -0.02596338512915, -4.39470996079559,  0.01624864962975,  2.19611684890774, -0.00240879051584, -0.75104302451432,  0.00674613682247,  0.13149317958808, -0.00187763777362 ),
    (0.15457299681924, -2.37898834973084, -0.09331049056315,  2.84868151156327, -0.06247880153653, -2.64577170229825,  0.02163541888798,  2.23697657451713, -0.05588393329856, -1.67148153367602,  0.04781476674921,  1.00595954808547,  0.00222312597743, -0.45953458054983,  0.03174092540049,  0.16378164858596, -0.01390589421898, -0.05032077717131,  0.00651420667831,  0.02347897407020, -0.00881362733839 ),
    (0.30296907319327, -1.61273165137247, -0.22613988682123,  1.07977492259970, -0.08587323730772, -0.25656257754070,  0.03282930172664, -0.16276719120440, -0.00915702933434, -0.22638893773906, -0.02364141202522,  0.39120800788284, -0.00584456039913, -0.22138138954925,  0.06276101321749,  0.04500235387352, -0.00000828086748,  0.02005851806501,  0.00205861885564,  0.00302439095741, -0.02950134983287 ),
    (0.33642304856132, -1.49858979367799, -0.25572241425570,  0.87350271418188, -0.11828570177555,  0.12205022308084,  0.11921148675203, -0.80774944671438, -0.07834489609479,  0.47854794562326, -0.00469977914380, -0.12453458140019, -0.00589500224440, -0.04067510197014,  0.05724228140351,  0.08333755284107,  0.00832043980773, -0.04237348025746, -0.01635381384540,  0.02977207319925, -0.01760176568150 ),
    (0.44915256608450, -0.62820619233671, -0.14351757464547,  0.29661783706366, -0.22784394429749, -0.37256372942400, -0.01419140100551,  0.00213767857124,  0.04078262797139, -0.42029820170918, -0.12398163381748,  0.22199650564824,  0.04097565135648,  0.00613424350682,  0.10478503600251,  0.06747620744683, -0.01863887810927,  0.05784820375801, -0.03193428438915,  0.03222754072173,  0.00541907748707 ),
    (0.56619470757641, -1.04800335126349, -0.75464456939302,  0.29156311971249,  0.16242137742230, -0.26806001042947,  0.16744243493672,  0.00819999645858, -0.18901604199609,  0.45054734505008,  0.30931782841830, -0.33032403314006, -0.27562961986224,  0.06739368333110,  0.00647310677246, -0.04784254229033,  0.08647503780351,  0.01639907836189, -0.03788984554840,  0.01807364323573, -0.00588215443421 ),
    (0.58100494960553, -0.51035327095184, -0.53174909058578, -0.31863563325245, -0.14289799034253, -0.20256413484477,  0.17520704835522,  0.14728154134330,  0.02377945217615,  0.38952639978999,  0.15558449135573, -0.23313271880868, -0.25344790059353, -0.05246019024463,  0.01628462406333, -0.02505961724053,  0.06920467763959,  0.02442357316099, -0.03721611395801,  0.01818801111503, -0.00749618797172 ),
    (0.53648789255105, -0.25049871956020, -0.42163034350696, -0.43193942311114, -0.00275953611929, -0.03424681017675,  0.04267842219415, -0.04678328784242, -0.10214864179676,  0.26408300200955,  0.14590772289388,  0.15113130533216, -0.02459864859345, -0.17556493366449, -0.11202315195388, -0.18823009262115, -0.04060034127000,  0.05477720428674,  0.04788665548180,  0.04704409688120, -0.02217936801134 )
)

ABButter = (
    (0.98621192462708, -1.97223372919527, -1.97242384925416,  0.97261396931306,  0.98621192462708 ),
    (0.98500175787242, -1.96977855582618, -1.97000351574484,  0.97022847566350,  0.98500175787242 ),
    (0.97938932735214, -1.95835380975398, -1.95877865470428,  0.95920349965459,  0.97938932735214 ),
    (0.97531843204928, -1.95002759149878, -1.95063686409857,  0.95124613669835,  0.97531843204928 ),
    (0.97316523498161, -1.94561023566527, -1.94633046996323,  0.94705070426118,  0.97316523498161 ),
    (0.96454515552826, -1.92783286977036, -1.92909031105652,  0.93034775234268,  0.96454515552826 ),
    (0.96009142950541, -1.91858953033784, -1.92018285901082,  0.92177618768381,  0.96009142950541 ),
    (0.95856916599601, -1.91542108074780, -1.91713833199203,  0.91885558323625,  0.95856916599601 ),
    (0.94597685600279, -1.88903307939452, -1.89195371200558,  0.89487434461664,  0.94597685600279 )
)

SAMPLE_RATE_MAP = {48000:0,44100:1,32000:2,24000:3,22050:4,
                   16000:5,12000:6,11025:7,8000:8}


PINK_REF = 64.82

class Filter:
    def __init__(self, filter_func, kernel):
        self.kernel = kernel
        self.filter_func = filter_func

        self.unfiltered_samples = PositionedList([0.0] * \
                                                 (len(self.kernel) / 2))
        self.unfiltered_samples.current_index = len(self.unfiltered_samples)
        
        self.filtered_samples = [0.0] * (len(self.kernel) / 2)

    #takes a list of floating point samples
    #returns a list of filtered floating point samples
    def filter(self, samples):
        old_index = self.unfiltered_samples.current_index
        self.unfiltered_samples.extend(samples)
        
        
        self.filter_func(self.unfiltered_samples,
                         self.filtered_samples,
                         self.kernel)

        toreturn = self.filtered_samples[old_index:]

        #if we have more unfiltered samples than we'll need,
        #chop off the excess at the beginning
        if (len(self.unfiltered_samples) > (len(self.kernel) / 2)):
            self.unfiltered_samples = PositionedList(
                self.unfiltered_samples[-(len(self.kernel) / 2):])
            self.unfiltered_samples.current_index = len(self.unfiltered_samples)
        if (len(self.filtered_samples) > (len(self.kernel) / 2)):
            self.filtered_samples = self.filtered_samples[-(len(self.kernel) / 2):]

        return toreturn

#adjusts the array indexes in relation to current_index
class PositionedList(list):
    def __init__(self, sequence=None):
        list.__init__(self,sequence)
        self.current_index = 0

    def get(self, i):
        return list.__getitem__(self,self.current_index + i)

    def getslice(self, i, j):
        return self[self.current_index + i:self.current_index + j]

    def __repr__(self):
        return "%s%s" % (repr(self[0:self.current_index]),
                         repr(self[self.current_index:]))
    


def filter_yule(input, output, kernel):
    total_samples = len(input) - input.current_index
    
    input_kernel = tuple(reversed(kernel[0::2]))
    output_kernel = tuple(reversed(kernel[1::2]))

    while (total_samples > 0):
        output.append(1e-10 + \
            sum([i * k for (i,k) in izip(
                        input.getslice(-10,1),
                        input_kernel)]) - \
            sum([i * k for (i,k) in izip(
                        output[-10:],
                        output_kernel)])
                      )

        input.current_index += 1
        total_samples -= 1

def filter_butter(input, output, kernel):
    total_samples = len(input) - input.current_index
    
    input_kernel = tuple(reversed(kernel[0::2]))
    output_kernel = tuple(reversed(kernel[1::2]))

    while (total_samples > 0):
        output.append(sum([i * k for (i,k) in izip(
                        input.getslice(-2,1),
                        input_kernel)]) - \
                      sum([i * k for (i,k) in izip(
                        output[-2:],
                        output_kernel)]))
        input.current_index += 1
        total_samples -= 1


MAX_ORDER = 10

class EqualLoudnessFilter(audiotools.PCMReader):
    def __init__(self, pcmreader):
        if (pcmreader.channels != 2):
            raise ValueError("channels must equal 2")
        if (pcmreader.sample_rate not in SAMPLE_RATE_MAP.keys()):
            raise ValueError("unsupported sample rate")
        
        self.stream = audiotools.pcmstream.PCMStreamReader(
            pcmreader,
            pcmreader.bits_per_sample / 8,
            False,True)

        audiotools.PCMReader.__init__(
            self,
            self.stream,
            pcmreader.sample_rate,
            2,
            pcmreader.bits_per_sample)

        self.leftover_samples = []

        self.yule_filter_l = Filter(
            filter_yule,ABYule[SAMPLE_RATE_MAP[self.sample_rate]])

        self.yule_filter_r = Filter(
            filter_yule,ABYule[SAMPLE_RATE_MAP[self.sample_rate]])
        
        self.butter_filter_l = Filter(
            filter_butter, ABButter[SAMPLE_RATE_MAP[self.sample_rate]])

        self.butter_filter_r = Filter(
            filter_butter, ABButter[SAMPLE_RATE_MAP[self.sample_rate]])

    def read(self, bytes):
        #read in a bunch of floating point samples
        (frame_list,self.leftover_samples) = audiotools.FrameList.from_samples(
            self.leftover_samples + self.stream.read(bytes),
            self.channels)

        #convert them to a pair of floating-point channel lists
        l_channel = frame_list.channel(0)
        r_channel = frame_list.channel(1)

        #run our channel lists through the Yule and Butter filters
        l_channel = self.butter_filter_l.filter(
            self.yule_filter_l.filter(l_channel))
        
        r_channel = self.butter_filter_r.filter(
            self.yule_filter_r.filter(r_channel))

        #convert our channel lists back to integer samples
        multiplier = 1 << (self.bits_per_sample - 1)

        return audiotools.pcmstream.pcm_to_string(
            audiotools.FrameList.from_channels(
              ([int(round(s * multiplier)) for s in l_channel],
               [int(round(s * multiplier)) for s in r_channel])),
            self.bits_per_sample / 8,
            False)


#this takes a PCMReader-compatible object
#it yields FrameLists, each 50ms long (1/20th of a second)
#how many PCM frames that is varies depending on the sample rate
def replay_gain_blocks(pcmreader):
    unhandled_samples = []        #partial PCM frames
    frame_pool = audiotools.FrameList([],pcmreader.channels)
    
    reader = audiotools.pcmstream.PCMStreamReader(pcmreader,
                                                  pcmreader.bits_per_sample / 8,
                                                  False,False)
    
    (framelist,unhandled_samples) = audiotools.FrameList.from_samples(
        unhandled_samples + reader.read(audiotools.BUFFER_SIZE),
        pcmreader.channels)

    while ((len(framelist) > 0) or (len(unhandled_samples) > 0)):
        frame_pool.extend(framelist)

        while (frame_pool.total_frames() >= (pcmreader.sample_rate / 20)):
            yield audiotools.FrameList(
                frame_pool[0:
                           ((pcmreader.sample_rate / 20) * pcmreader.channels)],
                pcmreader.channels)
            frame_pool = audiotools.FrameList(
                frame_pool[((pcmreader.sample_rate / 20) * pcmreader.channels):],
                pcmreader.channels)

        (framelist,unhandled_samples) = audiotools.FrameList.from_samples(
            unhandled_samples + reader.read(audiotools.BUFFER_SIZE),
            pcmreader.channels)

    reader.close()
    #this drops the last block that's not 50ms long
    #that's probably the right thing to do
    

#takes a PCMReader-compatible object with 2 channels and a
#supported sample rate
#returns the stream's ReplayGain value in dB
def calculate_replay_gain(pcmstream):
    import math
    
    def __mean__(l):
        return sum(l) / len(l)

    pcmstream = EqualLoudnessFilter(pcmstream)
    
    db_blocks = []
    
    for block in replay_gain_blocks(pcmstream):
        left = __mean__([s ** 2 for s in block.channel(0)])
        right = __mean__([s ** 2 for s in block.channel(1)])
        db_blocks.append((left + right) / 2)
 
    db_blocks = [10 * math.log10(b + 10 ** -10) for b in db_blocks]
    db_blocks.sort()
    replay_gain = db_blocks[int(round(len(db_blocks) * 0.95))]

    return PINK_REF - replay_gain


if (__name__ == '__main__'):
    pass

