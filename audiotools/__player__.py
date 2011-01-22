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


(RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN) = range(3)

class Player:
    def __init__(self, audio_output,
                 replay_gain=RG_NO_REPLAYGAIN,
                 next_track_callback=lambda f: f):
        self.command_queue = Queue.Queue()
        self.worker = PlayerThread(audio_output,
                                   self.command_queue,
                                   replay_gain)
        self.thread = threading.Thread(target=self.worker.run,
                                       args=(next_track_callback,))
        self.thread.daemon = True
        self.thread.start()

    def open(self, track):
        self.track = track
        self.command_queue.put(("open", [track]))

    def play(self):
        self.command_queue.put(("play", []))

    def set_replay_gain(self, replay_gain):
        self.command_queue.put(("set_replay_gain", [replay_gain]))

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
    def __init__(self, audio_output, command_queue,
                 replay_gain=RG_NO_REPLAYGAIN):
        self.audio_output = audio_output
        self.command_queue = command_queue
        self.replay_gain = replay_gain

        self.track = None
        self.pcmconverter = None
        self.frames_played = 0
        self.total_frames = 0
        self.state = PLAYER_STOPPED

    def open(self, track):
        self.stop()
        self.track = track
        self.frames_played = 0
        self.total_frames = track.total_frames()

    def pause(self):
        if (self.state == PLAYER_PLAYING):
            self.state = PLAYER_PAUSED

    def play(self):
        if (self.track is not None):
            if (self.state == PLAYER_STOPPED):
                if (self.replay_gain == RG_TRACK_GAIN):
                    replay_gain = self.track.replay_gain()
                    if (replay_gain is not None):
                        pcmreader = audiotools.ReplayGainReader(
                            self.track.to_pcm(),
                            replay_gain.track_gain,
                            replay_gain.track_peak)
                    else:
                        pcmreader = self.track.to_pcm()
                elif (self.replay_gain == RG_ALBUM_GAIN):
                    replay_gain = self.track.replay_gain()
                    if (replay_gain is not None):
                        pcmreader = audiotools.ReplayGainReader(
                            self.track.to_pcm(),
                            replay_gain.album_gain,
                            replay_gain.album_peak)
                    else:
                        pcmreader = self.track.to_pcm()
                else:
                    pcmreader = self.track.to_pcm()

                if (not self.audio_output.compatible(pcmreader)):
                    self.audio_output.init(
                        sample_rate=pcmreader.sample_rate,
                        channels=pcmreader.channels,
                        channel_mask=pcmreader.channel_mask,
                        bits_per_sample=pcmreader.bits_per_sample)
                self.pcmconverter = audiotools.ThreadedPCMConverter(
                    pcmreader,
                    self.audio_output.framelist_converter())
                self.frames_played = 0
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PAUSED):
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PLAYING):
                pass

    def set_replay_gain(self, replay_gain):
        self.replay_gain = replay_gain

    def toggle_play_pause(self):
        if (self.state == PLAYER_PLAYING):
            self.pause()
        elif ((self.state == PLAYER_PAUSED) or
              (self.state == PLAYER_STOPPED)):
            self.play()

    def stop(self):
        if (self.pcmconverter is not None):
            self.pcmconverter.close()
            del(self.pcmconverter)
            self.pcmconverter = None
        self.frames_played = 0
        self.state = PLAYER_STOPPED

    def run(self, next_track_callback = lambda f: f):
        while (True):
            if ((self.state == PLAYER_STOPPED) or
                (self.state == PLAYER_PAUSED)):
                (command, args) = self.command_queue.get(True)
                if (command == "exit"):
                    self.audio_output.close()
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
        self.thread.join()


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

    @classmethod
    def available(self):
        return False

class NULLAudioOutput(AudioOutput):
    NAME = "NULL"

    def framelist_converter(self):
        return lambda f: f.frames

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

    def play(self, data):
        time.sleep(float(data) / self.sample_rate)

    def close(self):
        pass

    @classmethod
    def available(self):
        return True

class OSSAudioOutput(AudioOutput):
    NAME = "OSS"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        if (not self.initialized):
            import ossaudiodev

            self.sample_rate = sample_rate
            self.channels = channels
            self.channel_mask = channel_mask
            self.bits_per_sample = bits_per_sample

            self.ossaudio = ossaudiodev.open('w')
            if (self.bits_per_sample == 8):
                self.ossaudio.setfmt(ossaudiodev.AFMT_S8_LE)
            elif (self.bits_per_sample == 16):
                self.ossaudio.setfmt(ossaudiodev.AFMT_S16_LE)
            elif (self.bits_per_sample == 24):
                self.ossaudio.setfmt(ossaudiodev.AFMT_S16_LE)
            else:
                raise ValueError("Unsupported bits-per-sample")

            self.ossaudio.channels(channels)
            self.ossaudio.speed(sample_rate)

            self.initialized = True
        else:
            self.close()
            self.init(sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)

    def framelist_converter(self):
        if (self.bits_per_sample == 8):
            return lambda f: f.to_bytes(False, True)
        elif (self.bits_per_sample == 16):
            return lambda f: f.to_bytes(False, True)
        elif (self.bits_per_sample == 24):
            import audiotools.pcm

            return lambda f: audiotools.pcm.from_list(
                [i >> 8 for i in list(f)],
                self.channels, 16, True).to_bytes(False, True)
        else:
            raise ValueError("Unsupported bits-per-sample")

    def play(self, data):
        self.ossaudio.writeall(data)

    def close(self):
        if (self.initialized):
            self.initialized = False
            self.ossaudio.close()

    @classmethod
    def available(self):
        try:
            import ossaudiodev
            return True
        except ImportError:
            return False

class PulseAudioOutput(AudioOutput):
    NAME = "PulseAudio"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        if (not self.initialized):
            import subprocess

            self.sample_rate = sample_rate
            self.channels = channels
            self.channel_mask = channel_mask
            self.bits_per_sample = bits_per_sample

            if (bits_per_sample == 8):
                format = "u8"
            elif (bits_per_sample == 16):
                format = "s16le"
            elif (bits_per_sample == 24):
                format = "s24le"
            else:
                raise ValueError("Unsupported bits-per-sample")

            self.pacat = subprocess.Popen(
                [audiotools.BIN["pacat"],
                 "--rate", str(sample_rate),
                 "--format", format,
                 "--channels", str(channels),
                 "--latency-msec",str(10)],
                stdin=subprocess.PIPE)

            self.initialized = True
        else:
            self.close()
            self.init(sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)

    def framelist_converter(self):
        if (self.bits_per_sample == 8):
            return lambda f: f.to_bytes(True, False)
        elif (self.bits_per_sample == 16):
            return lambda f: f.to_bytes(False, True)
        elif (self.bits_per_sample == 24):
            return lambda f: f.to_bytes(False, True)
        else:
            raise ValueError("Unsupported bits-per-sample")

    def play(self, data):
        self.pacat.stdin.write(data)
        self.pacat.stdin.flush()

    def close(self):
        if (self.initialized):
            self.initialized = False
            self.pacat.stdin.close()
            self.pacat.wait()

    @classmethod
    def available(self):
        return True #FIXME
        # raise NotImplementedError()

class PortAudioOutput(AudioOutput):
    NAME = "PortAudio"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        if (not self.initialized):
            import pyaudio

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
        return lambda f: f.to_bytes(False, True)

    def play(self, data):
        self.stream.write(data)

    def close(self):
        if (self.initialized):
            self.stream.close()
            self.pyaudio.terminate()
            self.initialized = False

    @classmethod
    def available(self):
        try:
            import pyaudio
            return True
        except ImportError:
            return False

AUDIO_OUTPUT = (PulseAudioOutput, OSSAudioOutput,
                PortAudioOutput, NULLAudioOutput)
