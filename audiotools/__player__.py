#!/usr/bin/bin

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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


import os
import sys
import cPickle
import select
import audiotools
import time
import Queue
import threading


class Player:
    def __init__(self, audio_output, next_track_callback=lambda f: f):
        self.command_queue = Queue.Queue()
        self.worker = PlayerThread(audio_output, self.command_queue)
        self.thread = threading.Thread(target=self.worker.run,
                                       args=(next_track_callback,))
        self.thread.daemon = True
        self.thread.start()

    def open(self, track):
        self.track = track
        self.command_queue.put(("open", [track]))

    def play(self):
        self.command_queue.put(("play", []))

    def pause(self):
        self.command_queue.put(("pause", []))

    def toggle_play_pause(self):
        self.command_queue.put(("toggle_play_pause", []))

    def stop(self):
        self.command_queue.put(("stop", []))

    def close(self):
        self.command_queue.put(("exit", []))

    def progress(self):
        return (self.worker.frames_played, self.worker.total_frames)


(PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING) = range(3)

class PlayerThread:
    def __init__(self, audio_output, command_queue):
        self.audio_output = audio_output
        self.command_queue = command_queue

        self.track = None
        self.pcmreader = None
        self.pcmconverter = None
        self.frames_played = 0
        self.total_frames = 0
        self.state = PLAYER_STOPPED

    def open(self, track):
        self.track = track
        self.pcmreader = None
        self.pcmconverter = None
        self.frames_played = 0
        self.total_frames = track.total_frames()
        self.state = PLAYER_STOPPED

    def pause(self):
        if (self.state == PLAYER_PLAYING):
            self.state = PLAYER_PAUSED

    def play(self):
        if (self.track is not None):
            if (self.state == PLAYER_STOPPED):
                self.pcmreader = self.track.to_pcm()
                if (not self.audio_output.compatible(self.pcmreader)):
                    self.audio_output.init(
                        sample_rate=self.pcmreader.sample_rate,
                        channels=self.pcmreader.channels,
                        channel_mask=self.pcmreader.channel_mask,
                        bits_per_sample=self.pcmreader.bits_per_sample)
                self.pcmconverter = audiotools.ThreadedPCMConverter(
                    self.pcmreader,
                    self.audio_output.framelist_converter())
                self.frames_played = 0
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PAUSED):
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PLAYING):
                pass

    def toggle_play_pause(self):
        if (self.state == PLAYER_PLAYING):
            self.state = PLAYER_PAUSED
        elif (self.state == PLAYER_PAUSED):
            self.state = PLAYER_PLAYING

    def stop(self):
        if (self.pcmconverter is not None):
            self.pcmconverter.close()
            self.pcmconverter = None
            self.pcmreader = None
        self.frames_played = 0
        self.state = PLAYER_STOPPED

    def run(self, next_track_callback = lambda f: f):
        while (True):
            if ((self.state == PLAYER_STOPPED) or
                (self.state == PLAYER_PAUSED)):
                (command, args) = self.command_queue.get(True)
                if (command == "exit"):
                    return
                else:
                    getattr(self, command)(*args)
            else:
                try:
                    (command, args) = self.command_queue.get_nowait()
                    if (command == "exit"):
                        return
                    else:
                        getattr(self, command)(*args)
                except Queue.Empty:
                    if (self.frames_played < self.total_frames):
                        (data, frames) = self.pcmconverter.read()
                        self.audio_output.play(data)
                        self.frames_played += frames
                        if (self.frames_played >= self.total_frames):
                            next_track_callback()
                    else:
                        self.stop()


class ThreadedPCMConverter:
    def __init__(self, pcmreader, converter):
        self.pcmreader = pcmreader
        self.decoded_data = Queue.Queue()
        self.stop_decoding = threading.Event()

        def convert(pcmreader, converter, decoded_data, stop_decoding):
            frame = pcmreader.read(audiotools.BUFFER_SIZE)
            while ((not stop_decoding.is_set()) and (len(frame) > 0)):
                decoded_data.put((converter(frame), frame.frames))
                frame = pcmreader.read(audiotools.BUFFER_SIZE)
            else:
                decoded_data.put((None, 0))
                pcmreader.close()

        self.thread = threading.Thread(target=convert,
                                       args=(pcmreader,
                                             converter,
                                             self.decoded_data,
                                             self.stop_decoding))
        self.thread.daemon = True
        self.thread.start()

    def read(self):
        """Returns a (converted_data, pcm_frame_count) tuple."""

        return self.decoded_data.get(True)

    def close(self):
        self.stop_decoding.set()


class AudioOutput:
    """An abstract parent class for playing audio."""

    def __init__(self):
        self.sample_rate = 0
        self.channels = 0
        self.channel_mask = 0
        self.bits_per_sample = 0
        self.initialized = False

    def compatible(self, pcmreader):
        """Returns True if the given pcmreader is compatible.

        If False, one is expected to open a new output stream
        which is compatible."""

        return ((self.sample_rate == pcmreader.sample_rate) and
                (self.channels == pcmreader.channels) and
                (self.channel_mask == pcmreader.channel_mask) and
                (self.bits_per_sample == pcmreader.bits_per_sample))

    def framelist_converter(self):
        """Returns a function which converts framelist objects

        to objects acceptable by our play() method."""

        raise NotImplementedError()

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """Initializes the output stream.

        This *must* be called prior to play() and close().
        The general flow of audio playing is:

        >>> pcm = audiofile.to_pcm()
        >>> player = AudioOutput(pcm.sample_rate,
        ...                      pcm.channels,
        ...                      pcm.channel_mask,
        ...                      pcm.bits_per_sample)
        >>> player.init()
        >>> convert = player.framelist_converter()
        >>> frame = pcm.read(1024)
        >>> while (len(frame) > 0):
        ...     player.play(convert(frame))
        ...     frame = pcm.read(1024)
        >>> player.close()
        """

        raise NotImplementedError()

    def play(self, data):
        """Plays a chunk of converted data"""

        raise NotImplementedError()

    def close(self):
        """Closes the output stream"""

        raise NotImplementedError()

try:
    import pyaudio

    class PortAudioOutput(AudioOutput):
        def init(self, sample_rate, channels, channel_mask, bits_per_sample):
            if (not self.initialized):
                self.sample_rate = sample_rate
                self.channels = channels
                self.channel_mask = channel_mask
                self.bits_per_sample = bits_per_sample

                self.pyaudio = pyaudio.PyAudio()
                self.stream = self.pyaudio.open(
                    format=self.pyaudio.get_format_from_width(
                        self.bits_per_sample / 8, False),
                    channels=self.channels,
                    rate=self.sample_rate,
                    output=True)

                self.initialized = True
            else:
                self.close()
                self.init(sample_rate=sample_rate,
                          channels=channels,
                          channel_mask=channel_mask,
                          bits_per_sample=bits_per_sample)

        def framelist_converter(self):
            def convert(framelist):
                return framelist.to_bytes(False, True)

            return convert

        def play(self, data):
            self.stream.write(data)

        def close(self):
            if (self.initialized):
                self.stream.close()
                self.pyaudio.terminate()
                self.initialized = False

except ImportError:
    pass
