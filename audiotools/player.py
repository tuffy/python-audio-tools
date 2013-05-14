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


class Player:
    """a class for operating an audio player

    the player itself runs in a seperate thread,
    which this sends commands to"""

    def __init__(self, audio_output,
                 replay_gain=RG_NO_REPLAYGAIN,
                 next_track_callback=lambda: None):
        """audio_output is the name of the output as a string
        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN,
        indicating how the player should apply ReplayGain
        next_track_callback is a function with no arguments
        which is called by the player when the current track is finished"""

        from multiprocessing import Process, Array, Pipe
        from threading import Thread

        self.__player__ = None

        def call_next_track(next_track_conn, next_track_callback):
            response = next_track_conn.recv()
            while (response):
                next_track_callback()
                response = next_track_conn.recv()
            next_track_conn.close()

        (self.__command_conn__, client_conn) = Pipe(True)
        (server_next_track_conn, client_next_track_conn) = Pipe(False)
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
                    "current_progress":self.__progress__,
                    "replay_gain":replay_gain})

        self.__player__.start()

    def __del__(self):
        if (self.__player__ is not None):
            self.__command_conn__.send(("exit", tuple()))
            self.__command_conn__.close()
            self.__player__.join()
            self.__player__ = None

    def open(self, track):
        """opens the given AudioFile for playing

        stops playing the current file, if any"""

        self.__command_conn__.send(("open", (track,)))
        return self.__command_conn__.recv()

    def play(self):
        """begins or resumes playing an opened AudioFile, if any"""

        self.__command_conn__.send(("play", tuple()))
        return self.__command_conn__.recv()

    def set_replay_gain(self, replay_gain):
        """sets the given ReplayGain level to apply during playback

        choose from RG_NO_REPLAYGAIN, RG_TRACK_GAIN or RG_ALBUM_GAIN
        replayGain cannot be applied mid-playback
        one must stop() and play() a file for it to take effect"""

        self.__command_conn__.send(("set_replay_gain", (replay_gain,)))
        return self.__command_conn__.recv()

    def pause(self):
        """pauses playback of the current file

        playback may be resumed with play() or toggle_play_pause()"""

        self.__command_conn__.send(("pause", tuple()))
        return self.__command_conn__.recv()

    def toggle_play_pause(self):
        """pauses the file if playing, play the file if paused"""

        self.__command_conn__.send(("toggle_play_pause", tuple()))
        return self.__command_conn__.recv()

    def stop(self):
        """stops playback of the current file

        if play() is called, playback will start from the beginning"""

        self.__command_conn__.send(("stop_playing", tuple()))
        return self.__command_conn__.recv()

    def close(self):
        """closes the player for playback

        the player thread is halted and the AudioOutput is closed"""

        self.__command_conn__.send(("close", tuple()))
        response = self.__command_conn__.recv()
        if (self.__player__ is not None):
            self.__command_conn__.send(("exit", tuple()))
            self.__command_conn__.close()
            self.__player__.join()
            self.__player__ = None
        return response

    def progress(self):
        """returns a (pcm_frames_played, pcm_frames_total) tuple

        this indicates the current playback status in PCM frames"""

        return tuple(self.__progress__)

    def current_output_description(self):
        self.__command_conn__.send(("current_output_description", tuple()))
        return self.__command_conn__.recv()

    def current_output_name(self):
        self.__command_conn__.send(("current_output_name", tuple()))
        return self.__command_conn__.recv()

    def get_volume(self):
        self.__command_conn__.send(("get_volume", tuple()))
        return self.__command_conn__.recv()

    def set_volume(self, volume):
        self.__command_conn__.send(("set_volume", (volume,)))
        return self.__command_conn__.recv()


(PLAYER_STOPPED, PLAYER_PAUSED, PLAYER_PLAYING) = range(3)


class PlayerProcess:
    """the Player class' subprocess

    this should not be instantiated directly;
    player will do so automatically"""

    BUFFER_SIZE = 0.25  # in seconds

    def __init__(self, audio_output, progress, next_track_conn,
                 replay_gain=RG_NO_REPLAYGAIN):
        """audio_output is a string of what audio type to use

        progress is a shared Array of current frames / total frames

        next_track_conn is a Connection object
        to be sent an object when the current track ends

        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN, or RG_ALBUM_GAIN
        """

        self.__track__ = None          # the currently playing AudioFile
        self.__pcmreader__ = None      # the currently playing PCMReader

        # an AudioOutput subclass
        self.__audio_output__ = open_output(audio_output)
        self.__converter__ = None      # a FrameList converter function
        self.__buffer_size__ = 0       # the number of PCM frames to process

        self.__state__ = PLAYER_STOPPED
        self.__progress__ = progress   #an Array of current/total frames

        self.set_progress(0, 1)

        self.__next_track_conn__ = next_track_conn

        self.__replay_gain__ = replay_gain  # the sort of ReplayGain to apply

    def open(self, track):
        self.stop_playing()
        self.__track__ = track
        self.set_progress(0, 1)

    def close(self):
        self.stop_playing()
        self.__audio_output__.close()

    def pause(self):
        if (self.__state__ == PLAYER_PLAYING):
            self.__audio_output__.pause()
            self.__state__ = PLAYER_PAUSED

    def play(self):
        if (self.__track__ is not None):
            if (self.__state__ == PLAYER_STOPPED):
                self.start_playing()
            elif (self.__state__ == PLAYER_PAUSED):
                self.__audio_output__.resume()
                self.__state__ = PLAYER_PLAYING
            elif (self.__state__ == PLAYER_PLAYING):
                pass

    def set_replay_gain(self, replay_gain):
        self.__replay_gain__ = replay_gain

    def toggle_play_pause(self):
        if (self.__state__ == PLAYER_PLAYING):
            self.pause()
        elif ((self.__state__ == PLAYER_PAUSED) or
              (self.__state__ == PLAYER_STOPPED)):
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
        self.__state__ = PLAYER_PLAYING
        self.set_progress(0, self.__track__.total_frames())

    def stop_playing(self):
        if (self.__pcmreader__ is not None):
            self.__pcmreader__.close()
        self.__state__ = PLAYER_STOPPED
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
    def run(cls, audio_output, command_conn, next_track_conn,
            current_progress, replay_gain=RG_NO_REPLAYGAIN):
        """audio_output is a string of what audio type to use

        command_conn is a bidirectional Connection object
        which reads (command, (arg1, arg2, ...)) tuples
        from the parent and writes responses back

        next_track_conn is a unidirectional Connection object
        which writes an object when the player moves to the next track

        current_progress is an Array of 2 ints
        for the playing file's current/total progress

        replay_gain is RG_NO_REPLAYGAIN, RG_TRACK_GAIN, or RG_ALBUM_GAIN"""

        #build PlayerProcess state management object
        player = PlayerProcess(
            audio_output=audio_output,
            progress=current_progress,
            next_track_conn=next_track_conn,
            replay_gain=replay_gain)

        while (True):
            if (player.__state__ == PLAYER_PLAYING):
                if (command_conn.poll()):
                    #handle command before processing more audio, if any
                    (command, args) = command_conn.recv()
                    if (command == "exit"):
                        player.close()
                        command_conn.close()
                        next_track_conn.send(False)
                        next_track_conn.close()
                        return
                    else:
                        result = getattr(player, command)(*args)
                        command_conn.send(result)
                else:
                    player.output_chunk()
            else:
                (command, args) = command_conn.recv()
                if (command == "exit"):
                    player.close()
                    command_conn.close()
                    next_track_conn.send(False)
                    next_track_conn.close()
                    return
                else:
                    result = getattr(player, command)(*args)
                    command_conn.send(result)


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
    CDPlayer will do so automatically"""

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
                self.pcmconverter = ThreadedPCMConverter(
                    self.track,
                    self.framelist_converter)
                self.frames_played = 0
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PAUSED):
                self.audio_output.resume()
                self.state = PLAYER_PLAYING
            elif (self.state == PLAYER_PLAYING):
                pass

    def pause(self):
        if (self.state == PLAYER_PLAYING):
            self.audio_output.pause()
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
            if (self.state in (PLAYER_STOPPED, PLAYER_PAUSED)):
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
        from . import DecodingError
        try:
            self.pcmreader.close()
        except DecodingError:
            pass


class ThreadedPCMConverter:
    """a class for decoding a PCMReader in a seperate thread

    PCMReader's data is queued such that even if decoding and
    conversion are relatively time-consuming, read() will
    continue smoothly"""

    def __init__(self, pcmreader, converter):
        """pcmreader is a PCMReader object

        converter is a function which takes a FrameList
        and returns an object suitable for the current AudioOutput object
        upon conclusion, the PCMReader is automatically closed"""

        import Queue
        import threading

        self.decoded_data = Queue.Queue()
        self.stop_decoding = threading.Event()

        def convert(pcmreader,
                    buffer_size,
                    converter,
                    decoded_data,
                    stop_decoding):
            try:
                frame = pcmreader.read(buffer_size)
                while ((not stop_decoding.is_set()) and (len(frame) > 0)):
                    try:
                        decoded_data.put((converter(frame), frame.frames),
                                         True,
                                         1)
                        frame = pcmreader.read(buffer_size)
                    except Queue.Full:
                        pass
                else:
                    decoded_data.put((None, 0))
                    pcmreader.close()
            except (ValueError, IOError):
                decoded_data.put((None, 0))
                pcmreader.close()

        self.thread = threading.Thread(
            target=convert,
            args=(pcmreader,
                  pcmreader.sample_rate / 20,
                  converter,
                  self.decoded_data,
                  self.stop_decoding))
        self.thread.daemon = True
        self.thread.start()

    def read(self):
        """returns a (converted_data, pcm_frame_count) tuple"""

        return self.decoded_data.get(True)

    def close(self):
        """stops the decoding thread and closes the PCMReader"""

        self.stop_decoding.set()
        self.thread.join()


class AudioOutput:
    """an abstract parent class for playing audio"""

    def __init__(self):
        """automatically initializes output format for playing
        CD quality audio"""

        self.set_format(44100, 2, 0x3, 16)

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

    def __init__(self):
        self.__volume__ = 0.30
        AudioOutput.__init__(self)

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

        pass

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
        AudioOutput.__init__(self)

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

        raise NotImplementedError()

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        raise NotImplementedError()

    def close(self):
        """closes the output stream"""

        if (self.__ossaudio__ is not None):
            self.__ossaudio__.close()
            self.__ossaudio__ = None

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

    def __init__(self):
        self.__pulseaudio__ = None
        AudioOutput.__init__(self)

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

        self.__pulseaudio__.pause()

    def resume(self):
        """resumes playing paused audio output"""

        self.__pulseaudio__.resume()

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        return self.__pulseaudio__.get_volume()

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            self.__pulseaudio__.set_volume(volume)
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

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


class CoreAudioOutput(AudioOutput):
    """an AudioOutput subclass for CoreAudio output"""

    NAME = "CoreAudio"

    def __init__(self):
        self.__coreaudio__ = None
        AudioOutput.__init__(self)

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

        self.__coreaudio__.pause()

    def resume(self):
        """resumes playing paused audio output"""

        self.__coreaudio__.resume()

    def get_volume(self):
        """returns a floating-point volume value between 0.0 and 1.0"""

        return self.__coreaudio__.get_volume()

    def set_volume(self, volume):
        """sets the output volume to a floating point value
        between 0.0 and 1.0"""

        if ((volume >= 0) and (volume <= 1.0)):
            self.__coreaudio__.set_volume(volume)
        else:
            raise ValueError("volume must be between 0.0 and 1.0")

    def close(self):
        """closes the output stream"""

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
    """iterates over all available AudioOutput subclasses
    this will always yield at least one output"""

    if (PulseAudioOutput.available()):
        yield PulseAudioOutput

    if (CoreAudioOutput.available()):
        yield CoreAudioOutput

    if (OSSAudioOutput.available()):
        yield OSSAudioOutput

    yield NULLAudioOutput


def open_output(output):
    """given an output type string (e.g. "PulseAudio")
    returns that AudioOutput subclass
    or raises ValueError if it is unavailable"""

    for audio_output in available_outputs():
        if (audio_output.NAME == output):
            return audio_output()
    else:
        raise ValueError("no such outout %s" % (output))
