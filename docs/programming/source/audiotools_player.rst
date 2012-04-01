:mod:`audiotools.player` --- the Audio Player Module
====================================================

.. module:: audiotools.player
   :synopsis: the Audio Player Module

The :mod:`audiotools.player` module contains the Player and
AudioOutput classes for playing AudioFiles.

.. data:: AUDIO_OUTPUT

   A tuple of :class:`AudioOutput`-compatible classes of available
   output types.
   As with ``AVAILABLE_TYPES``, these are classes that are available
   to audiotools, not necessarily available to the user.

================= =================
Class             Output System
----------------- -----------------
PulseAudioOutput  PulseAudio_
OSSAudioOutput    OSS_
PortAudioOutput   PortAudio_
NULLAudioOutput   No output
================= =================


Player Objects
--------------

This class is an audio player which plays audio data
from an opened audio file object to a given output sink.

.. class:: Player(audio_output[, replay_gain[, next_track_callback]])

   ``audio_output`` is a :class:`AudioOutput` object subclass which
   audio data will be played to.
   ``replay_gain`` is either ``RG_NO_REPLAYGAIN``,
   ``RG_TRACK_GAIN`` or ``RG_ALBUM_GAIN``, indicating the level
   of ReplayGain to apply to tracks being played back.
   ``next_track_callback`` is a function which takes no arguments,
   to be called when the currently playing track is completed.

.. method:: Player.open(audiofile)

   Opens the given :class:`audiotools.AudioFile` object for playing.
   Any currently playing file is stopped.

.. method:: Player.play()

   Begins or resumes playing the currently opened
   :class:`audiotools.AudioFile` object, if any.

.. method:: Player.set_replay_gain(replay_gain)

   Sets the given ReplayGain level to apply during playback.
   Choose from ``RG_NO_REPLAYGAIN``, ``RG_TRACK_GAIN`` or ``RG_ALBUM_GAIN``
   ReplayGain cannot be applied mid-playback.
   One must :meth:`stop` and :meth:`play` a file for it to take effect.

.. method:: Player.pause()

   Pauses playback of the current file.
   Playback may be resumed with :meth:`play` or :meth:`toggle_play_pause`

.. method:: Player.toggle_play_pause()

   Pauses the file if playing, play the file if paused.

.. method:: Player.stop()

   Stops playback of the current file.
   If :meth:`play` is called, playback will start from the beginning.

.. method:: Player.close()

   Closes the player for playback.
   The player thread is halted and the :class:`AudioOutput` object is closed.

.. method:: Player.progress()

   Returns a (``pcm_frames_played``, ``pcm_frames_total``) tuple.
   This indicates the current playback status in terms of PCM frames.

CDPlayer Objects
----------------

This class is an audio player which plays audio data from a
CDDA disc to a given output sink.

.. class:: CDPlayer(cdda, audio_output[, next_track_callback])

   ``cdda`` is a :class:`audiotools.CDDA` object.
   ``audio_output`` is a :class:`AudioOutput` object subclass which
   audio data will be played to.
   ``next_track_callback`` is a function which takes no arguments,
   to be called when the currently playing track is completed.

.. method:: CDPlayer.open(track_number)

   Opens the given track number for reading, where
   ``track_number`` starts from 1.

.. method:: CDPlayer.play()

   Begins or resumes playing the currently opened track, if any.

.. method:: CDPlayer.pause()

   Pauses playback of the current track.
   Playback may be resumed with :meth:`play` or :meth:`toggle_play_pause`

.. method:: CDPlayer.toggle_play_pause()

   Pauses the track if playing, play the track if paused.

.. method:: CDPlayer.stop()

   Stops playback of the current track.
   If :meth:`play` is called, playback will start from the beginning.

.. method:: CDPlayer.close()

   Closes the player for playback.
   The player thread is halted and the :class:`AudioOutput` object is closed.

.. method:: CDPlayer.progress()

   Returns a (``pcm_frames_played``, ``pcm_frames_total``) tuple.
   This indicates the current playback status in terms of PCM frames.

AudioOutput Objects
-------------------

This is an abstract class used to implement audio output sinks.

.. class:: AudioOutput( )

.. data:: AudioOutput.NAME

   The name of the AudioOutput subclass as a string.

.. method:: AudioOutput.compatible(pcmreader)

   Returns ``True`` if the given :class:`audiotools.PCMReader`
   is compatible with the currently opened output stream.
   If ``False``, one should call :meth:`init` in order to
   reinitialize the output stream to play the given reader.

.. method:: AudioOutput.init(sample_rate, channels, channel_mask, bits_per_sample)

   Initializes the output stream for playing audio with the given parameters.
   This *must* be called prior to :meth:`play` and :meth:`close`.

.. method:: AudioOutput.framelist_converter()

   Returns a function which converts :class:`audiotools.pcm.FrameList`
   objects to objects which are compatible with our
   :meth:`play` method, for the currently initialized stream.

.. method:: AudioOutput.play(data)

   Plays the converted data object to our output stream.

.. note::

   Why not simply have the :meth:`play` method perform PCM conversion itself
   instead of shifting it to :meth:`framelist_converter`?
   The reason is that conversion may be a relatively time-consuming task.
   By shifting that process into a subthread, there's less chance
   that performing that work will cause playing to stutter
   while it completes.

.. method:: AudioOutput.close()

   Closes the output stream for further playback.

.. classmethod:: AudioOutput.available()

   Returns True if the AudioOutput implementation is available on the system.

.. _PulseAudio: http://www.pulseaudio.org

.. _OSS: http://www.opensound.com

.. _PortAudio: http://www.portaudio.com
