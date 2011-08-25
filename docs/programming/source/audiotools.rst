:mod:`audiotools` --- the Base Python Audio Tools Module
========================================================

.. module:: audiotools
   :synopsis: the Base Python Audio Tools Module


The :mod:`audiotools` module contains a number of useful base
classes and functions upon which all of the other modules depend.


.. data:: VERSION

   The current Python Audio Tools version as a plain string.

.. data:: AVAILABLE_TYPES

   A tuple of :class:`AudioFile`-compatible classes of available
   audio types.
   Note these are types available to audiotools, not necessarily
   available to the user - depending on whether the required binaries
   are installed or not.

   ============= ==================================
   Class         Format
   ------------- ----------------------------------
   AACAudio      AAC in ADTS container
   AiffAudio     Audio Interchange File Format
   ALACAudio     Apple Lossless
   AuAudio       Sun Au
   FlacAudio     Native Free Lossless Audio Codec
   M4AAudio      AAC in M4A container
   MP3Audio      MPEG-1 Layer 3
   MP2Audio      MPEG-1 Layer 2
   OggFlacAudio  Ogg Free Lossless Audio Codec
   ShortenAudio  Shorten
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
   Raises :exc:`UnsupportedFile` if the file cannot identified or is
   not supported.
   Raises :exc:`IOError` if the file cannot be opened at all.

.. function:: open_files(filenames[, sorted[, messenger]])

   Given a list of filename strings, returns a list of
   :class:`AudioFile`-compatible objects which can be successfully opened.
   By default, they are returned sorted by album number and track number.
   If ``sorted`` is ``False``, they are returned in the same order
   as they appear in the filenames list.
   If ``messenger`` is given, use that :class:`Messenger` object
   to for warnings if files cannot be opened.
   Otherwise, such warnings are sent to stdout.

.. function:: open_directory(directory[, sorted[, messenger]])

   Given a root directory, returns an iterator of all the
   :class:`AudioFile`-compatible objects found via a recursive
   search of that directory.
   ``sorted``, and ``messenger`` work as in :func:`open_files`.

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

   This function takes two functions, presumably analogous
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

.. function:: pcm_frame_cmp(pcmreader1, pcmreader2)

   This function takes two :class:`PCMReader` objects and compares
   their PCM frame output.
   It returns the frame number of the first mismatch as an integer
   which begins at frame number 0.
   If the two streams match completely, it returns ``None``.
   May raise :exc:`IOError` or :exc:`ValueError` if problems
   occur during reading.

.. function:: pcm_split(pcmreader, pcm_lengths)

   Takes a :class:`PCMReader` object and list of PCM sample length integers.
   Returns an iterator of new :class:`PCMReader` objects,
   each limited to the given lengths.
   The original pcmreader is closed upon the iterator's completion.

.. function:: applicable_replay_gain(audiofiles)

   Takes a list of :class:`AudioFile`-compatible objects.
   Returns ``True`` if ReplayGain can be applied to those files
   based on their sample rate, number of channels, and so forth.
   Returns ``False`` if not.

.. function:: calculate_replay_gain(audiofiles)

   Takes a list of :class:`AudioFile`-compatible objects.
   Returns an iterator of
   ``(audiofile, track_gain, track_peak, album_gain, album_peak)``
   tuples or raises :exc:`ValueError` if a problem occurs during calculation.

.. function:: read_metadata_file(path)

   Given a path to a FreeDB XMCD file or MusicBrainz XML file,
   returns an :class:`AlbumMetaDataFile`-compatible object
   or raises a :exc:`MetaDataFileException` if the file cannot be
   read or parsed correctly.

.. function:: read_sheet(filename)

   Reads a Cuesheet-compatible file such as :class:`toc.TOCFile` or
   :class:`cue.Cuesheet` or raises :exc:`SheetException` if
   the file cannot be opened, identified or parsed correctly.

.. function:: to_pcm_progress(audiofile, progress)

   Given an :class:`AudioFile`-compatible object and ``progress``
   function, returns a :class:`PCMReaderProgress` object
   of that object's PCM stream.

   If ``progress`` is ``None``, the audiofile's PCM stream
   is returned as-is.

AudioFile Objects
-----------------

.. class:: AudioFile()

   The :class:`AudioFile` class represents an audio file on disk,
   such as a FLAC file, MP3 file, WAVE file and so forth.
   It is not meant to be instantiated directly.  Instead, functions
   such as :func:`open` will return :class:`AudioFile`-compatible
   objects with the following attributes and methods.

.. attribute:: AudioFile.NAME

   The name of the format as a string.
   This is how the format is referenced by utilities via the `-t` option,
   and must be unique among all formats.

.. attribute:: AudioFile.SUFFIX

   The default file suffix as a string.
   This is used by the ``%(suffix)s`` format field in the
   :meth:`track_name` classmethod, and by the :func:`filename_to_type`
   function for inferring the file format from its name.
   However, it need not be unique among all formats.

.. attribute:: AudioFile.COMPRESSION_MODES

   A tuple of valid compression level strings, for use with the
   :meth:`from_pcm` and :meth:`convert` methods.
   If the format has no compression levels, this tuple will be empty.

.. attribute:: AudioFile.DEFAULT_COMPRESSION

   A string of the default compression level to use
   with :meth:`from_pcm` and :meth:`convert`, if none is given.
   This is *not* the default compression indicated in the user's
   configuration file; it is a hard-coded value of last resort.

.. attribute:: AudioFile.COMPRESSION_DESCRIPTIONS

   A dict of compression descriptions, as unicode strings.
   The key is a valid compression mode string.
   Not all compression modes need have a description;
   some may be left blank.

.. attribute:: AudioFile.BINARIES

   A tuple of binary strings required by the format.
   For example, the Vorbis format may require ``"oggenc"`` and ``"oggdec"``
   in order to be available for the user.

.. attribute:: AudioFile.REPLAYGAIN_BINARIES

   A tuple of binary strings required for ReplayGain application.
   For example, the Vorbis format may require ``"vorbisgain"`` in
   order to use the :meth:`add_replay_gain` classmethod.
   This tuple may be empty if the format requires no binaries
   or has no ReplayGain support.

.. classmethod:: AudioFile.is_type(file)

   Takes a file-like object with :meth:`read` and :meth:`seek` methods
   that's reset to the beginning of the stream.
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

.. method:: AudioFile.seconds_length()

   Returns the length of this audio file as a :class:`decimal.Decimal`
   number of seconds.

.. method:: AudioFile.lossless()

   Returns ``True`` if the data in the audio file has been stored losslessly.
   Returns ``False`` if not.

.. method:: AudioFile.set_metadata(metadata)

   Takes a :class:`MetaData`-compatible object and sets this audio file's
   metadata to that value, if possible.
   Raises :exc:`IOError` if a problem occurs when writing the file.

.. method:: AudioFile.update_metadata(metadata)

   Takes the :class:`MetaData`-compatible object returned by this
   audio file's :meth:`AudioFile.get_metadata` method
   and sets this audiofile's metadata to that value, if possible.
   Raises :exc:`IOError` if a problem occurs when writing the file.

.. note::

   What's the difference between :meth:`AudioFile.set_metadata`
   and :meth:`AudioFile.update_metadata`?

   Metadata implementations may also contain side information
   such as track length, file encoder, and so forth.
   :meth:`AudioFile.set_metadata` presumes the :class:`MetaData`
   object is from a different :class:`AudioFile` object or has
   been built from scratch.
   Therefore, it will update the newly added
   metadata side info as needed so as to not break the file.

   :meth:`AudioFile.update_metadata` presumes the :class:`MetaData`
   object is either taken from the original :class:`AudioFile` object
   or has been carefully constructed to not break anything when
   applied to the file.
   It is a lower-level routine which does *not* update metadata side info
   (which may be necessary when modifying that side info is required).

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
   May return a :class:`PCMReaderError` if an error occurs
   initializing the decoder.

.. classmethod:: AudioFile.from_pcm(filename, pcmreader[, compression])

   Takes a filename string, :class:`PCMReader`-compatible object
   and optional compression level string.
   Creates a new audio file as the same format as this audio class
   and returns a new :class:`AudioFile`-compatible object.
   Raises :exc:`EncodingError` if a problem occurs during encoding.

   In this example, we'll transcode ``track.flac`` to ``track.mp3``
   at the default compression level:

   >>> audiotools.MP3Audio.from_pcm("track.mp3",
   ...                              audiotools.open("track.flac").to_pcm())

.. method:: AudioFile.convert(filename, target_class[, compression[, progress]])

   Takes a filename string, :class:`AudioFile` subclass
   and optional compression level string.
   Creates a new audio file and returns an object of the same class.
   Raises :exc:`EncodingError` if a problem occurs during encoding.

   In this example, we'll transcode ``track.flac`` to ``track.mp3``
   at the default compression level:

   >>> audiotools.open("track.flac").convert("track.mp3",
   ...                                       audiotools.MP3Audio)

   Why have both a ``convert`` method as well as ``to_pcm``/``from_pcm``
   methods?
   Although the former is often implemented using the latter,
   the pcm methods alone contain only raw audio data.
   By comparison, the ``convert`` method has information about
   what is the file is being converted to and can transfer other side data
   if necessary.

   For example, if .wav file with non-audio RIFF chunks is
   converted to WavPack, this method will preserve those chunks:

   >>> audiotools.open("chunks.wav").convert("chunks.wv",
   ...                                       audiotools.WavPackAudio)

   whereas the ``to_pcm``/``from_pcm`` method alone will not.

   The optional ``progress`` argument is a function which takes
   two integer arguments: ``amount_processed`` and ``total_amount``.
   If supplied, this function is called at regular intervals
   during the conversion process and may be used to indicate
   the current status to the user.
   Note that these numbers are only meaningful when compared
   to one another; ``amount`` may represent PCM frames, bytes
   or anything else.
   The only restriction is that ``total_amount`` will remain
   static during processing and ``amount_processed`` will
   progress from 0 to ``total_amount``.

   >>> def print_progress(x, y):
   ...   print "%d%%" % (x * 100 / y)
   ...
   >>> audiotools.open("track.flac").convert("track.wv",
   ...                                       audiotools.WavPackAudio,
   ...                                       progress=print_progress)

.. method:: AudioFile.verify([progress])

   Verifies the track for correctness.
   Returns ``True`` if verification is successful.
   Raises an :class:`InvalidFile` subclass if some problem is detected.
   If the file has built-in checksums or other error detection
   capabilities, this method checks those values to ensure it has not
   been damaged in some way.

   The optional ``progress`` argument functions identically
   to the one provided to :meth:`convert`.
   That is, it takes a two integer argument function which is called
   at regular intervals to indicate the status of verification.

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

.. classmethod:: AudioFile.track_name(file_path[, track_metadata[, format[, suffix]]])

   Given a file path string and optional :class:`MetaData`-compatible object
   a UTF-8 encoded Python format string, and an ASCII-encoded suffix string,
   returns a filename string with the format string fields filled-in.
   If not provided by metadata, ``track_number`` and ``album_number``
   will be determined from ``file_path``, if possible.
   Raises :exc:`UnsupportedTracknameField` if the format string contains
   unsupported fields.

   Currently supported fields are:

   ========================== ===============================================
   Field                      Value
   -------------------------- -----------------------------------------------
   ``%(album_name)s``         ``track_metadata.album_name``
   ``%(album_number)s``       ``track_metadata.album_number``
   ``%(album_total)s``        ``track_metadata.album_total``
   ``%(album_track_number)s`` ``album_number`` combined with ``track_number``
   ``%(artist_name)s``        ``track_metadata.artist_name``
   ``%(catalog)s``            ``track_metadata.catalog``
   ``%(comment)s``            ``track_metadata.comment``
   ``%(composer_name)s``      ``track_metadata.composer_name``
   ``%(conductor_name)s``     ``track_metadata.conductor_name``
   ``%(copyright)s``          ``track_metadata.copyright``
   ``%(date)s``               ``track_metadata.date``
   ``%(ISRC)s``               ``track_metadata.ISRC``
   ``%(media)s``              ``track_metadata.year``
   ``%(performer_name)s``     ``track_metadata.performer_name``
   ``%(publisher)s``          ``track_metadata.publisher``
   ``%(suffix)s``             the :class:`AudioFile` suffix
   ``%(track_name)s``         ``track_metadata.track_name``
   ``%(track_number)2.2d``    ``track_metadata.track_number``
   ``%(track_total)s``        ``track_metadata.track_total``
   ``%(year)s``               ``track_metadata.year``
   ``%(basename)s``           ``file_path`` basename without suffix
   ========================== ===============================================

.. classmethod:: AudioFile.add_replay_gain(filenames[, progress])

   Given a list of filename strings of the same class as this
   :class:`AudioFile` class, calculates and adds ReplayGain metadata
   to those files.
   Raises :exc:`ValueError` if some problem occurs during ReplayGain
   calculation or application.
   ``progress``, if indicated, is a function which takes two arguments
   that is called as needed during ReplayGain application to indicate
   progress - identical to the argument used by :meth:`convert`.

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

.. method:: AudioFile.clean(fixes_performed[, output_filename])

   Cleans the audio file of known data and metadata problems.
   ``fixes_performed`` is a list-like object which is appended
   with unicode strings of the fixes performed.

   ``output_filename`` is an optional string in which the fixed
   audio file is placed.
   If omitted, no actual fixes are performed.
   Note that this method never modifies the original file.

   Raises :exc:`IOError` if some error occurs when writing the new file.

.. classmethod:: AudioFile.has_binaries(system_binaries)

   Takes the :attr:`audiotools.BIN` object of system binaries.
   Returns ``True`` if all the binaries necessary to implement
   this :class:`AudioFile`-compatible class are present and executable.
   Returns ``False`` if not.

WaveContainer Objects
^^^^^^^^^^^^^^^^^^^^^

This is an abstract :class:`AudioFile` subclass suitable
for extending by formats that store RIFF WAVE chunks internally,
such as Wave, FLAC, WavPack and Shorten.
It overrides the :meth:`AudioFile.convert` method such that
any stored chunks are transferred properly from one file to the next.
This is accomplished by implementing three additional methods.

.. class:: WaveContainer

.. method:: WaveContainer.to_wave(wave_filename[, progress])

   Creates a Wave file with the given filename string
   from our data, with any stored chunks intact.
   ``progress``, if given, functions identically to the
   :meth:`AudioFile.convert` method.
   May raise :exc:`EndodingError` if some problem occurs during encoding.

.. classmethod:: WaveContainer.from_wave(filename, wave_filename[, compression[, progress]])

   Like :meth:`AudioFile.from_pcm`, creates a file with our class
   at the given ``filename`` string, from the given ``wave_filename``
   string and returns a new object of our class.
   ``compression`` is an optional compression level string
   and ``progress`` functions identically to that of
   :meth:`AudioFile.convert`.
   May raise :exc:`EndodingError` if some problem occurs during encoding.

.. method:: WaveContainer.has_foreign_riff_chunks()

   Returns ``True`` if our object has non-audio RIFF WAVE chunks.

AiffContainer Objects
^^^^^^^^^^^^^^^^^^^^^

Much like :class:`WaveContainer`, this is an abstract
:class:`AudioFile` subclass suitable
for extending by formats that store AIFF chunks internally,
such as AIFF, FLAC and Shorten.
It overrides the :meth:`AudioFile.convert` method such that
any stored chunks are transferred properly from one file to the next.
This is accomplished by implementing three additional methods.

.. class:: AiffContainer

.. method:: AiffContainer.to_aiff(aiff_filename[, progress])

   Creates an AIFF file with the given filename string
   from our data, with any stored chunks intact.
   ``progress``, if given, functions identically to the
   :meth:`AudioFile.convert` method.
   May raise :exc:`EndodingError` if some problem occurs during encoding.

.. classmethod:: AiffContainer.from_aiff(filename, aiff_filename[, compression[, progress]])

   Like :meth:`AudioFile.from_pcm`, creates a file with our class
   at the given ``filename`` string, from the given ``aiff_filename``
   string and returns a new object of our class.
   ``compression`` is an optional compression level string
   and ``progress`` functions identically to that of
   :meth:`AudioFile.convert`.
   May raise :exc:`EndodingError` if some problem occurs during encoding.

.. method:: AiffContainer.has_foreign_aiff_chunks()

   Returns ``True`` if our object has non-audio AIFF chunks.

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

.. method:: MetaData.clean(fixes_performed)

   Returns a new :class:`MetaData` object of the same class
   that's been cleaned of known problems including, but not limited to

   * Leading whitespace in text fields
   * Trailing whitespace in text fields
   * Empty fields
   * Leading zeroes in numerical fields
   * Incorrectly labeled image metadata fields

   ``fixes_performed`` is a list object with an append method.
   Text descriptions of the fixes performed are appended
   to that list as unicode strings.

.. method:: MetaData.raw_info()

   Returns a unicode string of raw metadata information
   with as little filtering as possible.
   This is meant to be useful for debugging purposes.

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

AlbumMetaDataFile Objects
-------------------------

.. class:: AlbumMetaDataFile(album_name, artist_name, year, catalog, extra, track_metadata)

   This is an abstract parent class to :class:`audiotools.XMCD` and
   :class:`audiotools.MusicBrainzReleaseXML`.
   It represents a collection of album metadata as generated
   by the FreeDB or MusicBrainz services.
   Modifying fields within an :class:`AlbumMetaDataFile`-compatible
   object will modify its underlying representation and those
   changes will be present when :meth:`to_string` is called
   on the updated object.
   Note that :class:`audiotools.XMCD` doesn't support the `catalog`
   field while :class:`audiotools.MusicBrainzReleaseXML` doesn't
   support the `extra` fields.

.. data:: AlbumMetaDataFile.album_name

   The album's name as a Unicode string.

.. data:: AlbumMetaDataFile.artist_name

   The album's artist's name as a Unicode string.

.. data:: AlbumMetaDataFile.year

   The album's release year as a Unicode string.

.. data:: AlbumMetaDataFile.catalog

   The album's catalog number as a Unicode string.

.. data:: AlbumMetaDataFile.extra

   The album's extra information as a Unicode string.

.. method:: AlbumMetaDataFile.__len__()

   The total number of tracks on the album.

.. method:: AlbumMetaDataFile.to_string()

   Returns the on-disk representation of the file as a binary string.

.. classmethod:: AlbumMetaDataFile.from_string(string)

   Given a binary string, returns an :class:`AlbumMetaDataFile` object
   of the same class.
   Raises :exc:`MetaDataFileException` if a parsing error occurs.

.. method:: AlbumMetaDataFile.get_track(index)

   Given a track index (starting from 0), returns a
   (`track_name`, `track_artist`, `track_extra`) tuple of Unicode strings.
   Raises :exc:`IndexError` if the requested track is out-of-bounds.

.. method:: AlbumMetaDataFile.set_track(index, track_name, track_artist, track_extra)

   Given a track index (starting from 0) and a set of Unicode strings,
   sets the appropriate track information.
   Raises :exc:`IndexError` if the requested track is out-of-bounds.

.. classmethod:: AlbumMetaDataFile.from_tracks(tracks)

   Given a set of :class:`AudioFile` objects, returns an
   :class:`AlbumMetaDataFile` object of the same class.
   All files are presumed to be from the same album.

.. classmethod:: AlbumMetaDataFile.from_cuesheet(cuesheet, total_frames, sample_rate[, metadata])

   Given a Cuesheet-compatible object with :meth:`catalog`,
   :meth:`IRSCs`, :meth:`indexes` and :meth:`pcm_lengths` methods;
   `total_frames` and `sample_rate` integers; and an optional
   :class:`MetaData` object of the entire album's metadata,
   returns an :class:`AlbumMetaDataFile` object of the same class
   constructed from that data.

.. method:: AlbumMetaDataFile.track_metadata(track_number)

   Given a `track_number` (starting from 1), returns a
   :class:`MetaData` object of that track's metadata.

   Raises :exc:`IndexError` if the track is out-of-bounds.

.. method:: AlbumMetaDataFile.get(track_number, default)

   Given a `track_number` (starting from 1), returns a
   :class:`MetaData` object of that track's metadata,
   or returns `default` if that track is not present.

.. method:: AlbumMetaDataFile.track_metadatas()

   Returns an iterator over all the :class:`MetaData` objects
   in this file.

.. method:: AlbumMetaDataFile.metadata()

   Returns a single :class:`MetaData` object of all consistent fields
   in this file.
   For example, if `album_name` is the same in all MetaData objects,
   the returned object will have that `album_name` value.
   If `track_name` differs, the returned object have a blank
   `track_name` field.


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
   May raise :exc:`IOError` if there is a problem reading the
   source file, or :exc:`ValueError` if the source file has
   some sort of error.

.. method:: PCMReader.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.
   May raise a :exc:`DecodingError`, typically indicating that
   a helper subprocess used for decoding has exited with an error.

PCMReaderError Objects
^^^^^^^^^^^^^^^^^^^^^^

.. class:: PCMReaderError(error_message, sample_rate, channels, channel_mask, bits_per_sample)

   This is a subclass of :class:`PCMReader` which always returns empty
   :class:`pcm.FrameList` objects and always raises a :class:`DecodingError`
   with the given ``error_message`` when closed.
   The purpose of this is to postpone error generation so that
   all encoding errors, even those caused by unsuccessful decoding,
   are restricted to the :meth:`from_pcm` classmethod
   which can then propagate the :class:`DecodingError` error message
   to the user.

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

PCMReaderWindow Objects
^^^^^^^^^^^^^^^^^^^^^^^

.. class:: PCMReaderWindow(pcmreader, initial_offset, total_pcm_frames)

   This class wraps around an existing :class:`PCMReader` object
   and truncates or extends its samples as needed.
   ``initial_offset``, if positive, indicates how many
   PCM frames to truncate from the beginning of the stream.
   If negative, the beginning of the stream is padded by
   that many PCM frames - all of which have a value of 0.
   ``total_pcm_frames`` indicates the total length of the stream
   as a non-negative number of PCM frames.
   If shorter than the actual length of the PCM reader's stream,
   the reader is truncated.
   If longer, the stream is extended by as many PCM frames as needed.
   Again, padding frames have a value of 0.

LimitedPCMReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: LimitedPCMReader(buffered_pcmreader, total_pcm_frames)

   This class wraps around an existing :class:`BufferedPCMReader`
   and ensures that no more than ``total_pcm_frames`` will be read
   from that stream by limiting reads to it.

.. note::

   :class:`PCMReaderWindow` is designed primarly for handling
   sample offset values in a :class:`CDTrackReader`,
   or for skipping a potentially large number of samples
   in a stream.
   :class:`LimitedPCMReader` is designed for splitting a
   stream into several smaller streams without losing any PCM frames.

   Which to use for a given situation depends on whether one cares
   about consuming the samples outside of the sub-reader or not.

PCMReaderProgress Objects
^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: PCMReaderProgress(pcmreader, total_frames, progress)

   This class wraps around an existing :class:`PCMReader` object
   and generates periodic updates to a given ``progress`` function.
   ``total_frames`` indicates the total number of PCM frames
   in the PCM stream.

   >>> progress_display = SingleProgressDisplay(Messenger("audiotools"), u"encoding file")
   >>> pcmreader = source_audiofile.to_pcm()
   >>> source_frames = source_audiofile.total_frames()
   >>> target_audiofile = AudioType.from_pcm("target_filename",
   ...                                       PCMReaderProgress(pcmreader,
   ...                                                         source_frames,
   ...                                                         progress_display.update))


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

.. class:: CDDA(device[, speed[, perform_logging]])

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

   If ``True``, ``perform_logging`` indicates that track reads
   should generate :class:`CDTrackLog` entries.
   Otherwise, no logging is performed.

.. warning::

   ``perform_logging`` also determines the level of multithreading allowed
   during CD reading.
   If logging is active, :class:`CDTrackReader`'s read method
   will block all other threads until the read is complete.
   If logging is inactive, a read will not block other threads.
   This is an unfortunate necessity due to libcdio's callback
   mechanism implementation.

.. method:: CDDA.length()

   The length of the entire CD, in sectors.

.. method:: CDDA.first_sector()

   The position of the first sector on the CD, typically 0.

.. method:: CDDA.last_sector()

   The position of the last sector on the CD.

CDTrackReader Objects
^^^^^^^^^^^^^^^^^^^^^

.. class:: CDTrackReader(cdda, track_number[, perform_logging])

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

DVDAudio Objects
----------------

.. class:: DVDAudio(audio_ts_path[, device])

   This class is used to access a DVD-Audio.
   It contains a collection of titlesets.
   Each titleset contains a list of :class:`DVDATitle` objects,
   and each :class:`DVDATitle` contains a list of
   :class:`DVDATrack` objects.
   ``audio_ts_path`` is the path to the DVD-Audio's
   ``AUDIO_TS`` directory, such as ``/media/cdrom/AUDIO_TS``.
   ``device`` is the path to the DVD-Audio's mount device,
   such as ``/dev/cdrom``.

   For example, to access the 3rd :class:`DVDATrack` object
   of the 2nd :class:`DVDATitle` of the first titleset,
   one can simply perform the following:

   >>> track = DVDAudio(path)[0][1][2]

.. note::

   If ``device`` is indicated *and* the ``AUDIO_TS`` directory
   contains a ``DVDAUDIO.MKB`` file, unprotection will be
   performed automatically if supported on the user's platform.
   Otherwise, the files are assumed to be unprotected.

DVDATitle Objects
^^^^^^^^^^^^^^^^^

.. class:: DVDATitle(dvdaudio, titleset, title, pts_length, tracks)

   This class represents a single DVD-Audio title.
   ``dvdaudio`` is a :class:`DVDAudio` object.
   ``titleset`` and ``title`` are integers indicating
   this title's position in the DVD-Audio - both offset from 0.
   ``pts_length`` is the the total length of the title in
   PTS ticks (there are 90000 PTS ticks per second).
   ``tracks`` is a list of :class:`DVDATrack` objects.

   It is rarely instantiated directly; one usually
   retrieves titles from the parent :class:`DVDAudio` object.

.. data:: DVDATitle.dvdaudio

   The parent :class:`DVDAudio` object.

.. data:: DVDATitle.titleset

   An integer of this title's titleset, offset from 0.

.. data:: DVDATitle.title

   An integer of this title's position within the titleset, offset from 0.

.. data:: DVDATitle.pts_length

   The length of this title in PTS ticks.

.. data:: DVDATitle.tracks

   A list of :class:`DVDATrack` objects.

.. method:: DVDATitle.info()

   Returns a (``sample_rate``, ``channels``, ``channel_mask``,
   ``bits_per_sample``, ``type``) tuple of integers.
   ``type`` is ``0xA0`` if the title is a PCM stream,
   or ``0xA1`` if the title is an MLP stream.

.. method:: DVDATitle.stream()

   Returns an :class:`AOBStream` object of this title's data.

.. method:: DVDATitle.to_pcm()

   Returns a :class:`PCMReader`-compatible object of this title's
   entire data stream.

DVDATrack Objects
^^^^^^^^^^^^^^^^^

.. class:: DVDATrack(dvdaudio, titleset, title, track, first_pts, pts_length, first_sector, last_sector)

   This class represents a single DVD-Audio track.
   ``dvdaudio`` is a :class:`DVDAudio` object.
   ``titleset``, ``title`` and ``track`` are integers indicating
   this track's position in the DVD-Audio - all offset from 0.
   ``first_pts`` is the track's first PTS value.
   ``pts_length`` is the the total length of the track in PTS ticks.
   ``first_sector`` and ``last_sector`` indicate the range of
   sectors this track occupies.

   It is also rarely instantiated directly;
   one usually retrieves tracks from the parent
   :class:`DVDATitle` object.

.. data:: DVDATrack.dvdaudio

   The parent :class:`DVDAudio` object.

.. data:: DVDATrack.titleset

   An integer of this tracks's titleset, offset from 0.

.. data:: DVDATrack.title

   An integer of this track's position within the titleset, offset from 0.

.. data:: DVDATrack.track

   An integer of this track's position within the title, offset from 0.

.. data:: DVDATrack.first_pts

   The track's first PTS index.

.. data:: DVDATrack.pts_length

   The length of this track in PTS ticks.

.. data:: DVDATrack.first_sector

   The first sector this track occupies.

.. warning::

   The track is *not* guaranteed to start at the beginning of
   its first sector.
   Although it begins within that sector, the track's start may be
   offset some arbitrary number of bytes from the sector's start.

.. data:: DVDATrack.last_sector

   The last sector this track occupies.

AOBStream Objects
^^^^^^^^^^^^^^^^^

.. class:: AOBStream(aob_files, first_sector, last_sector[, unprotector])

   This is a stream of DVD-Audio AOB data.
   It contains several convenience methods to make
   unpacking that data easier.
   ``aob_files`` is a list of complete AOB file path strings.
   ``first_sector`` and ``last_sector`` are integers
   indicating the stream's range of sectors.
   ``unprotector`` is a function which takes a string
   of binary sector data and returns an unprotected binary string.

.. method:: AOBStream.sectors()

   Iterates over a series of 2048 byte, binary strings of sector data
   for the entire AOB stream.
   If ``unprotector`` is present, those sectors are returned unprotected.

.. method:: AOBStream.packets()

   Iterates over a series of packets by wrapping around the sectors
   iterator.
   Each sector contains one or more packets.
   Packets containing audio data (that is, those with a stream ID
   of ``0xBD``) are returned while non-audio packets are discarded.

.. method:: AOBStream.packet_payloads()

   Iterates over a series of packet data by wrapping around the
   packets iterator.
   The payload is the packet with its ID, CRC and padding removed.
   Concatenating all of a stream's payloads results
   in a complete MLP or PCM stream suitable for passing to
   a decoder.

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

.. class:: ExecQueue2()

   This is a class for executing multiple Python functions in
   parallel across multiple CPUs and receiving results
   from those functions.

.. method:: ExecQueue2.execute(function, args[, kwargs])

   Queues a Python function, list of arguments and optional
   dictionary of keyword arguments.

.. method:: ExecQueue2.run([max_processes])

   Executes all queued Python functions, running ``max_processes``
   number of functions at a time until the entire queue is empty.
   Returns an iterator of the returned values of those functions.
   This operates by forking a new subprocess per function
   with a pipe between them, executing that function in the child process
   and then transferring the resulting pickled object back to the parent
   before performing an unconditional exit.

   Queued functions that raise an exception or otherwise exit uncleanly
   yield ``None``.
   Likewise, any side effects of the called function have no
   effect on ExecQueue's caller.

ExecProgressQueue Objects
-------------------------

.. class:: ExecProgressQueue(progress_display[, total_progress_message])

   This class runs multiple jobs in parallel and displays their
   progress output to the given :class:`ProgressDisplay` object.
   The optional ``total_progress_message`` argument is a unicode string
   which displays an additional progress bar of the queue's total progress.

.. attribute:: ExecProgressQueue.results

   A dict of results returned by the queued functions once executed.
   The key is an integer starting from 0.

.. note::

   Why not a list?
   Since jobs may finish in an arbitrary order,
   a dict is used so that results can be accumulated out-of-order.
   Even using placeholder values such as ``None`` may not
   be appropriate if queued functions return ``None`` as
   a significant value.

.. method:: ExecProgressQueue.execute(function[, progress_text[, completion_output[, *args[, **kwargs]]]])

   Queues a Python function for execution.
   This function is passed the optional ``args`` and ``kwargs``
   arguments upon execution.
   However, this function is also passed an *additional* ``progress``
   keyword argument which is a function that takes ``current`` and
   ``total`` integer arguments.
   The executed function can then call that ``progress`` function
   at regular intervals to indicate its progress.

   If given, ``progress_text`` is a unicode string to be displayed
   while the function is being executed.

   ``completion_output`` is displayed once the executed function is
   completed.
   It can be either a unicode string or a function whose argument
   is the returned result of the executed function and which must
   output either a unicode string or ``None``.
   If ``None``, no output text is generated for the completed job.

.. method:: ExecProgressQueue.run([max_processes])

   Executes all the queued functions, running ``max_processes`` number
   of functions at a time until the entire queue is empty.
   This operates by forking a new subprocess per function
   in which the running progress and function output are
   piped to the parent for display to the screen or accumulation
   in the :attr:`ExecProgressQueue.results` dict.

   If an exception occurs in one of the subprocesses,
   that exception will be raised by :meth:`ExecProgressQueue.run`
   and all the running jobs will be terminated.

   >>> def progress_function(progress, filename):
   ...   # perform work here
   ...   progress(current, total)
   ...   # more work
   ...   result.a = a
   ...   result.b = b
   ...   result.c = c
   ...   return result
   ...
   >>> def format_result(result):
   ...    return u"%s %s %s" % (result.a, result.b, result.c)
   ...
   >>> queue = ExecProgressQueue(ProgressDisplay(Messenger("executable")))
   >>> queue.execute(function=progress_function,
   ...               progress_text=u"%s progress" % (filename1),
   ...               completion_output=format_result,
   ...               filename=filename1)
   ...
   >>> queue.execute(function=progress_function,
   ...               progress_text=u"%s progress" % (filename2),
   ...               completion_output=format_result,
   ...               filename=filename2)
   ...
   >>> queue.run()
   >>> queue.results


Messenger Objects
-----------------

.. class:: Messenger(executable_name, options)

   This is a helper class for displaying program data,
   analogous to a primitive logging facility.
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

.. method:: Messenger.os_error(oserror)

   Given an :class:`OSError` object, displays it as a properly formatted
   error message with an appended newline.

.. note::

   This is necessary because of the way :class:`OSError` handles
   its embedded filename string.
   Using this method ensures that filename is properly encoded when
   displayed.
   Otherwise, there's a good chance that non-ASCII filenames will
   be garbled.

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

.. method:: Messenger.info_rows()

   Functions like :meth:`Messenger.output_rows`,
   but displays output via :meth:`Messenger.info` rather than
   :meth:`Messenger.output`.

.. method:: Messenger.divider_row(dividers)

   This method takes a list of vertical divider Unicode characters,
   one per output column, and multiplies those characters by their
   column width when displayed.

   >>> m.new_row()
   >>> m.output_column(u"foo")
   >>> m.output_column(u" ")
   >>> m.output_column(u"bar")
   >>> m.divider_row([u"-",u" ",u"-"])
   >>> m.new_row()
   >>> m.output_column(u"test")
   >>> m.output_column(u" ")
   >>> m.output_column(u"column")
   >>> m.output_rows()
   foo  bar
   ---- ------
   test column

.. method:: Messenger.ansi(string, codes)

   Takes a Unicode string and list of ANSI SGR code integers.
   If ``stdout`` is to a TTY, returns a Unicode string
   formatted with those codes.
   If not, the string is returned as is.
   Codes can be taken from the many predefined values
   in the :class:`Messenger` class.
   Note that not all output terminals are guaranteed to support
   all ANSI escape codes.

.. method:: Messenger.ansi_err(string, codes)

   This is identical to ``Messenger.ansi``, but it checks whether
   ``stderr`` is a TTY instead of ``stdout``.

    ======================== ====================
    Code                     Effect
    ------------------------ --------------------
    ``Messenger.RESET``      resets current codes
    ``Messenger.BOLD``       bold font
    ``Messenger.FAINT``      faint font
    ``Messenger.ITALIC``     italic font
    ``Messenger.UNDERLINE``  underline text
    ``Messenger.BLINK_SLOW`` blink slowly
    ``Messenger.BLINK_FAST`` blink quickly
    ``Messenger.REVERSE``    reverse text
    ``Messenger.STRIKEOUT``  strikeout text
    ``Messenger.FG_BLACK``   foreground black
    ``Messenger.FG_RED``     foreground red
    ``Messenger.FG_GREEN``   foreground green
    ``Messenger.FG_YELLOW``  foreground yellow
    ``Messenger.FG_BLUE``    foreground blue
    ``Messenger.FG_MAGENTA`` foreground magenta
    ``Messenger.FG_CYAN``    foreground cyan
    ``Messenger.FG_WHITE``   foreground write
    ``Messenger.BG_BLACK``   background black
    ``Messenger.BG_RED``     background red
    ``Messenger.BG_GREEN``   background green
    ``Messenger.BG_YELLOW``  background yellow
    ``Messenger.BG_BLUE``    background blue
    ``Messenger.BG_MAGENTA`` background magenta
    ``Messenger.BG_CYAN``    background cyan
    ``Messenger.BG_WHITE``   background white
    ======================== ====================

.. method:: Messenger.ansi_clearline()

   Generates a ANSI escape codes to clear the current line.

   This works only if ``stdout`` is a TTY, otherwise is does nothing.

   >>> msg = Messenger("audiotools", None)
   >>> msg.partial_output(u"working")
   >>> time.sleep(1)
   >>> msg.ansi_clearline()
   >>> msg.output(u"done")

.. method:: Messenger.ansi_uplines(self, lines)

   Moves the cursor upwards by the given number of lines.

.. method:: Messenger.ansi_cleardown(self)

   Clears all the output below the current line.
   This is typically used in conjuction with :meth:`Messenger.ansi_uplines`.

   >>> msg = Messenger("audiotools", None)
   >>> msg.output(u"line 1")
   >>> msg.output(u"line 2")
   >>> msg.output(u"line 3")
   >>> msg.output(u"line 4")
   >>> time.sleep(2)
   >>> msg.ansi_uplines(4)
   >>> msg.ansi_cleardown()
   >>> msg.output(u"done")

.. method:: Messenger.terminal_size(fd)

   Given a file descriptor integer, or file object with a fileno() method,
   returns the size of the current terminal as a (``height``, ``width``)
   tuple of integers.

ProgressDisplay Objects
-----------------------

.. class:: ProgressDisplay(messenger)

   This is a class for displaying incremental progress updates to the screen.
   It takes a :class:`Messenger` object which is used for generating
   output.
   Whether or not :attr:`sys.stdout` is a TTY determines how
   this class operates.
   If a TTY is detected, screen updates are performed incrementally
   with individual rows generated and refreshed as needed using
   ANSI escape sequences such that the user's screen need not scroll.
   If a TTY is not detected, most progress output is omitted.

.. method:: ProgressDisplay.add_row(row_id, output_line)

   Adds a row of output to be displayed with progress indicated.
   ``row_id`` should be a unique identifier, typically an int.
   ``output_line`` should be a unicode string indicating what
   we're displaying the progress of.

.. method:: ProgressDisplay.update_row(row_id, current, total)

   Updates the progress of the given row.
   ``current`` and ``total`` are integers such that
   ``current`` / ``total`` indicates the percentage of progress performed.

.. method:: ProgressDisplay.refresh()

   Refreshes the screen output, clearing and displaying a fresh
   progress rows as needed.
   This is called automatically by :meth:`update_row`.

.. method:: ProgressDisplay.clear()

   Clears the screen output.
   Although :meth:`refresh` will call this method as needed,
   one may need to call it manually when generating
   output independently for the progress monitor
   so that partial updates aren't left on the user's screen.

.. method:: ProgressDisplay.delete_row(row_id)

   Removes the row with the given ID from the current list
   of progress monitors.

.. class:: SingleProgressDisplay(messenger, progress_text)

   This is a subclass of :class:`ProgressDisplay` used
   for generating only a single line of progress output.
   As such, one only specifies a single row of unicode ``progress_text``
   at initialization time and can avoid the row management functions
   entirely.

.. method:: SingleProgressDisplay.update(current, total)

   Updates the status of our output row with ``current`` and ``total``
   integers, which function identically to those of
   :meth:`ProgressDisplay.update_row`.

.. class:: ReplayGainProgressDisplay(messenger, lossless_replay_gain)

   This is another :class:`ProgressDisplay` subclass optimized
   for the display of ReplayGain application progress.
   ``messenger`` is a :class:`Messenger` object and
   ``lossless_replay_gain`` is a boolean indicating whether
   ReplayGain is being applied losslessly or not
   (which can be determined from the :meth:`AudioFile.lossless_replay_gain`
   classmethod).
   Whether or not :attr:`sys.stdout` is a TTY determines how
   this class behaves.

.. method:: ReplayGainProgressDisplay.initial_message()

   If operating on a TTY, this does nothing since progress output
   will be displayed.
   Otherwise, this indicates that ReplayGain application has begun.

.. method:: ReplayGainProgressDisplay.update(current, total)

   Updates the status of ReplayGain application.

.. method:: ReplayGainProgressDisplay.final_message()

   If operating on a TTY, this indicates that ReplayGain application
   is complete.
   Otherwise, this does nothing.

   >>> rg_progress = ReplayGainProgressDisplay(messenger, AudioType.lossless_replay_gain())
   >>> rg_progress.initial_message()
   >>> AudioType.add_replay_gain(filename_list, rg_progress.update)
   >>> rg_Progress.final_message()

.. class:: ProgressRow(row_id, output_line)

   This is used by :class:`ProgressDisplay` and its subclasses
   for actual output generation.
   ``row_id`` is a unique identifier and ``output_line`` is a unicode string.
   It is not typically instantiated directly.

.. method:: ProgressRow.update(current, total)

   Updates the current progress with ``current`` and ``total`` integer values.

.. method:: ProgressRow.unicode(width)

   Returns the output line and its current progress as a unicode string,
   formatted to the given width in onscreen characters.
   Screen width can be determined from the :meth:`Messenger.terminal_size`
   method.

display_unicode Objects
^^^^^^^^^^^^^^^^^^^^^^^

This class is for displaying portions of a unicode string to
the screen.
The reason this is needed is because not all Unicode characters
are the same width.
So, for example, if one wishes to display a portion of a unicode string to
a screen that's 80 ASCII characters wide, one can't simply perform:

>>> messenger.output(unicode_string[0:80])

since some of those Unicode characters might be double width,
which would cause the string to wrap.

.. class:: display_unicode(unicode_string)

.. method:: display_unicode.head(display_characters)

   Returns a new :class:`display_unicode` object that's been
   truncated to the given number of display characters.

   >>> s = u"".join(map(unichr, range(0x30a1, 0x30a1+25)))
   >>> len(s)
   25
   >>> u = unicode(display_unicode(s).head(40))
   >>> len(u)
   20
   >>> print repr(u)
   u'\u30a1\u30a2\u30a3\u30a4\u30a5\u30a6\u30a7\u30a8\u30a9\u30aa\u30ab\u30ac\u30ad\u30ae\u30af\u30b0\u30b1\u30b2\u30b3\u30b4'

.. method:: display_unicode.tail(display_characters)

   Returns a new :class:`display_unicode` object that's been
   truncated to the given number of display characters.

   >>> s = u"".join(map(unichr, range(0x30a1, 0x30a1+25)))
   >>> len(s)
   25
   >>> u = unicode(display_unicode(s).tail(40))
   >>> len(u)
   20
   >>> print repr(u)
   u'\u30a6\u30a7\u30a8\u30a9\u30aa\u30ab\u30ac\u30ad\u30ae\u30af\u30b0\u30b1\u30b2\u30b3\u30b4\u30b5\u30b6\u30b7\u30b8\u30b9'

.. method:: display_unicode.split(display_characters)

   Returns a tuple of :class:`display_unicode` objects.
   The first is up to ``display_characters`` wide,
   while the second contains the remainder.

   >>> s = u"".join(map(unichr, range(0x30a1, 0x30a1+25)))
   >>> (head, tail) = display_unicode(s).split(40)
   >>> print repr(unicode(head))
   u'\u30a1\u30a2\u30a3\u30a4\u30a5\u30a6\u30a7\u30a8\u30a9\u30aa\u30ab\u30ac\u30ad\u30ae\u30af\u30b0\u30b1\u30b2\u30b3\u30b4'
   >>> print repr(unicode(tail))
   u'\u30b5\u30b6\u30b7\u30b8\u30b9'
