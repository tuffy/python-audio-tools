:mod:`audiotools` --- the Base Python Audio Tools Module
========================================================

.. module:: audiotools
   :synopsis: the Base Python Audio Tools Module


The :mod:`audiotools` module contains a number of useful base
classes and functions upon which all of the other modules depend.

.. function:: open(filename)

   Opens the given filename string and returns an :class:`AudioFile`-compatible
   object.

AudioFile Objects
-----------------

.. class:: AudioFile()

   The :class:`AudioFile` class represents an audio file on disk,
   such as a FLAC file, MP3 file, WAVE file and so forth.
   It is not meant to be instatiated directly, but returned from functions
   such as :func:`open` which will return an :class:`AudioFile`-compatible
   object implementing the following methods and attributes.

.. classmethod:: AudioFile.is_type(file)

   Takes a file-like object with :meth:`read` and :meth:`seek` methods.
   Returns ``True`` if the file is determined to be of the same type
   as this particular :class:`AudioFile` implementation.
   Returns ``False`` if not.

.. method:: AudioFile.bits_per_sample()

   Returns the number of bits-per-sample in this audio file as a positive
   integer.

.. method:: AudioFile.channels()

   Returns the number of channels in this audio file as a positive integer.

.. method:: AudioFile.channel_mask()

   Returns a :class:`ChannelMask` object representing the channel assignment
   of this audio file.
   If the channel assignment is unknown or undefined, that :class:`ChannelMask`
   object may have an undefined value.

.. method:: AudioFile.sample_rate()

   Returns the sample rate of this audio file, in Hz, as a positive integer.

.. method:: AudioFile.total_frames()

   Returns the total number of PCM frames in this audio file,
   as a non-negative integer.

.. method:: AudioFile.cd_frames()

   Returns the total number of CD frames in this audio file,
   as a non-negative integer.
   Each CD frame is 1/75th of a second.

.. method:: AudioFile.lossless()

   Returns ``True`` if the data in the audio file has been stored losslessly.
   Returns ``False`` if not.

.. method:: AudioFile.set_metadata(metadata)

   Takes a :class:`MetaData`-compatible object and sets this audio file's
   metadata to that value, if possible.
   Raises :exc:`IOError` if a problem occurs when writing the file.

.. method:: AudioFile.get_metadata()

   Returns a :class:`MetaData`-compatible object representing this
   audio file's metadata, or ``None`` if this file contains no
   metadata.
   Raises :exc:`IOError` if a problem occurs when reading the file.

.. method:: AudioFile.delete_metadata()

   Deletes the audio file's metadata, removing or unsetting tags
   as necessary.
   Raises :exc:`IOError` if a problem occurs when writing the file.

.. method:: AudioFile.to_pcm()

   Returns this audio file's PCM data as a :class:`PCMReader`-compatible
   object.

.. classmethod:: AudioFile.from_pcm(filename, pcmreader[, compression=None])

   Takes a filename string, :class:`PCMReader`-compatible object
   and optional compression level string.
   Creates a new audio file as the same format as this audio class
   and returns a new :class:`AudioFile`-compatible object.
   Raises :exc:`EncodingError` if a problem occurs during encoding.

Transcoding an Audio File
^^^^^^^^^^^^^^^^^^^^^^^^^

In this example, we'll transcode ``track.flac`` to ``track.mp3``
at the default compression level:

   >>> audiotools.MP3Audio.from_pcm("track.mp3",
   ...                              audiotools.open("track.flac").to_pcm())

.. method:: AudioFile.to_wave(wave_filename)

   Takes a filename string and creates a new RIFF WAVE file
   at that location.
   Raises :exc:`EncodingError` if a problem occurs during encoding.

.. classmethod:: AudioFile.from_wave(filename, wave_filename[, compression=None])

   Takes a filename string of our new file, a wave_filename string of
   an existing RIFF WAVE file and an optional compression level string.
   Creates a new audio file as the same format as this audio class
   and returns a new :class:`AudioFile`-compatible object.
   Raises :exc:`EncodingError` if a problem occurs during encoding.

.. classmethod:: AudioFile.supports_foreign_riff_chunks()

   Returns ``True`` if this :class:`AudioFile` implementation supports storing
   non audio RIFF WAVE chunks.  Returns ``False`` if not.

.. method:: AudioFile.has_foreign_riff_chunks()

   Returns ``True`` if this audio file contains non audio RIFF WAVE chunks.
   Returns ``False`` if not.

.. method:: AudioFile.track_number()

   Returns this audio file's track number as a non-negative integer.
   This method first checks the file's metadata values.
   If unable to find one, it then tries to determine a track number
   from the track's filename.
   If that method is also unsuccessful, it returns 0.

.. method:: AudioFile.album_number()

   Returns this audio file's album number as a non-negative integer.
   This method first checks the file's metadata values.
   If unable to find one, it then tries to determine an album number
   from the track's filename.
   If that method is also unsuccessful, it returns 0.

.. classmethod:: AudioFile.track_name(track_number, track_metadata[, album_number = 0[, format = FORMAT_STRING]])

    Given a track number integer, :class:`MetaData`-compatible object
    (or ``None``) and optional album number integer and optional
    Python-formatted format string, returns a filename string with
    the format string fields filled-in.
    Raises :exc:`UnsupportedTracknameField` if the format string contains
    unsupported fields.

.. classmethod:: AudioFile.add_replay_gain(filenames)

   Given a list of filename strings of the same class as this
   :class:`AudioFile` class, calculates and adds ReplayGain metadata
   to those files.
   Raises :exc:`ValueError` if some problem occurs during ReplayGain
   calculation or application.

.. classmethod:: AudioFile.can_add_replay_gain()

   Returns ``True`` if this audio class supports ReplayGain
   and we have the necessary binaries to apply it.
   Returns ``False`` if not.

.. classmethod:: AudioFile.lossless_replay_gain()

   Returns ``True`` if this audio class applies ReplayGain via a
   lossless process - such as by adding a metadata tag of some sort.
   Returns ``False`` if applying metadata modifies the audio file
   data itself.

.. method:: AudioFile.replay_gain()

   Returns this audio file's ReplayGain values as a
   :class:`ReplayGain` object, or ``None`` if this audio file has no values.

.. method:: AudioFile.set_cuesheet(cuesheet)

   Takes a cuesheet-compatible object with :meth:`catalog`,
   :meth:`IRSCs`, :meth:`indexes` and :meth:`pcm_lengths` methods
   and sets this audio file's embedded cuesheet to those values, if possible.
   Raises :exc:`IOError` if this :class:`AudioFile` supports embedded
   cuesheets but some error occurred when writing the file.

.. method:: AudioFile.get_cuesheet()

   Returns a cuesheet-compatible object with :meth:`catalog`,
   :meth:`IRSCs`, :meth:`indexes` and :meth:`pcm_lengths` methods
   or ``None`` if no cuesheet is embedded.
   Raises :exc:`IOError` if some error occurs when reading the file.

.. classmethod:: AudioFile.has_binaries()

   Returns ``True`` if all the binaries necessary to implement
   this :class:`AudioFile`-compatible class are present and executable.
   Returns ``False`` if not.

