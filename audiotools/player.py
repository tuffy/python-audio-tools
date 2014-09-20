#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


(RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN) = range(3)
DEFAULT_FORMAT = (44100, 2, 0x3, 16)

(PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING) = range(3)


class Player(object):
    """a class for operating an audio player

    the player itself runs in a seperate thread,
    which this sends commands to"""

    def __init__(self, audio_output,
                 replay_gain=RG_NO_REPLAYGAIN,
                 next_track_callback=lambda: None):
        """audio_output is an AudioOutput object

        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN,
        indicating how the player should apply ReplayGain

        next_track_callback is a function with no arguments
        which is called by the player when the current track is finished

        Raises :exc:`ValueError` if unable to start player subprocess."""

        import threading
        import Queue

        if (not isinstance(audio_output, AudioOutput)):
            raise TypeError("invalid output object")

        self.__audio_output__ = audio_output
        self.__player__ = AudioPlayer(audio_output,
                                      next_track_callback,
                                      replay_gain)
        self.__commands__ = Queue.Queue()
        self.__responses__ = Queue.Queue()

        self.__thread__ = threading.Thread(
            target=self.__player__.run,
            kwargs={"commands": self.__commands__,
                    "responses": self.__responses__})
        self.__thread__.daemon = False
        self.__thread__.start()

    def open(self, track):
        """opens the given AudioFile for playing

        stops playing the current file, if any"""

        self.__commands__.put(("open", (track,)))

    def play(self):
        """begins or resumes playing an opened AudioFile, if any"""

        self.__commands__.put(("play", tuple()))

    def set_replay_gain(self, replay_gain):
        """sets the given ReplayGain level to apply during playback

        choose from RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN
        replayGain cannot be applied mid-playback
        one must stop() and play() a file for it to take effect"""

        self.__commands__.put(("set_replay_gain", (replay_gain,)))

    def set_output(self, output):
        """given an AudioOutput object,
        sets the player's output to that device

        any currently playing audio is stopped"""

        self.__audio_output__ = output
        self.__commands__.put(("set_output", (output,)))

    def pause(self):
        """pauses playback of the current file

        playback may be resumed with play() or toggle_play_pause()"""

        self.__commands__.put(("pause", tuple()))

    def toggle_play_pause(self):
        """pauses the file if playing, play the file if paused"""

        self.__commands__.put(("toggle_play_pause", tuple()))

    def stop(self):
        """stops playback of the current file

        if play() is called, playback will start from the beginning"""

        self.__commands__.put(("stop", tuple()))

    def state(self):
        """returns the current state of the Player
        as either PLAYER_STOPPED, PLAYER_PAUSED, or PLAYER_PLAYING ints"""

        return self.__player__.state()

    def close(self):
        """closes the player for playback

        the player thread is halted and the AudioOutput is closed"""

        self.__commands__.put(("close", tuple()))

    def progress(self):
        """returns a (pcm_frames_played, pcm_frames_total) tuple

        this indicates the current playback status in PCM frames"""

        return self.__player__.progress()

    def current_output_description(self):
        """returns the human-readable description of the current output device
        as a Unicode string"""

        return self.__audio_output__.description()

    def current_output_name(self):
        """returns the ``NAME`` attribute of the current output device
        as a plain string"""

        return self.__audio_output__.NAME

    def get_volume(self):
        """returns the current volume level as a floating point value
        between 0.0 and 1.0, inclusive"""

        return self.__audio_output__.get_volume()

    def set_volume(self, volume):
        """given a floating point value between 0.0 and 1.0, inclusive,
        sets the current volume level to that value"""

        self.__audio_output__.set_volume(volume)

    def change_volume(self, delta):
        """changes the volume by the given floating point amount
        where delta may be positive or negative
        and returns the new volume as a floating point value"""

        self.__audio_output__.set_volume(
            min(max(self.__audio_output__.get_volume() + delta, 0.0), 1.0))
        return self.__audio_output__.get_volume()


class AudioPlayer(object):
    def __init__(self, audio_output,
                 next_track_callback=lambda: None,
                 replay_gain=RG_NO_REPLAYGAIN):
        """audio_output is an AudioOutput object to play audio to

        next_track_callback is an optional function which
        is called with no arguments when the current track is finished"""

        self.__state__ = PLAYER_STOPPED
        self.__audio_output__ = audio_output
        self.__next_track_callback__ = next_track_callback
        self.__audiofile__ = None
        self.__pcmreader__ = None
        self.__buffer_size__ = 1
        self.__replay_gain__ = replay_gain
        self.__current_frames__ = 0
        self.__total_frames__ = 1

    def set_audiofile(self, audiofile):
        """sets audiofile to play"""

        self.__audiofile__ = audiofile

    def state(self):
        """returns current state of player which is one of:
        PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING"""

        return self.__state__

    def progress(self):
        """returns current progress
        as a (current frames, total frames) tuple"""

        return (self.__current_frames__, self.__total_frames__)

    def stop(self):
        """changes current state of player to PLAYER_STOPPED"""

        if (self.__state__ == PLAYER_STOPPED):
            # already stopped, so nothing to do
            return
        else:
            if (self.__state__ == PLAYER_PAUSED):
                self.__audio_output__.resume()

            self.__state__ = PLAYER_STOPPED
            self.__pcmreader__ = None
            self.__current_frames__ = 0
            self.__total_frames__ = 1

    def pause(self):
        """if playing, changes current state of player to PLAYER_PAUSED"""

        # do nothing if player is stopped or already paused
        if (self.__state__ == PLAYER_PLAYING):
            self.__audio_output__.pause()
            self.__state__ = PLAYER_PAUSED

    def play(self):
        """if audiofile has been opened,
        changes current state of player to PLAYER_PLAYING"""

        from audiotools import BufferedPCMReader

        if (self.__state__ == PLAYER_PLAYING):
            # already playing, so nothing to do
            return
        elif (self.__state__ == PLAYER_PAUSED):
            # go from unpaused to playing
            self.__audio_output__.resume()
            self.__state__ = PLAYER_PLAYING
        elif ((self.__state__ == PLAYER_STOPPED) and
              (self.__audiofile__ is not None)):
            # go from stopped to playing
            # if an audiofile has been opened

            # get PCMReader from selected audiofile
            pcmreader = self.__audiofile__.to_pcm()

            # apply ReplayGain if requested
            if (self.__replay_gain__ in (RG_TRACK_GAIN, RG_ALBUM_GAIN)):
                gain = self.__audiofile__.get_replay_gain()
                if (gain is not None):
                    from audiotools.replaygain import ReplayGainReader

                    if (self.__replay_gain__ == RG_TRACK_GAIN):
                        pcmreader = ReplayGainReader(pcmreader,
                                                     gain.track_gain,
                                                     gain.track_peak)
                    else:
                        pcmreader = ReplayGainReader(pcmreader,
                                                     gain.album_gain,
                                                     gain.album_peak)

            # buffer PCMReader so that one can process small chunks of data
            self.__pcmreader__ = BufferedPCMReader(pcmreader)

            # calculate quarter second buffer size
            # (or at least 256 samples)
            self.__buffer_size__ = max(int(round(0.25 *
                                                 pcmreader.sample_rate)),
                                       256)

            # set output to be compatible with PCMReader
            self.__audio_output__.set_format(
                sample_rate=self.__pcmreader__.sample_rate,
                channels=self.__pcmreader__.channels,
                channel_mask=self.__pcmreader__.channel_mask,
                bits_per_sample=self.__pcmreader__.bits_per_sample)

            # reset progress
            self.__current_frames__ = 0
            self.__total_frames__ = self.__audiofile__.total_frames()

            # update state so audio begins playing
            self.__state__ = PLAYER_PLAYING

    def output_audio(self):
        """if player is playing, output the next chunk of audio if possible

        if audio is exhausted, stop playing and call the next_track callback"""

        if (self.__state__ == PLAYER_PLAYING):
            try:
                frame = self.__pcmreader__.read(self.__buffer_size__)
            except (IOError, ValueError) as err:
                # some sort of read error occurred
                # so cease playing file and move on to next
                self.stop()
                if (callable(self.__next_track_callback__)):
                    self.__next_track_callback__()
                return

            if (len(frame) > 0):
                self.__current_frames__ += frame.frames
                self.__audio_output__.play(frame)
            else:
                # audio has been exhausted
                self.stop()
                if (callable(self.__next_track_callback__)):
                    self.__next_track_callback__()

    def run(self, commands, responses):
        """runs the audio playing thread while accepting commands
        from the given Queue"""

        from Queue import Empty

        while (True):
            try:
                (command,
                 args) = commands.get(self.__state__ != PLAYER_PLAYING)
                # got a command to process
                if (command == "open"):
                    # stop whatever's playing and prepare new track for playing
                    self.stop()
                    self.set_audiofile(args[0])
                elif (command == "play"):
                    self.play()
                elif (command == "set_replay_gain"):
                    self.__replay_gain__ = args[0]
                elif (command == "set_output"):
                    # resume (if necessary) and close existing output
                    if (self.__state__ == PLAYER_PAUSED):
                        self.__audio_output__.resume()
                    self.__audio_output__.close()

                    # set new output and set format (if necessary)
                    self.__audio_output__ = args[0]
                    if (self.__pcmreader__ is not None):
                        self.__audio_output__.set_format(
                            sample_rate=self.__pcmreader__.sample_rate,
                            channels=self.__pcmreader__.channels,
                            channel_mask=self.__pcmreader__.channel_mask,
                            bits_per_sample=self.__pcmreader__.bits_per_sample)

                    # if paused, reset audio output to paused
                    if (self.__state__ == PLAYER_PAUSED):
                        self.__audio_output__.pause()
                elif (command == "pause"):
                    self.pause()
                elif (command == "toggle_play_pause"):
                    # switch from paused to playing or playing to paused
                    if (self.__state__ == PLAYER_PAUSED):
                        self.play()
                    elif (self.__state__ == PLAYER_PLAYING):
                        self.pause()
                elif (command == "stop"):
                    self.stop()
                    self.__audio_output__.close()
                elif (command == "close"):
                    self.stop()
                    self.__audio_output__.close()
                    return
            except Empty:
                # no commands to process
                # so output audio if playing
                self.output_audio()


class CDPlayer(Player):
    def __init__(self, cddareader, audio_output,
                 next_track_callback=lambda: None):
        """cdda is a CDDAReader object

        audio_output is an AudioOutput object

        next_track_callback is a function with no arguments
        which is called by the player when the current track is finished"""

        import threading
        import Queue

        if (not isinstance(audio_output, AudioOutput)):
            raise TypeError("invalid output object")

        self.__audio_output__ = audio_output
        self.__player__ = CDAudioPlayer(cddareader,
                                        audio_output,
                                        next_track_callback)
        self.__commands__ = Queue.Queue()
        self.__responses__ = Queue.Queue()

        self.__thread__ = threading.Thread(
            target=self.__player__.run,
            kwargs={"commands": self.__commands__,
                    "responses": self.__responses__})
        self.__thread__.daemon = False
        self.__thread__.start()

    def open(self, track_number):
        """opens the given track_number for playing

        stops playing the current track, if any"""

        self.__commands__.put(("open", (track_number,)))

    def set_replay_gain(self, replay_gain):
        """ReplayGain not applicable to CDDA, so this does nothing"""

        pass


class CDAudioPlayer(AudioPlayer):
    def __init__(self, cddareader, audio_output,
                 next_track_callback=lambda: None):
        """cdda is a CDDAReader object to play tracks from

        audio_output is an AudioOutput object to play audio to

        next_track_callback is an optional function
        which is called with no arguments when the current track is finished"""

        self.__state__ = PLAYER_STOPPED
        self.__audio_output__ = audio_output
        self.__next_track_callback__ = next_track_callback
        self.__cddareader__ = cddareader
        self.__offsets__ = cddareader.track_offsets
        self.__lengths__ = cddareader.track_lengths
        self.__track_number__ = None
        self.__pcmreader__ = None
        self.__buffer_size__ = 1
        self.__replay_gain__ = RG_NO_REPLAYGAIN
        self.__current_frames__ = 0
        self.__total_frames__ = 1

    def set_audiofile(self, track_number):
        """set tracks number to play"""

        # ensure track number is in the proper range
        if (track_number in self.__offsets__.keys()):
            self.__track_number__ = track_number

    def play(self):
        """if track has been selected,
        changes current state of player to PLAYER_PLAYING"""

        from audiotools import BufferedPCMReader, PCMReaderHead

        if (self.__state__ == PLAYER_PLAYING):
            # already playing, so nothing to do
            return
        elif (self.__state__ == PLAYER_PAUSED):
            # go from unpaused to playing
            self.__audio_output__.resume()
            self.__state__ = PLAYER_PLAYING
        elif ((self.__state__ == PLAYER_STOPPED) and
              (self.__track_number__ is not None)):
            # go from stopped to playing
            # if a track number has been selected

            # seek to specified track number
            self.__cddareader__.seek(self.__offsets__[self.__track_number__])
            track = PCMReaderHead(self.__cddareader__,
                                  self.__lengths__[self.__track_number__],
                                  False)

            # decode PCMReader in thread
            # and place in buffer so one can process small chunks of data
            self.__pcmreader__ = BufferedPCMReader(ThreadedPCMReader(track))

            # calculate quarter second buffer size
            self.__buffer_size__ = int(round(0.25 * 44100))

            # set output to be compatible with PCMReader
            self.__audio_output__.set_format(
                sample_rate=44100,
                channels=2,
                channel_mask=0x3,
                bits_per_sample=16)

            # reset progress
            self.__current_frames__ = 0
            self.__total_frames__ = self.__lengths__[self.__track_number__]

            # update state so audio begins playing
            self.__state__ = PLAYER_PLAYING


class ThreadedPCMReader(object):
    """a PCMReader which decodes all output in the background

    It will queue *all* output from its contained PCMReader
    as fast as possible in a separate thread.
    This may be a problem if PCMReader's total output is very large
    or has no upper bound.
    """

    def __init__(self, pcmreader):
        from Queue import Queue
        from threading import (Thread, Event)

        def transfer_data(read, queue, stop_event):
            try:
                frame = read(4096)
            except ValueError:
                return

            while (not stop_event.is_set()):
                # want to be sure to put 0 length frame in queue
                # if reading is intended to continue
                queue.put(frame)
                if (len(frame) > 0):
                    try:
                        frame = read(4096)
                    except ValueError:
                        break
                else:
                    break

        self.__pcmreader_close__ = pcmreader.close
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample

        self.__queue__ = Queue()
        self.__stop_event__ = Event()
        self.__thread__ = Thread(target=transfer_data,
                                 args=(pcmreader.read,
                                       self.__queue__,
                                       self.__stop_event__))
        self.__thread__.daemon = True
        self.__thread__.start()
        self.__last_frame__ = None
        self.__finished__ = False

    def read(self, pcm_frames):
        if (not self.__finished__):
            frame = self.__queue__.get()
            if (len(frame) > 0):
                return frame
            else:
                self.__last_frame__ = frame
                self.__finished__ = True
                return frame
        else:
            return self.__last_frame__

    def __del__(self):
        self.__stop_event__.set()
        self.__thread__.join()

    def close(self):
        self.__pcmreader_close__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class AudioOutput(object):
    """an abstract parent class for playing audio"""

    def __init__(self):
        self.sample_rate = None
        self.channels = None
        self.channel_mask = None
        self.bits_per_sample = None

    def __getstate__(self):
        """gets internal state for use by Pickle module"""

        return ""

    def __setstate__(self, name):
        """sets internal state for use by Pickle module"""

        # audio outputs are initialized closed for obvious reasons
        self.sample_rate = None
        self.channels = None
        self.channel_mask = None
        self.bits_per_sample = None

    def description(self):
        """returns user-facing name of output device as unicode"""

        raise NotImplementedError()

    def compatible(self, sample_rate, channels, channel_mask, bits_per_sample):
        """returns True if the given pcmreader is compatible
        with the given format"""

        return ((self.sample_rate == sample_rate) and
                (self.channels == channels) and
                (self.channel_mask == channel_mask) and
                (self.bits_per_sample == bits_per_sample))

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """sets the output stream to the given format

        if the stream hasn't been initialized, this method initializes it

        if the stream has been initialized to a different format,
        this method closes and reopens the stream to the new format

        if the stream has been initialized to the same format,
        this method does nothing"""

        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

    def play(self, framelist):
        """plays a FrameList"""

        raise NotImplementedError()

    def pause(self):
        """pauses audio output, with the expectation it will be resumed"""

        raise NotImplementedError()

    def resume(self):
        """resumes playing paused audio output"""

        raise NotImplementedError()

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        return 0.0

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        pass

    def close(self):
        """closes the output stream"""

        self.sample_rate = None
        self.channels = None
        self.channel_mask = None
        self.bits_per_sample = None

    @classmethod
    def available(cls):
        """returns True if the AudioOutput is available on the system"""

        return False


class NULLAudioOutput(AudioOutput):
    """an AudioOutput subclass which does not actually play anything

    although this consumes audio output at the rate it would normally
    play, it generates no output"""

    NAME = "NULL"

    def __init__(self):
        self.__volume__ = 0.30
        AudioOutput.__init__(self)

    def __getstate__(self):
        return "NULL"

    def __setstate__(self, name):
        AudioOutput.__setstate__(self, name)
        self.__volume__ = 0.30

    def description(self):
        """returns user-facing name of output device as unicode"""

        return u"Dummy Output"

    def play(self, framelist):
        """plays a chunk of converted data"""

        import time

        time.sleep(float(framelist.frames) / self.sample_rate)

    def pause(self):
        """pauses audio output, with the expectation it will be resumed"""

        pass

    def resume(self):
        """resumes playing paused audio output"""

        pass

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        return self.__volume__

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            self.__volume__ = volume
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

        AudioOutput.close(self)

    @classmethod
    def available(cls):
        """returns True"""

        return True


class OSSAudioOutput(AudioOutput):
    """an AudioOutput subclass for OSS output"""

    NAME = "OSS"

    def __init__(self):
        """automatically initializes output format for playing
        CD quality audio"""

        self.__ossaudio__ = None
        self.__ossmixer__ = None
        AudioOutput.__init__(self)

    def __getstate__(self):
        """gets internal state for use by Pickle module"""

        return "OSS"

    def __setstate__(self, name):
        """sets internal state for use by Pickle module"""

        AudioOutput.__setstate__(self, name)
        self.__ossaudio__ = None
        self.__ossmixer__ = None

    def description(self):
        """returns user-facing name of output device as unicode"""

        return u"Open Sound System"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """sets the output stream to the given format

        if the stream hasn't been initialized, this method initializes it

        if the stream has been initialized to a different format,
        this method closes and reopens the stream to the new format

        if the stream has been initialized to the same format,
        this method does nothing"""

        if (self.__ossaudio__ is None):
            # output hasn't been initialized

            import ossaudiodev

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            # initialize audio output device and setup framelist converter
            self.__ossaudio__ = ossaudiodev.open('w')
            self.__ossmixer__ = ossaudiodev.openmixer()
            if (self.bits_per_sample == 8):
                self.__ossaudio__.setfmt(ossaudiodev.AFMT_S8_LE)
                self.__converter__ = lambda f: f.to_bytes(False, True)
            elif (self.bits_per_sample == 16):
                self.__ossaudio__.setfmt(ossaudiodev.AFMT_S16_LE)
                self.__converter__ = lambda f: f.to_bytes(False, True)
            elif (self.bits_per_sample == 24):
                from audiotools.pcm import from_list

                self.__ossaudio__.setfmt(ossaudiodev.AFMT_S16_LE)
                self.__converter__ = lambda f: from_list(
                    [i >> 8 for i in list(f)],
                    self.channels, 16, True).to_bytes(False, True)
            else:
                raise ValueError("Unsupported bits-per-sample")

            self.__ossaudio__.channels(channels)
            self.__ossaudio__.speed(sample_rate)
        elif (not self.compatible(sample_rate=sample_rate,
                                  channels=channels,
                                  channel_mask=channel_mask,
                                  bits_per_sample=bits_per_sample)):
            # output has been initialized to a different format

            self.close()
            self.set_format(sample_rate=sample_rate,
                            channels=channels,
                            channel_mask=channel_mask,
                            bits_per_sample=bits_per_sample)

    def play(self, framelist):
        """plays a FrameList"""

        self.__ossaudio__.writeall(self.__converter__(framelist))

    def pause(self):
        """pauses audio output, with the expectation it will be resumed"""

        pass

    def resume(self):
        """resumes playing paused audio output"""

        pass

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        import ossaudiodev

        if (self.__ossmixer__ is None):
            self.set_format(*DEFAULT_FORMAT)

        controls = self.__ossmixer__.controls()
        for control in (ossaudiodev.SOUND_MIXER_VOLUME,
                        ossaudiodev.SOUND_MIXER_PCM):
            if (controls & (1 << control)):
                try:
                    volumes = self.__ossmixer__.get(control)
                    return (sum(volumes) / float(len(volumes))) / 100.0
                except ossaudiodev.OSSAudioError:
                    continue
        else:
            return 0.0

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            if (self.__ossmixer__ is None):
                self.set_format(*DEFAULT_FORMAT)

            controls = self.__ossmixer__.controls()
            ossvolume = max(min(int(round(volume * 100)), 100), 0)
            for control in (ossaudiodev.SOUND_MIXER_VOLUME,
                            ossaudiodev.SOUND_MIXER_PCM):
                if (controls & (1 << control)):
                    try:
                        self.__ossmixer__.set(control, (ossvolume, ossvolume))
                    except ossaudiodev.OSSAudioError:
                        continue
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

        AudioOutput.close(self)

        if (self.__ossaudio__ is not None):
            self.__ossaudio__.close()
            self.__ossaudio__ = None
        if (self.__ossmixer__ is not None):
            self.__ossmixer__.close()
            self.__ossmixer__ = None

    @classmethod
    def available(cls):
        """returns True if OSS output is available on the system"""

        try:
            import ossaudiodev
            ossaudiodev.open("w").close()
            return True
        except (ImportError, IOError):
            return False


class PulseAudioOutput(AudioOutput):
    """an AudioOutput subclass for PulseAudio output"""

    NAME = "PulseAudio"

    def __init__(self):
        self.__pulseaudio__ = None
        AudioOutput.__init__(self)

    def __getstate__(self):
        """gets internal state for use by Pickle module"""

        return "PulseAudio"

    def __setstate__(self, name):
        """sets internal state for use by Pickle module"""

        AudioOutput.__setstate__(self, name)
        self.__pulseaudio__ = None

    def description(self):
        """returns user-facing name of output device as unicode"""

        # FIXME - pull this from device description
        return u"Pulse Audio"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """sets the output stream to the given format

        if the stream hasn't been initialized, this method initializes it

        if the stream has been initialized to a different format,
        this method closes and reopens the stream to the new format

        if the stream has been initialized to the same format,
        this method does nothing"""

        if (self.__pulseaudio__ is None):
            # output hasn't been initialized

            from audiotools.output import PulseAudio

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            self.__pulseaudio__ = PulseAudio(sample_rate,
                                             channels,
                                             bits_per_sample,
                                             "Python Audio Tools")
            self.__converter__ = {
                8: lambda f: f.to_bytes(True, False),
                16: lambda f: f.to_bytes(False, True),
                24: lambda f: f.to_bytes(False, True)}[self.bits_per_sample]
        elif (not self.compatible(sample_rate=sample_rate,
                                  channels=channels,
                                  channel_mask=channel_mask,
                                  bits_per_sample=bits_per_sample)):
            # output has been initialized to a different format

            self.close()
            self.set_format(sample_rate=sample_rate,
                            channels=channels,
                            channel_mask=channel_mask,
                            bits_per_sample=bits_per_sample)

    def play(self, framelist):
        """plays a FrameList"""

        self.__pulseaudio__.play(self.__converter__(framelist))

    def pause(self):
        """pauses audio output, with the expectation it will be resumed"""

        if (self.__pulseaudio__ is not None):
            self.__pulseaudio__.pause()

    def resume(self):
        """resumes playing paused audio output"""

        if (self.__pulseaudio__ is not None):
            self.__pulseaudio__.resume()

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        if (self.__pulseaudio__ is None):
            self.set_format(*DEFAULT_FORMAT)

        return self.__pulseaudio__.get_volume()

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            if (self.__pulseaudio__ is None):
                self.set_format(*DEFAULT_FORMAT)

            self.__pulseaudio__.set_volume(volume)
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

        AudioOutput.close(self)

        if (self.__pulseaudio__ is not None):
            self.__pulseaudio__.flush()
            self.__pulseaudio__.close()
            self.__pulseaudio__ = None

    @classmethod
    def available(cls):
        """returns True if PulseAudio is available and running on the system"""

        try:
            from audiotools.output import PulseAudio

            return True
        except ImportError:
            return False


class ALSAAudioOutput(AudioOutput):
    """an AudioOutput subclass for ALSA output"""

    NAME = "ALSA"

    def __init__(self):
        self.__alsaaudio__ = None
        AudioOutput.__init__(self)

    def __getstate__(self):
        """gets internal state for use by Pickle module"""

        return "ALSA"

    def __setstate__(self, name):
        """sets internal state for use by Pickle module"""

        AudioOutput.__setstate__(self, name)
        self.__alsaaudio__ = None

    def description(self):
        """returns user-facing name of output device as unicode"""

        # FIXME - pull this from device description
        return u"Advanced Linux Sound Architecture"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """sets the output stream to the given format

        if the stream hasn't been initialized, this method initializes it

        if the stream has been initialized to a different format,
        this method closes and reopens the stream to the new format

        if the stream has been initialized to the same format,
        this method does nothing"""

        if (self.__alsaaudio__ is None):
            # output hasn't been initialized

            from audiotools.output import ALSAAudio

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            self.__alsaaudio__ = ALSAAudio("default",
                                           sample_rate,
                                           channels,
                                           bits_per_sample)
        elif (not self.compatible(sample_rate=sample_rate,
                                  channels=channels,
                                  channel_mask=channel_mask,
                                  bits_per_sample=bits_per_sample)):
            # output has been initialized to different format

            self.close()
            self.set_format(sample_rate=sample_rate,
                            channels=channels,
                            channel_mask=channel_mask,
                            bits_per_sample=bits_per_sample)

    def play(self, framelist):
        """plays a FrameList"""

        self.__alsaaudio__.play(framelist)

    def pause(self):
        """pauses audio output, with the expectation it will be resumed"""

        if (self.__alsaaudio__ is not None):
            self.__alsaaudio__.pause()

    def resume(self):
        """resumes playing paused audio output"""

        if (self.__alsaaudio__ is not None):
            self.__alsaaudio__.resume()

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        if (self.__alsaaudio__ is None):
            self.set_format(*DEFAULT_FORMAT)
        return self.__alsaaudio__.get_volume()

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            if (self.__alsaaudio__ is None):
                self.set_format(*DEFAULT_FORMAT)
            self.__alsaaudio__.set_volume(volume)
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

        AudioOutput.close(self)

        if (self.__alsaaudio__ is not None):
            self.__alsaaudio__.flush()
            self.__alsaaudio__.close()
            self.__alsaaudio__ = None

    @classmethod
    def available(cls):
        """returns True if ALSA is available and running on the system"""

        try:
            from audiotools.output import ALSAAudio

            return True
        except ImportError:
            return False


class CoreAudioOutput(AudioOutput):
    """an AudioOutput subclass for CoreAudio output"""

    NAME = "CoreAudio"

    def __init__(self):
        self.__coreaudio__ = None
        AudioOutput.__init__(self)

    def __getstate__(self):
        """gets internal state for use by Pickle module"""

        return "CoreAudio"

    def __setstate__(self, name):
        """sets internal state for use by Pickle module"""

        AudioOutput.__setstate__(self, name)
        self.__coreaudio__ = None

    def description(self):
        """returns user-facing name of output device as unicode"""

        # FIXME - pull this from device description
        return u"Core Audio"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """sets the output stream to the given format

        if the stream hasn't been initialized, this method initializes it

        if the stream has been initialized to a different format,
        this method closes and reopens the stream to the new format

        if the stream has been initialized to the same format,
        this method does nothing"""

        if (self.__coreaudio__ is None):
            # output hasn't been initialized

            from audiotools.output import CoreAudio

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            self.__coreaudio__ = CoreAudio(sample_rate,
                                           channels,
                                           channel_mask,
                                           bits_per_sample)
        elif (not self.compatible(sample_rate=sample_rate,
                                  channels=channels,
                                  channel_mask=channel_mask,
                                  bits_per_sample=bits_per_sample)):
            # output has been initialized in a different format

            self.close()
            self.set_format(sample_rate=sample_rate,
                            channels=channels,
                            channel_mask=channel_mask,
                            bits_per_sample=bits_per_sample)

    def play(self, framelist):
        """plays a FrameList"""

        self.__coreaudio__.play(framelist.to_bytes(False, True))

    def pause(self):
        """pauses audio output, with the expectation it will be resumed"""

        if (self.__coreaudio__ is not None):
            self.__coreaudio__.pause()

    def resume(self):
        """resumes playing paused audio output"""

        if (self.__coreaudio__ is not None):
            self.__coreaudio__.resume()

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        if (self.__coreaudio__ is None):
            self.set_format(*DEFAULT_FORMAT)
        try:
            return self.__coreaudio__.get_volume()
        except ValueError:
            # get_volume_scalar() call was unsuccessful
            return 1.0

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            if (self.__coreaudio__ is None):
                self.set_format(*DEFAULT_FORMAT)
            try:
                self.__coreaudio__.set_volume(volume)
            except ValueError:
                # set_volume_scalar() call was unsuccessful
                pass
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

        AudioOutput.close(self)

        if (self.__coreaudio__ is not None):
            self.__coreaudio__.flush()
            self.__coreaudio__.close()
            self.__coreaudio__ = None

    @classmethod
    def available(cls):
        """returns True if the AudioOutput is available on the system"""

        try:
            from audiotools.output import CoreAudio

            return True
        except ImportError:
            return False


def available_outputs():
    """iterates over all available AudioOutput objects
    this will always yield at least one output"""

    if (PulseAudioOutput.available()):
        yield PulseAudioOutput()

    if (ALSAAudioOutput.available()):
        yield ALSAAudioOutput()

    if (CoreAudioOutput.available()):
        yield CoreAudioOutput()

    if (OSSAudioOutput.available()):
        yield OSSAudioOutput()

    yield NULLAudioOutput()


def open_output(output):
    """given an output type string (e.g. "PulseAudio")
    returns that AudioOutput instance
    or raises ValueError if it is unavailable"""

    for audio_output in available_outputs():
        if (audio_output.NAME == output):
            return audio_output
    else:
        raise ValueError("no such outout %s" % (output))
