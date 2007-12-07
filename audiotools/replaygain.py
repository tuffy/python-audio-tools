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

AYule = ((1.0, -3.8466461711806699, 7.81501653005538, -11.341703551320419, 13.055042193275449, -12.28759895145294, 9.4829380631978992, -5.8725786177599897, 2.7546586187461299, -0.86984376593551005, 0.13919314567432001),
         (1.0, -3.4784594855007098, 6.3631777756614802, -8.5475152747187408, 9.4769360780128, -8.8149868137015499, 6.8540154093699801, -4.3947099607955904, 2.1961168489077401, -0.75104302451432003, 0.13149317958807999),
         (1.0, -2.3789883497308399, 2.84868151156327, -2.6457717022982501, 2.2369765745171302, -1.67148153367602, 1.0059595480854699, -0.45953458054982999, 0.16378164858596, -0.050320777171309998, 0.023478974070199998),
         (1.0, -1.6127316513724701, 1.0797749225997, -0.2565625775407, -0.1627671912044, -0.22638893773905999, 0.39120800788283999, -0.22138138954924999, 0.045002353873520001, 0.020058518065010002, 0.0030243909574099999),
         (1.0, -1.4985897936779899, 0.87350271418187997, 0.12205022308084, -0.80774944671437998, 0.47854794562325997, -0.12453458140019, -0.040675101970140001, 0.083337552841070001, -0.042373480257460003, 0.029772073199250002),
         (1.0, -0.62820619233671005, 0.29661783706366002, -0.37256372942400001, 0.0021376785712399998, -0.42029820170917997, 0.22199650564824, 0.0061342435068200002, 0.06747620744683, 0.057848203758010003, 0.032227540721730001),
         (1.0, -1.0480033512634901, 0.29156311971248999, -0.26806001042946997, 0.0081999964585799997, 0.45054734505007998, -0.33032403314005998, 0.067393683331100004, -0.047842542290329998, 0.016399078361890002, 0.018073643235729998),
         (1.0, -0.51035327095184002, -0.31863563325244998, -0.20256413484477001, 0.14728154134329999, 0.38952639978998999, -0.23313271880868, -0.052460190244630001, -0.025059617240530001, 0.02442357316099, 0.01818801111503),
         (1.0, -0.25049871956019998, -0.43193942311113998, -0.034246810176749999, -0.046783287842420002, 0.26408300200954998, 0.15113130533215999, -0.17556493366449, -0.18823009262115001, 0.054777204286740003, 0.047044096881200002)
         )

BYule = ((0.038575994352000001, -0.021603671841850001, -0.0012339531685100001, -9.2916779589999993e-05, -0.016552603416190002, 0.02161526843274, -0.02074045215285, 0.0059429806512499997, 0.0030642802319099998, 0.00012025322027, 0.0028846368391600001),
         (0.054186564064300002, -0.029110078089480001, -0.0084870937985100006, -0.0085116564546900003, -0.0083499090493599996, 0.022452932533390001, -0.025963385129149998, 0.016248649629749999, -0.0024087905158400001, 0.0067461368224699999, -0.00187763777362),
         (0.15457299681924, -0.093310490563149995, -0.062478801536530001, 0.021635418887979999, -0.05588393329856, 0.047814766749210001, 0.0022231259774300001, 0.031740925400489998, -0.013905894218979999, 0.00651420667831, -0.0088136273383899993),
         (0.30296907319326999, -0.22613988682123001, -0.085873237307719993, 0.032829301726640003, -0.0091570293343400007, -0.02364141202522, -0.0058445603991300003, 0.062761013217490003, -8.2808674800000004e-06, 0.0020586188556400002, -0.029501349832869998),
         (0.33642304856131999, -0.25572241425570003, -0.11828570177555001, 0.11921148675203, -0.078344896094790006, -0.0046997791438, -0.0058950022444000001, 0.057242281403510002, 0.0083204398077299999, -0.016353813845399998, -0.017601765681500001),
         (0.44915256608449999, -0.14351757464546999, -0.22784394429749, -0.01419140100551, 0.040782627971389998, -0.12398163381747999, 0.04097565135648, 0.10478503600251, -0.01863887810927, -0.031934284389149997, 0.0054190774870700002),
         (0.56619470757640999, -0.75464456939302005, 0.16242137742230001, 0.16744243493672001, -0.18901604199609001, 0.30931782841830002, -0.27562961986223999, 0.0064731067724599998, 0.086475037803509999, -0.037889845548399997, -0.0058821544342100001),
         (0.58100494960552995, -0.53174909058578002, -0.14289799034253001, 0.17520704835522, 0.02377945217615, 0.15558449135572999, -0.25344790059353001, 0.016284624063329999, 0.069204677639589998, -0.03721611395801, -0.0074961879717200001),
         (0.53648789255105001, -0.42163034350695999, -0.0027595361192900001, 0.042678422194150002, -0.10214864179676, 0.14590772289387999, -0.024598648593450002, -0.11202315195388, -0.04060034127, 0.047886655481800003, -0.02217936801134)
         )

AButter = ((1.0, -1.9722337291952701, 0.97261396931305999),
           (1.0, -1.96977855582618, 0.97022847566350001),
           (1.0, -1.9583538097539801, 0.95920349965458995),
           (1.0, -1.9500275914987799, 0.95124613669835001),
           (1.0, -1.94561023566527, 0.94705070426117999),
           (1.0, -1.9278328697703599, 0.93034775234267997),
           (1.0, -1.91858953033784, 0.92177618768380998),
           (1.0, -1.9154210807478, 0.91885558323625005),
           (1.0, -1.88903307939452, 0.89487434461663995))

BButter = ((0.98621192462707996, -1.9724238492541599, 0.98621192462707996),
           (0.98500175787241995, -1.9700035157448399, 0.98500175787241995),
           (0.97938932735214002, -1.95877865470428, 0.97938932735214002),
           (0.97531843204928004, -1.9506368640985701, 0.97531843204928004),
           (0.97316523498161001, -1.94633046996323, 0.97316523498161001),
           (0.96454515552826003, -1.9290903110565201, 0.96454515552826003),
           (0.96009142950541004, -1.9201828590108201, 0.96009142950541004),
           (0.95856916599601005, -1.9171383319920301, 0.95856916599601005),
           (0.94597685600279002, -1.89195371200558, 0.94597685600279002))

SAMPLE_RATE_MAP = {48000:0,44100:1,32000:2,24000:3,22050:4,
                   16000:5,12000:6,11025:7,8000:8}


PINK_REF = 64.82

class Filter:
    def __init__(self, input_kernel, output_kernel):
        self.input_kernel = input_kernel
        self.output_kernel = output_kernel

        self.unfiltered_samples = [0.0] * len(self.input_kernel)        
        self.filtered_samples = [0.0] * len(self.output_kernel)

    #takes a list of floating point samples
    #returns a list of filtered floating point samples
    def filter(self, samples):
        toreturn = []

        input_kernel = tuple(reversed(self.input_kernel))
        output_kernel = tuple(reversed(self.output_kernel[1:]))

        for s in samples:
            self.unfiltered_samples.append(s)

            filtered = sum([i * k for i,k in zip(
                self.unfiltered_samples[-len(input_kernel):],
                input_kernel)]) - \
                       sum([i * k for i,k in zip(
                self.filtered_samples[-len(output_kernel):],
                output_kernel)])

            self.filtered_samples.append(filtered)
            toreturn.append(filtered)
                

        #if we have more filtered and unfiltered samples than we'll need,
        #chop off the excess at the beginning
        if (len(self.unfiltered_samples) > (len(self.input_kernel))):
            self.unfiltered_samples = self.unfiltered_samples[-len(self.input_kernel):]
            
        if (len(self.filtered_samples) > (len(self.output_kernel))):
            self.filtered_samples = self.filtered_samples[-len(self.output_kernel):]

        return toreturn


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
            BYule[SAMPLE_RATE_MAP[self.sample_rate]],
            AYule[SAMPLE_RATE_MAP[self.sample_rate]])

        self.yule_filter_r = Filter(
            BYule[SAMPLE_RATE_MAP[self.sample_rate]],
            AYule[SAMPLE_RATE_MAP[self.sample_rate]])
        
        self.butter_filter_l = Filter(
            BButter[SAMPLE_RATE_MAP[self.sample_rate]],
            AButter[SAMPLE_RATE_MAP[self.sample_rate]])

        self.butter_filter_r = Filter(
            BButter[SAMPLE_RATE_MAP[self.sample_rate]],
            AButter[SAMPLE_RATE_MAP[self.sample_rate]])

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

