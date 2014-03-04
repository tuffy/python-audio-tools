:mod:`audiotools.player` --- the Audio Player Module
====================================================

.. module:: audiotools.player
   :synopsis: the Audio Player Module

The :mod:`audiotools.player` module contains the Player and
AudioOutput classes for playing AudioFiles.

.. function:: audiotools.player.available_outputs()

Iterates over all available :class:`AudioOutput` objects.
This will always return at least one output object.

.. function:: audiotools.player.open_output(output)

Given a string of an :class:`AudioOutput` class' ``NAME`` attribute,
returns the given :class:`AudioOutput` object.

Raises :exc:`ValueError` if the output cannot be found.

Player Objects
--------------

This class is an audio player which plays audio data
from an opened audio file object to a given output sink.

.. class:: Player(audio_output[, replay_gain[, next_track_callback]])

   ``audio_output`` is an :class:`AudioOutput` object.

   ``replay_gain`` is either ``RG_NO_REPLAYGAIN``,
   ``RG_TRACK_GAIN`` or ``RG_ALBUM_GAIN``, indicating the level
   of ReplayGain to apply to tracks being played back.

   ``next_track_callback`` is a function which takes no arguments,
   to be called when the currently playing track is completed.

   Raises :exc:`ValueError` if unable to start player subprocess.

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

.. method:: Player.set_output(audio_output)

   Changes where the audio will be played to the given output
   where ``audio_output`` is an :class:`AudioOutput` object.

   Any currently playing audio is stopped and must be resumed
   from the beginning on the given output device.

.. method:: Player.pause()

   Pauses playback of the current file.
   Playback may be resumed with :meth:`play` or :meth:`toggle_play_pause`

.. method:: Player.toggle_play_pause()

   Pauses the file if playing, play the file if paused.

.. method:: Player.stop()

   Stops playback of the current file.
   If :meth:`play` is called, playback will start from the beginning.

.. method:: Player.state()

   Returns the current state of the player which will be either
   ``PLAYER_STOPPED``, ``PLAYER_PAUSED`` or ``PLAYER_PLAYING`` integers.

.. method:: Player.close()

   Closes the player for playback.
   The player thread is halted and the :class:`AudioOutput` object is closed.

.. method:: Player.progress()

   Returns a (``pcm_frames_played``, ``pcm_frames_total``) tuple.
   This indicates the current playback status in terms of PCM frames.

.. method:: Player.current_output_description()

   Returns the human-readable description of the current output device
   as a Unicode string.

.. method:: Player.current_output_name()

   Returns the ``NAME`` attribute of the current output device
   as a plain string.

.. method:: Player.get_volume()

   Returns the current volume level as a floating point value
   between 0.0 and 1.0, inclusive.

.. method:: Player.set_volume(volume)

   Given a floating point value between 0.0 and 1.0, inclusive,
   sets the current volume level to that value.

.. method:: Player.change_volume(delta)

   Given a floating point delta value which may be positive
   (to increase volume) or negative (to decrease volume),
   adjusts the current volume by that amount and returns
   the new volume as a floating point value between 0.0 and 1.0,
   inclusive.

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

.. class:: AudioOutput()

.. data:: AudioOutput.NAME

   The name of the AudioOutput subclass as a string.

.. method:: AudioOutput.description()

   Returns a user-friendly name of the output device as a Unicode string.

.. method:: AudioOutput.compatible(sample_rate, channels, channel_mask, bits_per_sample)

   Returns ``True`` if the given attributes are compatible
   with the currently opened output stream.

.. method:: AudioOutput.set_format(sample_rate, channels, channel_mask, bits_per_sample)

   Sets the output stream to the given format.

   If the stream hasn't been initialized, this method initializes it
   to that format.

   If the stream has been initialized to a different format,
   this method closes and reports the stream to the new format.

   If the stream has been initialized to the same format,
   this method does nothing.

.. method:: AudioOutput.play(framelist)

   Plays the given FrameList object to the output stream.
   This presumes the output stream's format has been set correctly.

.. method:: AudioOutput.pause()

   Pauses output of playing data.

.. note::

   Although suspending the transmission of data to output will also
   have the same effect as pausing, calling the output's .pause() method
   will typically suspend output immediately instead of having to
   wait for the buffer to empty - which may take a fraction of a second.

.. method:: AudioOutput.resume()

   Resumes playing data to output after it has been paused.

.. method:: AudioOutput.get_volume()

   Returns a floating-point volume value between 0.0 and 1.0, inclusive.

.. method:: AudioOutput.set_volume(volume)

   Given a floating-point volume value between 0.0 and 1.0, inclusive,
   sets audio output to that volume.

.. method:: AudioOutput.close()

   Closes the output stream for further playback.

.. classmethod:: AudioOutput.available()

   Returns True if the AudioOutput implementation is available on the system.
