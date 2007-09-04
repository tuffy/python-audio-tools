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


import audiotools
import tempfile,sys

class BLANK_PCM_Reader:
    #length is the total length of this PCM stream, in seconds
    def __init__(self, length,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = length
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.bytes_remaining = length * sample_rate * channels * \
            bits_per_sample / 8
        self.buffer = ""

    def read(self, bytes):
        if (bytes < self.bytes_remaining):
            if (bytes != len(self.buffer)):
                self.buffer = '\x01\x00' * (bytes / 2)
            self.bytes_remaining -= bytes
            return self.buffer
        elif (self.bytes_remaining > 0):
            self.bytes_remaining = 0
            return '\x01\x00' * (bytes / 2)
        else:
            return ""


    def close(self):
        pass

class PCM_Count:
    def __init__(self):
        self.count = 0
    
    def write(self, bytes):
        self.count += len(bytes)
    
    def __len__(self):
        return self.count

class DummyMetaData(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"Track Name",
                                     track_number=5,
                                     album_name=u"Album Name",
                                     artist_name=u"Artist Name")

TEST_LENGTH = 120
#TEST_LENGTH = 3600
#TEST_LENGTH = 60

def test_format(AudioFormat):
    temp = tempfile.NamedTemporaryFile(suffix="." + AudioFormat.SUFFIX)
    try:
        file_matches = True
        dummy_metadata = DummyMetaData()

        audiofile = AudioFormat.from_pcm(temp.name,
                                         BLANK_PCM_Reader(TEST_LENGTH))
        audiofile.set_metadata(dummy_metadata)
        if (audiofile.lossless()):
            file_matches = audiotools.pcm_cmp(
                audiofile.to_pcm(),BLANK_PCM_Reader(TEST_LENGTH))
        else:
            p = audiofile.to_pcm()
            counter = PCM_Count()
            audiotools.transfer_data(p.read,counter.write)
            p.close()
            file_matches = (len(counter) > 0)

        audiofile = audiotools.open(audiofile.filename)
        file_metadata = audiofile.get_metadata()
        if (file_metadata != None):
            if (not file_matches):
                print >>sys.stderr,"* File data mismatch"
            if (file_metadata != dummy_metadata):
                #print >>sys.stderr,""
                #print >>sys.stderr,repr(file_metadata)
                #print >>sys.stderr,repr(dummy_metadata)
                print >>sys.stderr,"* File metadata mismatch"
            return file_matches and (file_metadata == dummy_metadata)
        else:
            if (not file_matches):
                print >>sys.stderr,"* File data mismatch"
            return file_matches
    finally:
        temp.close()

if (__name__ == '__main__'):
    print "Testing Audio Tools"

    if (len(sys.argv) == 1):
        type_dict = audiotools.TYPE_MAP
    else:
        type_dict = dict([(key,value) for (key,value) in
                          audiotools.TYPE_MAP.items() if
                          key in sys.argv[1:]])
    
    max_suffix_length = max([len(s) for s in type_dict.keys()])
    for audiotype in type_dict.values():
        sys.stdout.write(
            "* Testing %%%d.%ds :" % (max_suffix_length,
                                      max_suffix_length) % (audiotype.SUFFIX))
        sys.stdout.flush()
        if (test_format(audiotype)):
            print " OK"
        else:
            print " FAILS"
