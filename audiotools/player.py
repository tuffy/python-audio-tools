#!/usr/bin/bin

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

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


(RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN) = range(3)


class Player:
    """a class for operating an audio player

    the player itself runs in a seperate thread,
    which this sends commands to"""

    def __init__(self, audio_output,
                 replay_gain=RG_NO_REPLAYGAIN,
                 next_track_callback=lambda: None):
        """audio_output is an AudioOutput subclass
        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN,
        indicating how the player should apply ReplayGain
        next_track_callback is a function with no arguments
        which is called by the player when the current track is finished"""

        import Queue
        import threading

        self.command_queue = Queue.Queue()
        self.worker = PlayerThread(audio_output,
                                   self.command_queue,
                                   replay_gain)
        self.thread = threading.Thread(target=self.worker.run,
                                       args=(next_track_callback,))
        # self.thread.daemon = True
        self.thread.start()

    def open(self, track):
        """opens the given AudioFile for playing

        stops playing the current file, if any"""

        self.track = track
        self.command_queue.put(("open", [track]))

    def play(self):
        """begins or resumes playing an opened AudioFile, if any"""

        self.command_queue.put(("play", []))

    def set_replay_gain(self, replay_gain):
        """sets the given ReplayGain level to apply during playback

        choose from RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN
        replayGain cannot be applied mid-playback
        one must stop() and play() a file for it to take effect"""

        self.command_queue.put(("set_replay_gain", [replay_gain]))

    def pause(self):
        """pauses playback of the current file

        playback may be resumed with play() or toggle_play_pause()"""

        self.command_queue.put(("pause", []))

    def toggle_play_pause(self):
        """pauses the file if playing, play the file if paused"""

        self.command_queue.put(("toggle_play_pause", []))

    def stop(self):
        """stops playback of the current file

        if play() is called, playback will start from the beginning"""

        self.command_queue.put(("stop", []))

    def close(self):
        """closes the player for playback

        the player thread is halted and the AudioOutput is closed"""

        self.command_queue.put(("exit", []))

    def progress(self):
        """returns a (pcm_frames_played, pcm_frames_total) tuple

        this indicates the current playback status in PCM frames"""

        return (self.worker.frames_played, self.worker.total_frames)


(PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING) = range(3)


class PlayerThread:
    """the Player class' subthread

    this should not be instantiated directly;
    player will do so automatically"""

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
                    from .replaygain import ReplayGainReader
                    replay_gain = self.track.replay_gain()

                    if (replay_gain is not None):
                        pcmreader = ReplayGainReader(
                            self.track.to_pcm(),
                            replay_gain.track_gain,
                            replay_gain.track_peak)
                    else:
                        pcmreader = self.track.to_pcm()
                elif (self.replay_gain == RG_ALBUM_GAIN):
                    from .replaygain import ReplayGainReader
                    replay_gain = self.track.replay_gain()

                    if (replay_gain is not None):
                        pcmreader = ReplayGainReader(
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

                from . import BufferedPCMReader

                if (self.pcmconverter is not None):
                    self.pcmconverter.close()
                self.pcmconverter = PCMConverter(
                    BufferedPCMReader(pcmreader),
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

    def run(self, next_track_callback=lambda: None):
        import Queue

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
                        self.audio_output.close()
                        return
                    else:
                        getattr(self, command)(*args)
                except Queue.Empty:
                    if (self.frames_played < self.total_frames):
                        (data, frames) = self.pcmconverter.read()
                        if (frames > 0):
                            self.audio_output.play(data)
                            self.frames_played += frames
                            if (self.frames_played >= self.total_frames):
                                next_track_callback()
                        else:
                            self.frames_played = self.total_frames
                            next_track_callback()
                    else:
                        self.stop()


class CDPlayer:
    """a class for operating a CDDA player

    the player itself runs in a seperate thread,
    which this sends commands to"""

    def __init__(self, cdda, audio_output,
                 next_track_callback=lambda: None):
        """cdda is a audiotools.CDDA object
        audio_output is an AudioOutput subclass
        next_track_callback is a function with no arguments
        which is called by the player when the current track is finished"""

        import Queue
        import threading

        self.command_queue = Queue.Queue()
        self.worker = CDPlayerThread(cdda,
                                     audio_output,
                                     self.command_queue)
        self.thread = threading.Thread(target=self.worker.run,
                                       args=(next_track_callback,))
        self.thread.daemon = True
        self.thread.start()

    def open(self, track_number):
        """track_number indicates which track to open, starting from 1

        stops playing the current track, if any"""

        self.command_queue.put(("open", [track_number]))

    def play(self):
        """begins or resumes playing the currently open track, if any"""

        self.command_queue.put(("play", []))

    def pause(self):
        """pauses playback of the current track

        playback may be resumed with play() or toggle_play_pause()"""

        self.command_queue.put(("pause", []))

    def toggle_play_pause(self):
        """pauses the track if playing, play the track if paused"""

        self.command_queue.put(("toggle_play_pause", []))

    def stop(self):
        """stops playback of the current track

        if play() is called, playback will start from the beginning"""

        self.command_queue.put(("stop", []))

    def close(self):
        """closes the player for playback

        the player thread is halted and the AudioOutput is closed"""

        self.command_queue.put(("exit", []))

    def progress(self):
        """returns a (pcm_frames_played, pcm_frames_total) tuple

        this indicates the current playback status in PCM frames"""

        return (self.worker.frames_played, self.worker.total_frames)


class CDPlayerThread:
    """the CDPlayer class' subthread

    this should not be instantiated directly;
    cDPlayer will do so automatically"""

    def __init__(self, cdda, audio_output, command_queue):
        self.cdda = cdda
        self.audio_output = audio_output
        self.command_queue = command_queue

        self.audio_output.init(
            sample_rate=44100,
            channels=2,
            channel_mask=3,
            bits_per_sample=16)
        self.framelist_converter = self.audio_output.framelist_converter()

        self.track = None
        self.pcmconverter = None
        self.frames_played = 0
        self.total_frames = 0
        self.state = PLAYER_STOPPED

    def open(self, track_number):
        self.stop()
        self.track = self.cdda[track_number]
        self.frames_played = 0
        self.total_frames = self.track.length() * 44100 / 75

    def play(self):
        if (self.track is not None):
            if (self.state == PLAYER_STOPPED):
                if (self.pcmconverter is not None):
                    self.pcmconverter.close()
                self.pcmconverter = PCMConverter(
                    self.track,
                    self.framelist_converter)
                self.frames_played = 0
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PAUSED):
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PLAYING):
                pass

    def pause(self):
        if (self.state == PLAYER_PLAYING):
            self.state = PLAYER_PAUSED

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

    def run(self, next_track_callback=lambda: None):
        import Queue

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
                        if (frames > 0):
                            self.audio_output.play(data)
                            self.frames_played += frames
                            if (self.frames_played >= self.total_frames):
                                next_track_callback()
                        else:
                            self.frames_played = self.total_frames
                            next_track_callback()
                    else:
                        self.stop()


class PCMConverter:
    def __init__(self, pcmreader, converter):
        self.pcmreader = pcmreader
        self.converter = converter
        self.buffer_size = (pcmreader.sample_rate *
                            pcmreader.channels *
                            (pcmreader.bits_per_sample / 8)) / 20
    def read(self):
        try:
            frame = self.pcmreader.read(self.buffer_size)
            return (self.converter(frame), frame.frames)
        except (ValueError, IOError):
            return (None, 0)

    def close(self):
        self.pcmreader.close()


class AudioOutput:
    """an abstract parent class for playing audio"""

    def __init__(self):
        self.sample_rate = 0
        self.channels = 0
        self.channel_mask = 0
        self.bits_per_sample = 0
        self.initialized = False

    def compatible(self, pcmreader):
        """returns True if the given pcmreader is compatible

        if False, one is expected to open a new output stream
        which is compatible"""

        return ((self.sample_rate == pcmreader.sample_rate) and
                (self.channels == pcmreader.channels) and
                (self.channel_mask == pcmreader.channel_mask) and
                (self.bits_per_sample == pcmreader.bits_per_sample))

    def framelist_converter(self):
        """returns a function which converts framelist objects

        to objects acceptable by our play() method"""

        raise NotImplementedError()

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream

        this *must* be called prior to play() and close()
        the general flow of audio playing is:

        >>> pcm = audiofile.to_pcm()
        >>> player = AudioOutput()
        >>> player.init(pcm.sample_rate,
        ...             pcm.channels,
        ...             pcm.channel_mask,
        ...             pcm.bits_per_sample)
        >>> convert = player.framelist_converter()
        >>> frame = pcm.read(1024)
        >>> while (len(frame) > 0):
        ...     player.play(convert(frame))
        ...     frame = pcm.read(1024)
        >>> player.close()
        """

        raise NotImplementedError()

    def play(self, data):
        """plays a chunk of converted data"""

        raise NotImplementedError()

    def close(self):
        """closes the output stream"""

        raise NotImplementedError()

    @classmethod
    def available(cls):
        """returns True if the AudioOutput is available on the system"""

        return False


class NULLAudioOutput(AudioOutput):
    """an AudioOutput subclass which does not actually play anything

    although this consumes audio output at the rate it would normally
    play, it generates no output"""

    NAME = "NULL"

    def framelist_converter(self):
        """returns a function which converts framelist objects

        to objects acceptable by our play() method"""

        return lambda f: f.frames

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream

        this *must* be called prior to play() and close()"""

        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

    def play(self, data):
        """plays a chunk of converted data"""

        import time

        time.sleep(float(data) / self.sample_rate)

    def close(self):
        """closes the output stream"""

        pass

    @classmethod
    def available(cls):
        """returns True"""

        return True


class OSSAudioOutput(AudioOutput):
    """an AudioOutput subclass for OSS output"""

    NAME = "OSS"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream

        this *must* be called prior to play() and close()"""

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
        """returns a function which converts framelist objects

        to objects acceptable by our play() method"""

        if (self.bits_per_sample == 8):
            return lambda f: f.to_bytes(False, True)
        elif (self.bits_per_sample == 16):
            return lambda f: f.to_bytes(False, True)
        elif (self.bits_per_sample == 24):
            from .pcm import from_list

            return lambda f: from_list(
                [i >> 8 for i in list(f)],
                self.channels, 16, True).to_bytes(False, True)
        else:
            raise ValueError("Unsupported bits-per-sample")

    def play(self, data):
        """plays a chunk of converted data"""

        self.ossaudio.writeall(data)

    def close(self):
        """closes the output stream"""

        if (self.initialized):
            self.initialized = False
            self.ossaudio.close()

    @classmethod
    def available(cls):
        """returns True if OSS output is available on the system"""

        try:
            import ossaudiodev
            return True
        except ImportError:
            return False


class PulseAudioOutput(AudioOutput):
    """an AudioOutput subclass for PulseAudio output"""

    NAME = "PulseAudio"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream

        this *must* be called prior to play() and close()"""

        if (not self.initialized):
            import subprocess
            from . import BIN

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
                [BIN["pacat"],
                 "-n", "Python Audio Tools",
                 "--rate", str(sample_rate),
                 "--format", format,
                 "--channels", str(channels),
                 "--latency-msec", str(100)],
                stdin=subprocess.PIPE)

            self.initialized = True
        else:
            self.close()
            self.init(sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)

    def framelist_converter(self):
        """returns a function which converts framelist objects

        to objects acceptable by our play() method"""

        if (self.bits_per_sample == 8):
            return lambda f: f.to_bytes(True, False)
        elif (self.bits_per_sample == 16):
            return lambda f: f.to_bytes(False, True)
        elif (self.bits_per_sample == 24):
            return lambda f: f.to_bytes(False, True)
        else:
            raise ValueError("Unsupported bits-per-sample")

    def play(self, data):
        """plays a chunk of converted data"""

        self.pacat.stdin.write(data)
        self.pacat.stdin.flush()

    def close(self):
        """closes the output stream"""

        if (self.initialized):
            self.initialized = False
            self.pacat.stdin.close()
            self.pacat.wait()

    @classmethod
    def server_alive(cls):
        import subprocess
        from . import BIN

        dev = subprocess.Popen([BIN["pactl"], "stat"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        dev.stdout.read()
        dev.stderr.read()
        return (dev.wait() == 0)

    @classmethod
    def available(cls):
        """returns True if PulseAudio is available and running on the system"""

        from . import BIN

        return (BIN.can_execute(BIN["pacat"]) and
                BIN.can_execute(BIN["pactl"]) and
                cls.server_alive())


class CoreAudioOutput(AudioOutput):
    """an AudioOutput subclass for CoreAudio output"""

    NAME = "CoreAudio"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream

        this *must* be called prior to play() and close()"""

        if (not self.initialized):
            self.sample_rate = sample_rate
            self.channels = channels
            self.channel_mask = channel_mask
            self.bits_per_sample = bits_per_sample

            from .output import CoreAudio
            self.coreaudio = CoreAudio(sample_rate,
                                       channels,
                                       channel_mask,
                                       bits_per_sample)
            self.initialized = True
        else:
            self.close()
            self.init(sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)

    def framelist_converter(self):
        """returns a function which converts framelist objects

        to objects acceptable by our play() method"""

        return lambda f: f.to_bytes(False, True)

    def play(self, data):
        """plays a chunk of converted data"""

        self.coreaudio.play(data)

    def close(self):
        """closes the output stream"""

        if (self.initialized):
            self.initialized = False
            self.coreaudio.flush()
            self.coreaudio.close()

    @classmethod
    def available(cls):
        """returns True if the AudioOutput is available on the system"""

        try:
            from .output import CoreAudio

            return True
        except ImportError:
            return False

class PortAudioOutput(AudioOutput):
    """an AudioOutput subclass for PortAudio output"""

    NAME = "PortAudio"

    def init(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream

        this *must* be called prior to play() and close()"""

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
        """returns a function which converts framelist objects

        to objects acceptable by our play() method"""

        return lambda f: f.to_bytes(False, True)

    def play(self, data):
        """plays a chunk of converted data"""

        self.stream.write(data)

    def close(self):
        """closes the output stream"""

        if (self.initialized):
            self.stream.close()
            self.pyaudio.terminate()
            self.initialized = False

    @classmethod
    def available(cls):
        """returns True if the AudioOutput is available on the system"""

        try:
            import pyaudio
            return True
        except ImportError:
            return False

AUDIO_OUTPUT = (PulseAudioOutput,
                OSSAudioOutput,
                CoreAudioOutput,
                PortAudioOutput,
                NULLAudioOutput)
