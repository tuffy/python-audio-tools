:mod:`audiotools` --- the Base Python Audio Tools Module
========================================================

.. module:: audiotools
   :synopsis: the Base Python Audio Tools Module


The :mod:`audiotools` module contains a number of useful base
classes and functions upon which all of the other modules depend.


.. data:: VERSION

   The current Python Audio Tools version as a plain string.

.. data:: AVAILALBLE_TYPES

   A tuple of :class:`AudioFile`-compatible objects of available
   audio types.
   Note these are types available to audiotools, not necessarily
   available to the user - depending on whether the required binaries
   are installed or not.

   ============= ==================================
   Class         Format
   ------------- ----------------------------------
   AACAudio      AAC in ADTS container
   AiffAudio     Audio Interchange File Format
   AuAudio       Sun Au
   FlacAudio     Native Free Lossless Audio Codec
   M4AAudio      AAC in M4A container
   MP3Audio      MPEG-1 Layer 3
   MP2Audio      MPEG-1 Layer 2
   OggFlacAudio  Ogg Free Lossless Audio Codec
   SpeexAudio    Ogg Speex
   VorbisAudio   Ogg Vorbis
   WaveAudio     Waveform Audio File Format
   WavPackAudio  WavPack
   ============= ==================================

.. data:: TYPE_MAP

   A dictionary of type_name strings -> :class:`AudioFile`
   values containing only types which have all required binaries
   installed.

.. data:: BIN

   A dictionary-like class for performing lookups of system binaries.
   This checks the system and user's config files and ensures that
   any redirected binaries are called from their proper location.
   For example, if the user has configured ``flac(1)`` to be run
   from ``/opt/flac/bin/flac``

   >>> BIN["flac"]
   "/opt/flac/bin/flac"

   This class also has a ``can_execute()`` method which returns
   ``True`` if the given binary is executable.

   >>> BIN.can_execute(BIN["flac"])
   True

.. function:: open(filename)

   Opens the given filename string and returns an :class:`AudioFile`-compatible
   object.
   Raises :exc:`UnsupportedFile` if the file cannot be opened,
   identified or is not supported.

.. function:: open_files(filenames[, sorted])

   Given a list of filename strings, returns a list of
   :class:`AudioFile`-compatible objects which can be successfully opened.
   By default, they are returned sorted by album number and track number.
   If ``sorted`` is ``False``, they are returned in the same order
   as they appear in the filenames list.

.. function:: open_directory(directory[, sorted])

   Given a root directory, returns an iterator of all the
   :class:`AudioFile`-compatible objects found via a recursive
   search of that directory.
   ``sorted`` works as in :func:`open_files`.

.. function:: group_tracks(audiofiles)

   Given an iterable collection of :class:`AudioFile`-compatible objects,
   returns an iterator of objects grouped into lists by album.
   That is, all objects with the same ``album_name`` and ``album_number``
   metadata fields will be returned in the same list on each pass.

.. function:: filename_to_type(path)

   Given a path, try to guess its :class:`AudioFile` class based on
   its filename suffix.
   Raises :exc:`UnknownAudioType` if the suffix is unrecognized.
   Raises :exc:`AmbiguousAudioType` if more than one type of audio
   shares the same suffix.

.. function:: transfer_data(from_function, to_function)

   This function takes two functions, presumably analagous
   to :func:`write` and :func:`read` functions, respectively.
   It calls ``to_function`` on the object returned by calling
   ``from_function`` with an integer argument (presumably a string)
   until that object's length is 0.

   >>> infile = open("input.txt","r")
   >>> outfile = open("output.txt","w")
   >>> transfer_data(infile.read,outfile.write)
   >>> infile.close()
   >>> outfile.close()

.. function:: transfer_framelist_data(pcmreader, to_function[, signed[, big_endian]])

   A natural progression of :func:`transfer_data`, this function takes
   a :class:`PCMReader` object and transfers the :class:`pcm.FrameList`
   objects returned by its :meth:`PCMReader.read` method to ``to_function``
   after converting them to plain strings.

   >>> pcm_data = audiotools.open("file.wav").to_pcm()
   >>> outfile = open("output.pcm","wb")
   >>> transfer_framelist_data(pcm_data,outfile)
   >>> pcm_data.close()
   >>> outfile.close()

.. function:: pcm_cmp(pcmreader1, pcmreader2)

   This function takes two :class:`PCMReader` objects and compares
   their PCM output.
   Returns ``True`` if that output matches exactly, ``False`` if not.

.. function:: stripped_pcm_cmp(pcmreader1, pcmreader2)

   This function takes two :class:`PCMReader` objects and compares
   their PCM output after stripping any 0 samples from the beginning
   and end of each.
   Returns ``True`` if the remaining output matches exactly,
   ``False`` if not.

.. function:: pcm_split(pcmreader, pcm_lengths)

   Takes a :class:`PCMReader` object and list of PCM sample length integers.
   Returns an iterator of new :class:`PCMReader` objects,
   each limited to the given lengths.
   The original pcmreader is closed upon the iterator's completion.

.. function:: calculate_replay_gain(audiofiles)

   Takes a list of :class:`AudioFile`-compatible objects.
   Returns an iterator of
   ``(audiofile, track_gain, track_peak, album_gain, album_peak)``
   tuples or raises :exc:`ValueError` if a problem occurs during calculation.

.. function:: read_metadata_file(path)

   Given a path to a FreeDB XMCD file or MusicBrainz XML file,
   returns an :class:`AlbumMetaData`-compatible object
   or raises a :exc:`MetaDataFileException` if the file cannot be
   read or parsed correctly.

.. function:: read_sheet(filename)

   Reads a Cuesheet-compatible file such as :class:`toc.TOCFile` or
   :class:`cue.Cuesheet` or raises :exc:`SheetException` if
   the file cannot be opened, identified or parsed correctly.

.. function:: find_glade_file(glade_filename)

   Given a Glade filename, search various system directories for
   the full path to an existing file.
   Raises :exc:`IOError` if the file cannot be found.

AudioFile Objects
-----------------

.. class:: AudioFile()

   The :class:`AudioFile` class represents an audio file on disk,
   such as a FLAC file, MP3 file, WAVE file and so forth.
   It is not meant to be instatiated directly.  Instead, functions
   such as :func:`open` will return :class:`AudioFile`-compatible
   objects implementing the following methods.

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

MetaData Objects
----------------

.. class:: MetaData([track_name[, track_number[, track_total[, album_name[, artist_name[, performer_name[, composer_name[, conductor_name[, media[, ISRC[, catalog[, copyright[, publisher[, year[, data[, album_number[, album_total[, comment[, images]]]]]]]]]]]]]]]]]]])

   The :class:`MetaData` class represents an :class:`AudioFile`'s
   non-technical metadata.
   It can be instantiated directly for use by the :meth:`set_metadata`
   method.
   However, the :meth:`get_metadata` method will typically return
   :class:`MetaData`-compatible objects corresponding to the audio file's
   low-level metadata implementation rather than actual :class:`MetaData`
   objects.
   Modifying fields within a :class:`MetaData`-compatible object
   will modify its underlying representation and those changes
   will take effect should :meth:`set_metadata` be called with
   that updated object.

   The ``images`` argument, if given, should be an iterable collection
   of :class:`Image`-compatible objects.

.. data:: MetaData.track_name

   This individual track's name as a Unicode string.

.. data:: MetaData.track_number

   This track's number within the album as an integer.

.. data:: MetaData.track_total

   The total number of tracks on the album as an integer.

.. data:: MetaData.album_name

   The name of this track's album as a Unicode string.

.. data:: MetaData.artist_name

   The name of this track's original creator/composer as a Unicode string.

.. data:: MetaData.performer_name

   The name of this track's performing artist as a Unicode string.

.. data:: MetaData.composer_name

   The name of this track's composer as a Unicode string.

.. data:: MetaData.conductor_name

   The name of this track's conductor as a Unicode string.

.. data:: MetaData.media

   The album's media type, such as u"CD", u"tape", u"LP", etc.
   as a Unicode string.

.. data:: MetaData.ISRC

   This track's ISRC value as a Unicode string.

.. data:: MetaData.catalog

   This track's album catalog number as a Unicode string.

.. data:: MetaData.year

   This track's album release year as a Unicode string.

.. data:: MetaData.date

   This track's album recording date as a Unicode string.

.. data:: MetaData.album_number

   This track's album number if it is one of a series of albums,
   as an integer.

.. data:: MetaData.album_total

   The total number of albums within the set, as an integer.

.. data:: MetaData.comment

   This track's comment as a Unicode string.

.. classmethod:: MetaData.converted(metadata)

   Takes a :class:`MetaData`-compatible object (or ``None``)
   and returns a new :class:`MetaData` object of the same class, or ``None``.
   For instance, ``VorbisComment.converted()`` returns ``VorbisComment``
   objects.
   The purpose of this classmethod is to offload metadata conversion
   to the metadata classes themselves.
   Therefore, by using the ``VorbisComment.converted()`` classmethod,
   the ``VorbisAudio`` class only needs to know how to handle
   ``VorbisComment`` metadata.

   Why not simply handle all metadata using this high-level representation
   and avoid conversion altogether?
   The reason is that :class:`MetaData` is often only a subset of
   what the low-level implementation can support.
   For example, a ``VorbisComment`` may contain the ``'FOO'`` tag
   which has no analogue in :class:`MetaData`'s list of fields.
   But when passed through the ``VorbisComment.converted()`` classmethod,
   that ``'FOO'`` tag will be preserved as one would expect.

   The key is that performing:

   >>> track.set_metadata(track.get_metadata())

   should always round-trip properly and not lose any metadata values.

.. classmethod:: MetaData.supports_images()

   Returns ``True`` if this :class:`MetaData` implementation supports images.
   Returns ``False`` if not.

.. method:: MetaData.images()

   Returns a list of :class:`Image`-compatible objects this metadata contains.

.. method:: MetaData.front_covers()

   Returns a subset of :meth:`images` which are marked as front covers.

.. method:: MetaData.back_covers()

   Returns a subset of :meth:`images` which are marked as back covers.

.. method:: MetaData.leaflet_pages()

   Returns a subset of :meth:`images` which are marked as leaflet pages.

.. method:: MetaData.media_images()

   Returns a subset of :meth:`images` which are marked as media.

.. method:: MetaData.other_images()

   Returns a subset of :meth:`images` which are marked as other.

.. method:: MetaData.add_image(image)

   Takes a :class:`Image`-compatible object and adds it to this
   metadata's list of images.

.. method:: MetaData.delete_image(image)

   Takes an :class:`Image` from this class, as returned by :meth:`images`,
   and removes it from this metadata's list of images.

.. method:: MetaData.merge(new_metadata)

   Updates this metadata by replacing empty fields with those
   from ``new_metadata``.  Non-empty fields are left as-is.

AlbumMetaData Objects
---------------------

.. class:: AlbumMetaData(metadata_iter)

   This is a dictionary-like object of
   track_number -> :class:`MetaData` values.
   It is designed to represent metadata returned by CD lookup
   services such as FreeDB or MusicBrainz.

.. method:: AlbumMetaData.metadata()

   Returns a single :class:`MetaData` object containing all the
   fields that are consistent across this object's collection of MetaData.


Image Objects
-------------

.. class:: Image(data, mime_type, width, height, color_depth, color_count, description, type)

   This class is a container for image data.

.. data:: Image.data

   A plain string of raw image bytes.

.. data:: Image.mime_type

   A Unicode string of this image's MIME type, such as u'image/jpeg'

.. data:: Image.width

   This image's width in pixels as an integer.

.. data:: Image.height

   This image's height in pixels as an integer

.. data:: Image.color_depth

   This image's color depth in bits as an integer.
   24 for JPEG, 8 for GIF, etc.

.. data:: Image.color_count

   For palette-based images, this is the number of colors the image contains
   as an integer.
   For non-palette images, this value is 0.

.. data:: Image.description

   A Unicode string of this image's description.

.. data:: Image.type

   An integer representing this image's type.

   ===== ============
   Value Type
   ----- ------------
   0     front cover
   1     back cover
   2     leaflet page
   3     media
   4     other
   ===== ============

.. method:: Image.suffix()

   Returns this image's typical filename suffix as a plain string.
   For example, JPEGs return ``"jpg"``

.. method:: Image.type_string()

   Returns this image's type as a plain string.
   For example, an image of type 0 returns ``"Front Cover"``

.. classmethod:: Image.new(image_data, description, type)

   Given a string of raw image bytes, a Unicode description string
   and image type integer, returns an :class:`Image`-compatible object.
   Raises :exc:`InvalidImage` If unable to determine the
   image type from the data string.

.. method:: Image.thumbnail(width, height, format)

   Given width and height integers and a format string (such as ``"JPEG"``)
   returns a new :class:`Image` object resized to those dimensions
   while retaining its original aspect ratio.

ReplayGain Objects
------------------

.. class:: ReplayGain(track_gain, track_peak, album_gain, album_peak)

   This is a simple container for ReplayGain values.

.. data:: ReplayGain.track_gain

   A float of a track's ReplayGain value.

.. data:: ReplayGain.track_peak

   A float of a track's peak value, from 0.0 to 1.0

.. data:: ReplayGain.album_gain

   A float of an album's ReplayGain value.

.. data:: ReplayGain.album_peak

   A float of an album's peak value, from 0.0 to 1.0

PCMReader Objects
-----------------

.. class:: PCMReader(file, sample_rate, channels, channel_mask, bits_per_sample[, process[, signed[, big_endian]]])

   This class wraps around file-like objects and generates
   :class:`pcm.FrameList` objects on each call to :meth:`read`.
   ``sample_rate``, ``channels``, ``channel_mask`` and ``bits_per_sample``
   should be integers.
   ``process`` is a subprocess helper object which generates PCM data.
   ``signed`` is ``True`` if the generated PCM data is signed.
   ``big_endian`` is ``True`` if the generated PCM data is big-endian.

   Note that :class:`PCMReader`-compatible objects need only implement the
   ``sample_rate``, ``channels``, ``channel_mask`` and ``bits_per_sample``
   fields.
   The rest are helpers for converting raw strings into :class:`pcm.FrameList`
   objects.

.. data:: PCMReader.sample_rate

   The sample rate of this audio stream, in Hz, as a positive integer.

.. data:: PCMReader.channels

   The number of channels in this audio stream as a positive integer.

.. data:: PCMReader.channel_mask

   The channel mask of this audio stream as a non-negative integer.

.. data:: PCMReader.bits_per_sample

   The number of bits-per-sample in this audio stream as a positive integer.

.. method:: PCMReader.read(bytes)

   Try to read a :class:`pcm.FrameList` object of size ``bytes``, if possible.
   This method is *not* guaranteed to read that amount of bytes.
   It may return less, particularly at the end of an audio stream.
   It may even return FrameLists larger than requested.
   However, it must always return a non-empty FrameList until the
   end of the PCM stream is reached.

.. method:: PCMReader.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.

PCMConverter Objects
^^^^^^^^^^^^^^^^^^^^

.. class:: PCMConverter(pcmreader, sample_rate, channels, channel_mask, bits_per_sample)

   This class takes an existing :class:`PCMReader`-compatible object
   along with a new set of ``sample_rate``, ``channels``,
   ``channel_mask`` and ``bits_per_sample`` values.
   Data from ``pcmreader`` is then automatically converted to
   the same format as those values.

.. data:: PCMConverter.sample_rate

   If the new sample rate differs from ``pcmreader``'s sample rate,
   audio data is automatically resampled on each call to :meth:`read`.

.. data:: PCMConverter.channels

   If the new number of channels is smaller than ``pcmreader``'s channel
   count, existing channels are removed or downmixed as necessary.
   If the new number of channels is larger, data from the first channel
   is duplicated as necessary to fill the rest.

.. data:: PCMConverter.channel_mask

   If the new channel mask differs from ``pcmreader``'s channel mask,
   channels are removed as necessary such that the proper channel
   only outputs to the proper speaker.

.. data:: PCMConverter.bits_per_sample

   If the new bits-per-sample differs from ``pcmreader``'s
   number of bits-per-sample, samples are shrunk or enlarged
   as necessary to cover the full amount of bits.

.. method:: PCMConverter.read

   This method functions the same as the :meth:`PCMReader.read` method.

.. method:: PCMConverter.close

   This method functions the same as the :meth:`PCMReader.close` method.

BufferedPCMReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: BufferedPCMReader(pcmreader)

   This class wraps around an existing :class:`PCMReader` object.
   Its calls to :meth:`read` are guaranteed to return
   :class:`pcm.FrameList` objects as close to the requested amount
   of bytes as possible without going over by buffering data
   internally.

   The reason such behavior is not required is that we often
   don't care about the size of the individual FrameLists being
   passed from one routine to another.
   But on occasions when we need :class:`pcm.FrameList` objects
   to be of a particular size, this class can accomplish that.

ReorderedPCMReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: ReorderedPCMReader(pcmreader, channel_order)

   This class wraps around an existing :class:`PCMReader` object.
   It takes a list of channel number integers
   (which should be the same as ``pcmreader``'s channel count)
   and reorders channels upon each call to :meth:`read`.

   For example, to swap channels 0 and 1 in a stereo stream,
   one could do the following:

   >>> reordered = ReorderedPCMReader(original, [1, 0])

   Calls to ``reordered.read()`` will then have the left channel
   on the right side and vice versa.

PCMCat Objects
^^^^^^^^^^^^^^

.. class:: PCMCat(pcmreaders)

   This class wraps around an iterable group of :class:`PCMReader` objects
   and concatenates their output into a single output stream.

.. warning::

   :class:`PCMCat` does not check that its input :class:`PCMReader` objects
   all have the same sample rate, channels, channel mask or bits-per-sample.
   Mixing incompatible readers is likely to trigger undesirable behavior
   from any sort of processing - which often assumes data will be in a
   consistent format.

ReplayGainReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: ReplayGainReader(pcmreader, gain, peak)

   This class wraps around an existing :class:`PCMReader` object.
   It takes floating point ``gain`` and ``peak`` values
   and modifies the pcmreader's output as necessary
   to match those values.
   This has the effect of raising or lowering a stream's sound volume
   to ReplayGain's reference value.

ChannelMask Objects
-------------------

.. class:: ChannelMask(mask)

   This is an integer-like class that abstracts channel assignments
   into a set of bit fields.

   ======= =========================
   Mask    Speaker
   ------- -------------------------
   0x1     ``front_left``
   0x2     ``front_right``
   0x4     ``front_center``
   0x8     ``low_frequency``
   0x10    ``back_left``
   0x20    ``back_right``
   0x40    ``front_left_of_center``
   0x80    ``front_right_of_center``
   0x100   ``back_center``
   0x200   ``side_left``
   0x400   ``side_right``
   0x800   ``top_center``
   0x1000  ``top_front_left``
   0x2000  ``top_front_center``
   0x4000  ``top_front_right``
   0x8000  ``top_back_left``
   0x10000 ``top_back_center``
   0x20000 ``top_back_right``
   ======= =========================

   All channels in a :class:`pcm.FrameList` will be in RIFF WAVE order
   as a sensible convention.
   But which channel corresponds to which speaker is decided by this mask.
   For example, a 4 channel PCMReader with the channel mask ``0x33``
   corresponds to the bits ``00110011``

   Reading those bits from right to left (least significant first)
   the ``front_left``, ``front_right``, ``back_left``, ``back_right``
   speakers are set.
   Therefore, the PCMReader's 4 channel FrameLists are laid out as follows:

   0. ``front_left``
   1. ``front_right``
   2. ``back_left``
   3. ``back_right``

   Since the ``front_center`` and ``low_frequency`` bits are not set,
   those channels are skipped in the returned FrameLists.

   Many formats store their channels internally in a different order.
   Their :class:`PCMReader` objects will be expected to reorder channels
   and set a :class:`ChannelMask` matching this convention.
   And, their :func:`from_pcm` classmethods will be expected
   to reverse the process.

   A :class:`ChannelMask` of 0 is "undefined",
   which means that channels aren't assigned to *any* speaker.
   This is an ugly last resort for handling formats
   where multi-channel assignments aren't properly defined.
   In this case, a :func:`from_pcm` classmethod is free to assign
   the undefined channels any way it likes, and is under no obligation
   to keep them undefined when passing back out to :meth:`to_pcm`

.. method:: ChannelMask.defined()

   Returns ``True`` if this mask is defined.

.. method:: ChannelMask.undefined()

   Returns ``True`` if this mask is undefined.

.. method:: ChannelMask.channels()

   Returns the speakers this mask contains as a list of strings
   in the order they appear in the PCM stream.

.. method:: ChannelMask.index(channel_name)

   Given a channel name string, returns the index of that channel
   within the PCM stream.
   For example:

   >>> mask = ChannelMask(0xB)     #fL, fR, LFE, but no fC
   >>> mask.index("low_frequency")
   2

.. classmethod:: ChannelMask.from_fields(**fields)

   Takes channel names as function arguments and returns a
   :class:`ChannelMask` object.

   >>> mask = ChannelMask.from_fields(front_right=True,
   ...                                front_left=True,
   ...                                front_center=True)
   >>> int(mask)
   7

.. classmethod:: ChannelMask.from_channels(channel_count)

   Takes a channel count integer and returns a :class:`ChannelMask` object.

.. warning::

   :func:`from_channels` *only* works for 1 and 2 channel counts
   and is meant purely as a convenience method for mono or stereo streams.
   All other values will trigger a :exc:`ValueError`

CDDA Objects
------------

.. class:: CDDA(device[, speed])

   This class is used to access a CD-ROM device.
   It functions as a list of :class:`CDTrackReader` objects,
   each representing a CD track and starting from index 1.

   >>> cd = CDDA("/dev/cdrom")
   >>> len(cd)
   17
   >>> cd[1]
   <audiotools.CDTrackReader instance at 0x170def0>
   >>> cd[17]
   <audiotools.CDTrackReader instance at 0x1341b00>

.. method:: CDDA.length()

   The length of the entire CD, in sectors.

.. method:: CDDA.first_sector()

   The position of the first sector on the CD, typically 0.

.. method:: CDDA.last_sector()

   The position of the last sector on the CD.

CDTrackReader Objects
^^^^^^^^^^^^^^^^^^^^^

.. class:: CDTrackReader(cdda, track_number)

   These objects are usually retrieved from :class:`CDDA` objects
   rather than instantiated directly.
   Each is a :class:`PCMReader`-compatible object
   with a few additional methods specific to CD reading.

.. data:: CDTrackReader.rip_log

   A :class:`CDTrackLog` object indicating cdparanoia's
   results from reading this track from the CD.
   This attribute should be checked only after the track
   has been fully read.

.. method:: CDTrackReader.offset()

   Returns the offset of this track within the CD, in sectors.

.. method:: CDTrackReader.length()

   Returns the total length of this track, in sectors.

CDTrackLog Objects
^^^^^^^^^^^^^^^^^^

.. class:: CDTrackLog()

   This is a dictionary-like object which should be retrieved
   from :class:`CDTrackReader` rather than instantiated directly.
   Its :meth:`__str__` method will return a human-readable
   collection of error statistics comparable to what's
   returned by the cdda2wav program.

ExecQueue Objects
-----------------

.. class:: ExecQueue()

   This is a class for executing multiple Python functions in
   parallel across multiple CPUs.

.. method:: ExecQueue.execute(function, args[, kwargs])

   Queues a Python function, list of arguments and optional
   dictionary of keyword arguments.

.. method:: ExecQueue.run([max_processes])

   Executes all queued Python functions, running ``max_processes``
   number of functions at a time until the entire queue is empty.
   This operates by forking a new subprocess per function,
   executing that function and then, regardless of the function's result,
   the child job performs an unconditional exit.

   This means that any side effects of executed functions have
   no effect on ExecQueue's caller besides those which modify
   files on disk (encoding an audio file, for example).

Messenger Objects
-----------------

.. class:: Messenger(executable_name, options)

   This is a helper class for displaying program data,
   analagous to a primitive logging facility.
   It takes a raw ``executable_name`` string and
   :class:`optparse.OptionParser` object.
   Its behavior changes depending on whether the
   ``options`` object's ``verbosity`` attribute is
   ``"normal"``, ``"debug"`` or ``"silent"``.

.. method:: Messenger.output(string)

   Outputs Unicode ``string`` to stdout and adds a newline,
   unless ``verbosity`` level is ``"silent"``.

.. method:: Messenger.partial_output(string)

   Output Unicode ``string`` to stdout and flushes output
   so it is displayed, but does not add a newline.
   Does nothing if ``verbosity`` level is ``"silent"``.

.. method:: Messenger.info(string)

   Outputs Unicode ``string`` to stdout and adds a newline,
   unless ``verbosity`` level is ``"silent"``.

.. method:: Messenger.partial_info(string)

   Output Unicode ``string`` to stdout and flushes output
   so it is displayed, but does not add a newline.
   Does nothing if ``verbosity`` level is ``"silent"``.

.. note::

   What's the difference between :meth:`Messenger.output` and :meth:`Messenger.info`?
   :meth:`Messenger.output` is for a program's primary data.
   :meth:`Messenger.info` is for incidental information.
   For example, trackinfo uses :meth:`Messenger.output` for what it
   displays since that output is its primary function.
   But track2track uses :meth:`Messenger.info` for its lines of progress
   since its primary function is converting audio
   and tty output is purely incidental.

.. method:: Messenger.warning(string)

   Outputs warning text, Unicode ``string`` and a newline to stderr,
   unless ``verbosity`` level is ``"silent"``.

   >>> m = audiotools.Messenger("audiotools",options)
   >>> m.warning(u"Watch Out!")
   *** Warning: Watch Out!

.. method:: Messenger.error(string)

   Outputs error text, Unicode ``string`` and a newline to stderr.

   >>> m.error(u"Fatal Error!")
   *** Error: Fatal Error!

.. method:: Messenger.usage(string)

   Outputs usage text, Unicode ``string`` and a newline to stderr.

   >>> m.usage(u"<arg1> <arg2> <arg3>")
   *** Usage: audiotools <arg1> <arg2> <arg3>

.. method:: Messenger.filename(string)

   Takes a raw filename string and converts it to a Unicode string.

.. method:: Messenger.new_row()

   This method begins the process of creating aligned table data output.
   It sets up a new row in our output table to which we can add
   columns of text which will be aligned automatically upon completion.

.. method:: Messenger.output_column(string[, right_aligned])

   This method adds a new Unicode string to the currently open row.
   If ``right_aligned`` is ``True``, its text will be right-aligned
   when it is displayed.
   When you've finished with one row and wish to start on another,
   call :meth:`Messenger.new_row` again.

.. method:: Messenger.blank_row()

   This method adds a completely blank row to its table data.
   Note that the first row within an output table cannot be blank.

.. method:: Messenger.output_rows()

   Formats and displays the entire table data through the
   :meth:`Messenger.output` method (which will do nothing
   if ``verbosity`` level is ``"silent"``).

   >>> m.new_row()
   >>> m.output_column(u"a",True)
   >>> m.output_column(u" : ",True)
   >>> m.output_column(u"This is some test data")
   >>> m.new_row()
   >>> m.output_column(u"ab",True)
   >>> m.output_column(u" : ",True)
   >>> m.output_column(u"Another row of test data")
   >>> m.new_row()
   >>> m.output_column(u"abc",True)
   >>> m.output_column(u" : ",True)
   >>> m.output_column(u"The final row of test data")
   >>> m.output_rows()
     a : This is some test data
    ab : Another row of test data
   abc : The final row of test data

