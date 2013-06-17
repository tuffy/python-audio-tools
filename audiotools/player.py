#!/usr/bin/bin

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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


import cPickle

(RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN) = range(3)
DEFAULT_FORMAT = (44100, 2, 0x3, 16)

class Player:
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

        from multiprocessing import Process, Array, Value, Pipe
        from threading import Thread

        self.__player__ = None

        if (not isinstance(audio_output, AudioOutput)):
            raise TypeError("invalid output object")

        def call_next_track(next_track_conn, next_track_callback):
            response = next_track_conn.recv()
            while (response):
                next_track_callback()
                response = next_track_conn.recv()
            next_track_conn.close()

        (self.__command_conn__, client_conn) = Pipe(True)
        (server_next_track_conn, client_next_track_conn) = Pipe(False)
        self.__state__ = Value("i", 0)
        self.__progress__ = Array("I", [0, 0])

        thread = Thread(target=call_next_track,
                        args=(server_next_track_conn, next_track_callback))
        thread.daemon = True
        thread.start()

        self.__player__ = Process(
            target=PlayerProcess.run,
            kwargs={"audio_output":audio_output,
                    "command_conn":client_conn,
                    "next_track_conn":client_next_track_conn,
                    "state":self.__state__,
                    "current_progress":self.__progress__,
                    "replay_gain":replay_gain})

        self.__player__.start()

    def __del__(self):
        if (self.__player__ is not None):
            self.__command_conn__.send(("exit", tuple(), False))
            self.__command_conn__.close()
            self.__player__.join()
            self.__player__ = None

    def open(self, track):
        """opens the given AudioFile for playing

        stops playing the current file, if any"""

        self.__command_conn__.send(("open", (track,), True))
        return self.__command_conn__.recv()

    def play(self):
        """begins or resumes playing an opened AudioFile, if any"""

        self.__command_conn__.send(("play", tuple(), True))
        return self.__command_conn__.recv()

    def set_replay_gain(self, replay_gain):
        """sets the given ReplayGain level to apply during playback

        choose from RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN
        replayGain cannot be applied mid-playback
        one must stop() and play() a file for it to take effect"""

        self.__command_conn__.send(("set_replay_gain", (replay_gain,), True))
        return self.__command_conn__.recv()

    def set_output(self, output):
        """given an AudioOutput object,
        sets the player's output to that device

        any currently playing audio is stopped"""

        if (not isinstance(output, AudioOutput)):
            raise TypeError("invalid output object")
        self.__command_conn__.send(("set_output", (output,), True))
        return self.__command_conn__.recv()

    def pause(self):
        """pauses playback of the current file

        playback may be resumed with play() or toggle_play_pause()"""

        self.__command_conn__.send(("pause", tuple(), True))
        return self.__command_conn__.recv()

    def toggle_play_pause(self):
        """pauses the file if playing, play the file if paused"""

        self.__command_conn__.send(("toggle_play_pause", tuple(), True))
        return self.__command_conn__.recv()

    def stop(self):
        """stops playback of the current file

        if play() is called, playback will start from the beginning"""

        self.__command_conn__.send(("stop_playing", tuple(), True))
        return self.__command_conn__.recv()

    def state(self):
        """returns the current state of the Player
        as either PLAYER_STOPPED, PLAYER_PAUSED, or PLAYER_PLAYING ints"""

        return self.__state__.value

    def close(self):
        """closes the player for playback

        the player thread is halted and the AudioOutput is closed"""

        self.__command_conn__.send(("close", tuple(), True))
        response = self.__command_conn__.recv()
        if (self.__player__ is not None):
            self.__command_conn__.send(("exit", tuple(), False))
            self.__command_conn__.close()
            self.__player__.join()
            self.__player__ = None
        return response

    def progress(self):
        """returns a (pcm_frames_played, pcm_frames_total) tuple

        this indicates the current playback status in PCM frames"""

        return tuple(self.__progress__)

    def current_output_description(self):
        """returns the human-readable description of the current output device
        as a Unicode string"""

        self.__command_conn__.send(("current_output_description",
                                    tuple(),
                                    True))
        return self.__command_conn__.recv()

    def current_output_name(self):
        """returns the ``NAME`` attribute of the current output device
        as a plain string"""

        self.__command_conn__.send(("current_output_name",
                                    tuple(),
                                    True))
        return self.__command_conn__.recv()

    def get_volume(self):
        """returns the current volume level as a floating point value
        between 0.0 and 1.0, inclusive"""

        self.__command_conn__.send(("get_volume", tuple(), True))
        return self.__command_conn__.recv()

    def set_volume(self, volume):
        """given a floating point value between 0.0 and 1.0, inclusive,
        sets the current volume level to that value"""

        self.__command_conn__.send(("set_volume", (volume,), False))


(PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING) = range(3)


class PlayerProcess:
    """the Player class' subprocess

    this should not be instantiated directly;
    player will do so automatically"""

    BUFFER_SIZE = 0.25  # in seconds

    def __init__(self, audio_output,
                 state,
                 progress,
                 next_track_conn,
                 replay_gain=RG_NO_REPLAYGAIN):
        """audio_output is an AudioOutput object

        state is a shared Value of the current processing state

        progress is a shared Array of current frames / total frames

        next_track_conn is a Connection object
        to be sent an object when the current track ends

        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN, or RG_ALBUM_GAIN
        """

        self.__track__ = None          # the currently playing AudioFile
        self.__pcmreader__ = None      # the currently playing PCMReader

        # an AudioOutput subclass
        self.__audio_output__ = audio_output
        self.__buffer_size__ = 0       # the number of PCM frames to process

        self.__state__ = state
        self.__state__.value = PLAYER_STOPPED
        self.__progress__ = progress   #an Array of current/total frames

        self.set_progress(0, 1)

        self.__next_track_conn__ = next_track_conn

        self.__replay_gain__ = replay_gain  # the sort of ReplayGain to apply

    def open(self, track):
        self.stop_playing()
        self.__track__ = track

    def close(self):
        self.stop_playing()
        self.__audio_output__.close()

    def pause(self):
        if (self.__state__.value == PLAYER_PLAYING):
            self.__audio_output__.pause()
            self.__state__.value = PLAYER_PAUSED

    def play(self):
        if (self.__track__ is not None):
            if (self.__state__.value == PLAYER_STOPPED):
                self.start_playing()
            elif (self.__state__.value == PLAYER_PAUSED):
                self.__audio_output__.resume()
                self.__state__.value = PLAYER_PLAYING
            elif (self.__state__.value == PLAYER_PLAYING):
                pass

    def set_replay_gain(self, replay_gain):
        self.__replay_gain__ = replay_gain

    def set_output(self, output):
        self.stop_playing()
        try:
            self.__audio_output__ = output
            self.__buffer_size__ = 0
            return True
        except ValueError:
            return False

    def toggle_play_pause(self):
        if (self.__state__.value == PLAYER_PLAYING):
            self.pause()
        elif ((self.__state__.value == PLAYER_PAUSED) or
              (self.__state__.value == PLAYER_STOPPED)):
            self.play()

    def current_output_name(self):
        return self.__audio_output__.NAME

    def current_output_description(self):
        return self.__audio_output__.description()

    def get_volume(self):
        return self.__audio_output__.get_volume()

    def set_volume(self, volume):
        return self.__audio_output__.set_volume(volume)

    def start_playing(self):
        from . import BufferedPCMReader

        #construct pcmreader from track
        #depending on whether ReplayGain is set
        if (self.__replay_gain__ == RG_TRACK_GAIN):
            from .replaygain import ReplayGainReader
            replay_gain = self.__track__.replay_gain()

            if (replay_gain is not None):
                pcmreader = ReplayGainReader(
                    self.__track__.to_pcm(),
                    replay_gain.track_gain,
                    replay_gain.track_peak)
            else:
                pcmreader = self.__track__.to_pcm()
        elif (self.__replay_gain__ == RG_ALBUM_GAIN):
            from .replaygain import ReplayGainReader
            replay_gain = self.__track__.replay_gain()

            if (replay_gain is not None):
                pcmreader = ReplayGainReader(
                    self.__track__.to_pcm(),
                    replay_gain.album_gain,
                    replay_gain.album_peak)
            else:
                pcmreader = self.__track__.to_pcm()
        else:
            pcmreader = self.__track__.to_pcm()

        pcmreader = BufferedPCMReader(pcmreader)

        #reopen AudioOutput if necessary based on file's parameters
        if (not self.__audio_output__.compatible(
                sample_rate=pcmreader.sample_rate,
                channels=pcmreader.channels,
                channel_mask=pcmreader.channel_mask,
                bits_per_sample=pcmreader.bits_per_sample)):
            self.__audio_output__.set_format(
                sample_rate=pcmreader.sample_rate,
                channels=pcmreader.channels,
                channel_mask=pcmreader.channel_mask,
                bits_per_sample=pcmreader.bits_per_sample)

        self.__pcmreader__ = pcmreader
        self.__buffer_size__ = min(round(self.BUFFER_SIZE *
                                         self.__track__.sample_rate()), 4096)
        self.__state__.value = PLAYER_PLAYING
        self.set_progress(0, self.__track__.total_frames())

    def stop_playing(self):
        if (self.__pcmreader__ is not None):
            self.__pcmreader__.close()
        self.__audio_output__.close()
        self.__state__.value = PLAYER_STOPPED
        self.set_progress(0, 1)

    def output_chunk(self):
        frame = self.__pcmreader__.read(self.__buffer_size__)
        if (len(frame) > 0):
            self.__progress__[0] += frame.frames
            self.__audio_output__.play(frame)
        else:
            self.stop_playing()
            self.__next_track_conn__.send(True)

    def set_progress(self, current, total):
        self.__progress__[1] = total
        self.__progress__[0] = current

    @classmethod
    def run(cls, audio_output, state, command_conn, next_track_conn,
            current_progress, replay_gain=RG_NO_REPLAYGAIN):
        """audio_output is an AudioOutput object

        state is a shared Value of the current state

        command_conn is a bidirectional Connection object
        which reads (command, (arg1, arg2, ...)) tuples
        from the parent and writes responses back

        next_track_conn is a unidirectional Connection object
        which writes an object when the player moves to the next track

        current_progress is an Array of 2 ints
        for the playing file's current/total progress

        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN, or RG_ALBUM_GAIN"""

        #build PlayerProcess state management object
        player = cls(audio_output=audio_output,
                     state=state,
                     progress=current_progress,
                     next_track_conn=next_track_conn,
                     replay_gain=replay_gain)

        while (True):
            if (state.value == PLAYER_PLAYING):
                if (command_conn.poll()):
                    #handle command before processing more audio, if any
                    while (command_conn.poll()):
                        (command, args, return_result) = command_conn.recv()
                        if (command == "exit"):
                            player.close()
                            command_conn.close()
                            next_track_conn.send(False)
                            next_track_conn.close()
                            return
                        else:
                            result = getattr(player, command)(*args)
                            if (return_result):
                                command_conn.send(result)
                else:
                    player.output_chunk()
            else:
                (command, args, return_result) = command_conn.recv()
                if (command == "exit"):
                    player.close()
                    command_conn.close()
                    next_track_conn.send(False)
                    next_track_conn.close()
                    return
                else:
                    result = getattr(player, command)(*args)
                    if (return_result):
                        command_conn.send(result)


class CDPlayer(Player):
    """a class for operating a CDDA player

    the player itself runs in a seperate thread,
    which this sends commands to"""

    def __init__(self, cdda,
                 audio_output,
                 next_track_callback=lambda: None):
        """cdda is a audiotools.CDDA object

        audio_output is an AudioOutput subclass

        next_track_callback is a function with no arguments
        which is called by the player when the current track is finished"""

        from multiprocessing import Process, Array, Value, Pipe
        from threading import Thread

        self.__player__ = None

        if (not isinstance(audio_output, AudioOutput)):
            raise TypeError("invalid output object")

        def call_next_track(next_track_conn, next_track_callback):
            response = next_track_conn.recv()
            while (response):
                next_track_callback()
                response = next_track_conn.recv()
            next_track_conn.close()

        (self.__command_conn__, client_conn) = Pipe(True)
        (server_next_track_conn, client_next_track_conn) = Pipe(False)
        self.__state__ = Value("i", 0)
        self.__progress__ = Array("I", [0, 0])

        thread = Thread(target=call_next_track,
                        args=(server_next_track_conn, next_track_callback))
        thread.daemon = True
        thread.start()

        self.__player__ = Process(
            target=CDPlayerProcess.run,
            kwargs={"cdda":cdda,
                    "audio_output":audio_output,
                    "state":self.__state__,
                    "command_conn":client_conn,
                    "next_track_conn":client_next_track_conn,
                    "current_progress":self.__progress__})

        self.__player__.start()

    def open(self, track_number):
        """track_number indicates which track to open, starting from 1

        stops playing the current track, if any"""

        self.__command_conn__.send(("open", (track_number,), True))
        return self.__command_conn__.recv()

    def set_replay_gain(self, replay_gain):
        #does nothing
        pass


class CDPlayerProcess(PlayerProcess):
    """the CDPlayer class' subprocess

    this should not be instantiated directly;
    CDPlayer will do so automatically"""

    def __init__(self, audio_output,
                 cdda,
                 state,
                 progress,
                 next_track_conn):
        """audio_output is an AudioOutput Object

        cdda is a CDDA object

        state is a shared Value of the current processing state

        progress is a shared Array of current frames / total frames

        next_track_conn is a Connection object
        to be sent an object when the current track ends
        """

        PlayerProcess.__init__(self,
                               audio_output,
                               state,
                               progress,
                               next_track_conn,
                               replay_gain=RG_NO_REPLAYGAIN)

        #self.__track__ will be either a CDTrackReader object or None
        self.__cdda__ = cdda

    def open(self, track_number):
        self.stop_playing()
        self.__track__ = self.__cdda__[track_number]

    def set_replay_gain(self, replay_gain):
        #does nothing
        pass

    def start_playing(self):
        from . import BufferedPCMReader

        #construct pcmreader from track
        pcmreader = BufferedPCMReader(self.__track__)

        #reopen AudioOutput if necessary
        if (not self.__audio_output__.compatible(
                sample_rate=44100,
                channels=2,
                channel_mask=0x3,
                bits_per_sample=16)):
            self.__audio_output__.set_format(
                sample_rate=44100,
                channels=2,
                channel_mask=0x3,
                bits_per_sample=16)

        self.__pcmreader__ = pcmreader
        self.__state__.value = PLAYER_PLAYING
        self.__buffer_size__ = min(round(self.BUFFER_SIZE * 44100), 4096)
        self.set_progress(0, self.__track__.length() * 44100 / 75)

    def stop_playing(self):
        # if (self.__pcmreader__ is not None):
        #     self.__pcmreader__.close()
        # self.__audio_output__.close()
        self.__state__.value = PLAYER_STOPPED
        self.set_progress(0, 1)

    @classmethod
    def run(cls, cdda, audio_output, state, command_conn, next_track_conn,
            current_progress):
        """audio_output is an AudioOutput object

        cdda is a CDDA object

        state is a shared Value of the current state

        command_conn is a bidirectional Connection object
        which reads (command, (arg1, arg2, ...)) tuples
        from the parent and writes responses back

        next_track_conn is a unidirectional Connection object
        which writes an object when the player moves to the next track

        current_progress is an Array of 2 ints
        for the playing file's current/total progress"""

        #build PlayerProcess state management object
        player = cls(audio_output=audio_output,
                     cdda=cdda,
                     state=state,
                     progress=current_progress,
                     next_track_conn=next_track_conn)

        while (True):
            if (state.value == PLAYER_PLAYING):
                if (command_conn.poll()):
                    #handle command before processing more audio, if any
                    while (command_conn.poll()):
                        (command, args, return_result) = command_conn.recv()
                        if (command == "exit"):
                            player.close()
                            command_conn.close()
                            next_track_conn.send(False)
                            next_track_conn.close()
                            return
                        else:
                            result = getattr(player, command)(*args)
                            if (return_result):
                                command_conn.send(result)
                else:
                    player.output_chunk()
            else:
                (command, args, return_result) = command_conn.recv()
                if (command == "exit"):
                    player.close()
                    command_conn.close()
                    next_track_conn.send(False)
                    next_track_conn.close()
                    return
                else:
                    result = getattr(player, command)(*args)
                    if (return_result):
                        command_conn.send(result)


class ThreadedPCMReader:
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
            frame = read(4096)
            while (not stop_event.is_set()):
                #want to be sure to put 0 length frame in queue
                #if reading is intended to continue
                queue.put(frame)
                if (len(frame) > 0):
                    frame = read(4096)
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


class AudioOutput:
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

        #audio outputs are initialized closed for obvious reasons
        self.sample_rate = None
        self.channels = None
        self.channel_mask = None
        self.bits_per_sample = None

    def description(self):
        """returns user-facing name of output device as unicode"""

        raise NotImplementedError()

    def compatible(self, sample_rate, channels, channel_mask, bits_per_sample):
        """returns True if the given pcmreader is compatible

        if False, one is expected to open a new output stream
        which is compatible"""

        return ((self.sample_rate == sample_rate) and
                (self.channels == channels) and
                (self.channel_mask == channel_mask) and
                (self.bits_per_sample == bits_per_sample))

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream for the given format

        if the output stream has already been initialized,
        this will close and reopen the stream for the new format"""

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
        """initializes the output stream for the given format

        if the output stream has already been initialized,
        this will close and reopen the stream for the new format"""

        if (self.__ossaudio__ is None):
            import ossaudiodev

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            #initialize audio output device and setup framelist converter
            self.__ossaudio__ = ossaudiodev.open('w')
            self.__ossmixer__ = ossaudiodev.openmixer()
            if (self.bits_per_sample == 8):
                self.__ossaudio__.setfmt(ossaudiodev.AFMT_S8_LE)
                self.__converter__ = lambda f: f.to_bytes(False, True)
            elif (self.bits_per_sample == 16):
                self.__ossaudio__.setfmt(ossaudiodev.AFMT_S16_LE)
                self.__converter__ = lambda f: f.to_bytes(False, True)
            elif (self.bits_per_sample == 24):
                from .pcm import from_list

                self.__ossaudio__.setfmt(ossaudiodev.AFMT_S16_LE)
                self.__converter__ = lambda f: from_list(
                    [i >> 8 for i in list(f)],
                    self.channels, 16, True).to_bytes(False, True)
            else:
                raise ValueError("Unsupported bits-per-sample")

            self.__ossaudio__.channels(channels)
            self.__ossaudio__.speed(sample_rate)
        else:
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

        #FIXME - pull this from device description
        return u"Pulse Audio"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream for the given format

        if the output stream has already been initialized,
        this will close and reopen the stream for the new format"""

        if (self.__pulseaudio__ is None):
            from .output import PulseAudio

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            self.__pulseaudio__ = PulseAudio(sample_rate,
                                             channels,
                                             bits_per_sample,
                                             "Python Audio Tools")
            self.__converter__ = {
                8:lambda f: f.to_bytes(True, False),
                16:lambda f: f.to_bytes(False, True),
                24:lambda f: f.to_bytes(False, True)}[self.bits_per_sample]
        else:
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
            from .output import PulseAudio

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

        #FIXME - pull this from device description
        return u"Advanced Linux Sound Architecture"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream for the given format

        if the output stream has already been initialized,
        this will close and reopen the stream for the new format"""

        if (self.__alsaaudio__ is None):
            from .output import ALSAAudio

            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            self.__alsaaudio__ = ALSAAudio("default",
                                           sample_rate,
                                            channels,
                                            bits_per_sample)
        else:
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
        """returns True if PulseAudio is available and running on the system"""

        try:
            from .output import ALSAAudio

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

        #FIXME - pull this from device description
        return u"Core Audio"

    def set_format(self, sample_rate, channels, channel_mask, bits_per_sample):
        """initializes the output stream for the given format

        if the output stream has already been initialized,
        this will close and reopen the stream for the new format"""

        if (self.__coreaudio__ is None):
            AudioOutput.set_format(self, sample_rate, channels,
                                   channel_mask, bits_per_sample)

            from .output import CoreAudio
            self.__coreaudio__ = CoreAudio(sample_rate,
                                           channels,
                                           channel_mask,
                                           bits_per_sample)
        else:
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
        return self.__coreaudio__.get_volume()

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            if (self.__coreaudio__ is None):
                self.set_format(*DEFAULT_FORMAT)
            self.__coreaudio__.set_volume(volume)
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
            from .output import CoreAudio

            return True
        except ImportError:
            return False


def available_outputs():
    """iterates over all available AudioOutput objects
    this will always yield at least one output"""

    if (ALSAAudioOutput.available()):
        yield ALSAAudioOutput()

    if (PulseAudioOutput.available()):
        yield PulseAudioOutput()

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
