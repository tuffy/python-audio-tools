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
   OpusAudio     Opus Audio Codec
   ShortenAudio  Shorten
   SpeexAudio    Ogg Speex
   VorbisAudio   Ogg Vorbis
   WaveAudio     Waveform Audio File Format
   WavPackAudio  WavPack
   ============= ==================================

.. data:: DEFAULT_TYPE

   The default type to use as a plain string, such as ``'wav'`` or ``'flac'``.

.. data:: DEFAULT_QUALITY

   A dict of type name strings -> quality value strings
   indicating the default compression quality value for the given type
   name suitable for :meth:`AudioFile.from_pcm` and :meth:`AudioFile.convert`
   method calls.

.. data:: DEFAULT_CDROM

   The default CD-ROM device to use for CD audio and DVD-Audio
   extraction as a plain string.

.. data:: TYPE_MAP

   A dictionary of type name strings -> :class:`AudioFile`
   values containing only types which have all required binaries
   installed.

.. data:: FILENAME_FORMAT

   The default format string to use for newly created files.

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

.. data:: IO_ENCODING

   The defined encoding to use for output to the screen as a plain
   string.
   This is typically ``'utf-8'``.

.. data:: FS_ENCODING

   The defined encoding to use for filenames read and written to disk
   as a plain string.
   This is typically ``'utf-8'``.

.. data:: MAX_JOBS

   The maximum number of simultaneous jobs to run at once by default
   as an integer.
   This may be defined from the user's config file.
   Otherwise, if Python's ``multiprocessing`` module is available,
   this is set to the user's CPU count.
   If neither is available, this is set to 1.

.. function:: file_type(file)

   Given a seekable file object rewound to the file's start,
   returns an :class:`AudioFile`-compatible class of the stream's
   detected type, or ``None`` if the stream's type is unknown.

   The :class:`AudioFile` class may not be available for use
   and so its :meth:`AudioFile.available` classmethod
   may need to be checked separately.

.. function:: open(filename)

   Opens the given filename string and returns an :class:`AudioFile`-compatible
   object.
   Raises :exc:`UnsupportedFile` if the file cannot identified or is
   not supported.
   Raises :exc:`IOError` if the file cannot be opened at all.

.. function:: open_files(filenames[, sorted][, messenger][, no_duplicates][, warn_duplicates][, opened_files])

   Given a list of filename strings, returns a list of
   :class:`AudioFile`-compatible objects which are successfully opened.
   By default, they are returned sorted by album number and track number.

   If ``sorted`` is ``False``, they are returned in the same order
   as they appear in the filenames list.

   If ``messenger`` is given, use that :class:`Messenger` object
   to for warnings if files cannot be opened.
   Otherwise, such warnings are sent to stdout.

   If ``no_duplicates`` is ``True``, attempting to open
   the same file twice raises a :exc:`DuplicateFile` exception.

   If ``no_duplicates`` is ``False`` and ``warn_duplicates`` is ``True``,
   attempting to open the same file twice results in a
   warning to ``messenger``, if present.

   ``opened_files``, if present, is a set of previously opened
   :class:`Filename` objects for the purpose of detecting duplicates.
   Any opened files are added to that set.

.. function:: open_directory(directory[, sorted[, messenger]])

   Given a root directory, returns an iterator of all the
   :class:`AudioFile`-compatible objects found via a recursive
   search of that directory.
   ``sorted``, and ``messenger`` work as in :func:`open_files`.

.. function:: sorted_tracks(audiofiles)

   Given a list of :class:`AudioFile` objects,
   returns a new list of those objects sorted by
   album number and track number, if present.
   If album number and track number aren't present,
   objects are sorted by base filename.

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

   >>> infile = open("input.txt", "r")
   >>> outfile = open("output.txt", "w")
   >>> transfer_data(infile.read, outfile.write)
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

   Given a ``.cue`` or ``.toc`` filename, returns a :class:`Sheet`
   of that file's cuesheet data.
   May raise :exc:`SheetException` if the file cannot be read
   or parsed correctly.

.. function:: to_pcm_progress(audiofile, progress)

   Given an :class:`AudioFile`-compatible object and ``progress``
   function, returns a :class:`PCMReaderProgress` object
   of that object's PCM stream.

   If ``progress`` is ``None``, the audiofile's PCM stream
   is returned as-is.

Filename Objects
----------------

.. class:: Filename(filename)

   :class:`Filename` is a file which may or may not exist on disk.
   ``filename`` is a raw string of the actual filename.
   Filename objects are immutable and hashable,
   which means they can be used as dictionary keys
   or placed in sets.

   The purpose of Filename objects is for easier
   conversion of raw string filename paths to Unicode,
   and to make it easier to detect filenames
   which point to the same file on disk.

   The former case is used by utilities to display
   output about file operations in progress.
   The latter case is for utilities
   which need to avoid overwriting input files
   with output files.

.. function:: Filename.__str__()

   Returns the raw string of the actual filename after
   being normalized.

.. function:: Filename.__unicode__()

   Returns a Unicode string of the filename after being decoded
   through :attr:`FS_ENCODING`.

.. function:: Filename.__eq__(filename)

   Filename objects which exist on disk hash and compare equally
   if their device ID and inode number values match
   (the ``st_dev`` and ``st_ino`` fields according to stat(2)).
   Filename objects which don't exist on disk hash and compare
   equally if their filename string matches.

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

.. attribute:: AudioFile.DESCRIPTION

   A longer, descriptive name for the audio type as a Unicode string.
   This is meant to be human-readable.

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

   A dict of compression descriptions, as Unicode strings.
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

.. classmethod:: AudioFile.from_pcm(filename, pcmreader[, compression][, total_pcm_frames])

   Takes a filename string, :class:`PCMReader`-compatible object,
   optional compression level string and optional total_pcm_frames integer.
   Creates a new audio file as the same format as this audio class
   and returns a new :class:`AudioFile`-compatible object.
   Raises :exc:`EncodingError` if a problem occurs during encoding.

   Specifying the total number of PCM frames to be encoded,
   when the number is known in advance, may allow the encoder
   to work more efficiently but is never required.

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

.. classmethod:: AudioFile.supports_replay_gain()

   Returns ``True`` if this class supports ReplayGain metadata.

.. classmethod:: AudioFile.lossless_replay_gain()

   Returns ``True`` if this audio class applies ReplayGain via a
   lossless process - such as by adding a metadata tag of some sort.
   Returns ``False`` if applying metadata modifies the audio file
   data itself.

.. classmethod:: AudioFile.can_add_replay_gain(audiofiles)

   Given a list of :class:`AudioFile` objects,
   returns ``True`` if this class can run :meth:`AudioFile.add_replay_gain`
   on those objects, ``False`` if not.

.. method:: AudioFile.replay_gain()

   Returns this audio file's ReplayGain values as a
   :class:`ReplayGain` object, or ``None`` if this audio file has no values.

.. method:: AudioFile.set_cuesheet(cuesheet)

   Given a :class:`Sheet` object, embeds a cuesheet in the track.
   This is for tracks which represent a whole CD image
   and wish to store track break data internally.
   May raise :exc:`IOError` if an error occurs writing the file.

.. method:: AudioFile.get_cuesheet()

   Returns a :class:`Sheet` object of a track's embedded cuesheet,
   or ``None`` if the track contains no cuesheet.
   May raise :exc:`IOError` if an error occurs reading the file.

.. method:: AudioFile.clean([output_filename])

   Cleans the audio file of known data and metadata problems.

   ``output_filename`` is an optional string in which the fixed
   audio file is placed.
   If omitted, no actual fixes are performed.
   Note that this method never modifies the original file.

   Returns list of fixes performed as Unicode strings.

   Raises :exc:`IOError` if some error occurs when writing the new file.
   Raises :exc:`ValueError` if the file itself is invalid.

.. classmethod:: AudioFile.available(system_binaries)

   Takes the :attr:`audiotools.BIN` object of system binaries.
   Returns ``True`` if all the binaries necessary to implement
   this :class:`AudioFile`-compatible class are present and executable.
   Returns ``False`` if not.

.. classmethod:: AudioFile.missing_components(messenger)

   Takes a :class:`Messenger` object and displays missing binaries
   or libraries needed to support this format and where to get them,
   if any.

WaveContainer Objects
^^^^^^^^^^^^^^^^^^^^^

This is an abstract :class:`AudioFile` subclass suitable
for extending by formats that store RIFF WAVE chunks internally,
such as Wave, FLAC, WavPack and Shorten.
It overrides the :meth:`AudioFile.convert` method such that
any stored chunks are transferred properly from one file to the next.
This is accomplished by implementing three additional methods.

.. class:: WaveContainer

.. method:: WaveContainer.has_foreign_wave_chunks()

   Returns ``True`` if our object has non-audio RIFF WAVE chunks.

.. method:: WaveContainer.wave_header_footer()

   Returns ``(header, footer)`` tuple of strings
   where ``header`` is everything before the PCM data
   and ``footer`` is everything after the PCM data.

   May raise :exc:`ValueError` if there's a problem
   with the header or footer data, such as invalid chunk IDs.
   May raise :exc:`IOError` if there's a problem
   reading the header or footer data from the file.

.. classmethod:: WaveContainer.from_wave(filename, header, pcmreader, footer[, compression])

   Encodes a new file from wave data.
   ``header`` and ``footer`` are binary strings as returned by a
   :meth:`WaveContainer.wave_header_footer` method,
   ``pcmreader`` is a :class:`PCMReader` object
   and ``compression`` is a binary string.

   Returns a new :class:`AudioFile`-compatible object
   or raises :exc:`EncodingError` if some error occurs when
   encoding the file.

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

.. method:: AiffContainer.has_foreign_aiff_chunks()

   Returns ``True`` if our object has non-audio AIFF chunks.

.. method:: AiffContainer.aiff_header_footer()

   Returns ``(header, footer)`` tuple of strings
   where ``header`` is everything before the PCM data
   and ``footer`` is everything after the PCM data.

   May raise :exc:`ValueError` if there's a problem
   with the header or footer data, such as invalid chunk IDs.
   May raise :exc:`IOError` if there's a problem
   reading the header or footer data from the file.

.. classmethod:: AiffContainer.from_aiff(filename, header, pcmreader, footer[, compression])

   Encodes a new file from wave data.
   ``header`` and ``footer`` are binary strings as returned by a
   :meth:`AiffContainer.aiff_header_footer` method,
   ``pcmreader`` is a :class:`PCMReader` object
   and ``compression`` is a binary string.

   Returns a new :class:`AudioFile`-compatible object
   or raises :exc:`EncodingError` if some error occurs when
   encoding the file.

MetaData Objects
----------------

.. class:: MetaData([track_name][, track_number][, track_total][, album_name][, artist_name][, performer_name][, composer_name][, conductor_name][, media][, ISRC][, catalog][, copyright][, publisher][, year][, data][, album_number][, album_total][, comment][, images])

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

   MetaData attributes may be ``None``,
   which indicates the low-level implementation has
   no corresponding entry.
   For instance, ID3v2.3 tags use the ``"TALB"`` frame
   to indicate the track's album name.
   If that frame is present, an :class:`audiotools.ID3v23Comment`
   MetaData object will have an ``album_name`` field containing
   a Unicode string of its value.
   If that frame is not present in the ID3v2.3 tag,
   its ``album_name`` field will be ``None``.

   For example, to access a track's album name field:

   >>> metadata = track.get_metadata()
   >>> metadata.album_name
   u"Album Name"

   To change a track's album name field:

   >>> metadata = track.get_metadata()
   >>> metadata.album_name = u"Updated Album Name"
   >>> track.update_metadata(metadata)  # because metadata comes from track's get_metadata() method, one can use update_metadata()

   To delete a track's album name field:

   >>> metadata = track.get_metadata()
   >>> del(metadata.album_name)
   >>> track.update_metadata(metadata)

   Or to replace a track's entire set of metadata:

   >>> metadata = MetaData(track_name=u"Track Name",
   ...                     album_name=u"Updated Album Name",
   ...                     track_number=1,
   ...                     track_total=3)
   >>> track.set_metadata(metadata)  # because metadata is built from scratch, one must use set_metadata()

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

.. method:: MetaData.fields()

   Yields an ``(attr, value)`` tuple per :class:`MetaData` field.

.. method:: MetaData.filled_fields()

   Yields an ``(attr, value)`` tuple per non-blank :class:`MetaData` field.
   Non-blank fields are those with a value other than ``None``.

.. method:: MetaData.empty_fields()

   Yields an ``(attr, value)`` tuple per blank :class:`MetaData` field.
   Blank fields are those with a value of ``None``.

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

.. method:: MetaData.clean()

   Returns a (:class:`MetaData`, ``fixes_performed``) tuple
   where ``MetaData`` is an object that's been cleaned of problems
   and ``fixes_performed`` is a list of unicode strings detailing
   those problems.
   Problems include:

   * Leading whitespace in text fields
   * Trailing whitespace in text fields
   * Empty fields
   * Leading zeroes in numerical fields
   * Incorrectly labeled image metadata fields

.. method:: MetaData.raw_info()

   Returns a Unicode string of raw metadata information
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

.. method:: PCMReader.read(pcm_frames)

   Try to read a :class:`pcm.FrameList` object with the given
   number of PCM frames, if possible.
   This method is *not* guaranteed to read that amount of frames.
   It may return less, particularly at the end of an audio stream.
   It may even return FrameLists larger than requested.
   However, it must always return a non-empty FrameList until the
   end of the PCM stream is reached.

   Once the end of the stream is reached, subsequent calls
   will return empty FrameLists.

   May raise :exc:`IOError` if there is a problem reading the
   source file, or :exc:`ValueError` if the source file has
   some sort of error.

.. method:: PCMReader.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.

   Subsequent calls to :meth:`PCMReader.read` will
   raise :exc:`ValueError` exceptions once the stream is closed.

PCMReaderError Objects
^^^^^^^^^^^^^^^^^^^^^^

.. class:: PCMReaderError(error_message, sample_rate, channels, channel_mask, bits_per_sample)

   This is a subclass of :class:`PCMReader` which always returns empty
   always raises a :class:`ValueError` when its read method is called.
   The purpose of this is to postpone error generation so that
   all encoding errors, even those caused by unsuccessful decoding,
   are restricted to the :meth:`from_pcm` classmethod
   which can then propagate an :class:`EncodingError` error message
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

RemaskedPCMReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: RemaskedPCMReader(pcmreader, channel_count, channel_mask)

   This class wraps around an existing :class:`PCMReader` object
   and constructs a new :class:`PCMReader` with the given
   channel count and mask.

   Channels common to ``pcmreader`` and the given channel mask
   are output by calls to :meth:`RemaskedPCMReader.read`
   while missing channels are populated with silence.

BufferedPCMReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: BufferedPCMReader(pcmreader)

   This class wraps around an existing :class:`PCMReader` object.
   Its calls to :meth:`read` are guaranteed to return
   :class:`pcm.FrameList` objects as close to the requested amount
   of PCM frames as possible without going over by buffering data
   internally.

   The reason such behavior is not required is that we often
   don't care about the size of the individual FrameLists being
   passed from one routine to another.
   But on occasions when we need :class:`pcm.FrameList` objects
   to be of a particular size, this class can accomplish that.

CounterPCMReader Objects
^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: CounterPCMReader(pcmreader)

   This class wraps around an existing :class:`PCMReader` object
   and keeps track of the number of bytes and frames written
   upon each call to ``read``.

.. attribute:: CounterPCMReader.frames_written

   The number of PCM frames written thus far.

.. method:: CounterPCMReader.bytes_written()

   The number of bytes written thus far.

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

   This class wraps around a list of :class:`PCMReader` objects
   and concatenates their output into a single output stream.

   If any of the readers has different attributes
   from the first reader in the stream, :exc:`ValueError` is raised
   at init-time.

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

   :class:`PCMReaderWindow` is designed primarily for handling
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

.. method:: CDDA.freedb_disc_id()

   A :class:`freedb.DiscID` object from this CD's table-of-contents.

.. method:: CDDA.musicbrainz_disc_id()

   A :class:`musicbrainz.DiscID` object from this CD's table-of-contents.

.. method:: CDDA.metadata_lookup([musicbrainz_server], [musicbrainz_port], [freedb_server], [freedb_port], [use_musicbrainz], [use_freedb])

   Calls :func:`metadata_lookup` using this CD's table-of-contents.

.. method:: CDDA.accuraterip_disc_id()

   A :class:`accuraterip.DiscID` object from this CD's table-of-contents.

.. method:: CDDA.accuraterip_lookup([server][, port])

   Calls :func:`accuraterip_lookup` using this CD's table-of-contents.

CD Lookups
^^^^^^^^^^

.. function:: metadata_lookup(first_track_number, last_track_number, offsets, lead_out_offset, total_length, [musicbrainz_server], [musicbrainz_port], [freedb_server], [freedb_port], [use_musicbrainz], [use_freedb])

   Generates a set of :class:`MetaData` objects from CD information.
   ``first_track_number`` and ``last_track_number`` are positive ints.
   ``offsets`` is a list of track offsets, in CD frames.
   ``lead_out_offset`` is the offset of the "lead-out" track, in CD frames.
   ``total_length`` is the total length of the disc, in CD frames.

   Returns a ``metadata[c][t]`` list of lists
   where ``c`` is a possible choice and ``t`` is the :class:`MetaData`
   for a given track (starting from 0).

   This will always return a list of :class:`MetaData` objects
   for at least one choice.
   In the event that no matches for the CD can be found,
   those objects will only contain ``track_number`` and ``track_total``
   fields.

.. function:: accuraterip_lookup(sorted_tracks[, server][, port])

   Given a list of :class:`AudioFile` objects sorted by
   track number, returns a
   ``{track_number:[(confidence, checksum, alt), ...], ...}``
   dict of values retrieved from the AccurateRip database
   where ``track_number`` is an int starting from 1,
   ``confidence`` is the number of people with the same people
   with a matching ``checksum`` of the track.

   May return a dict of empty lists if no AccurateRip entry is found.

   May return :exc:`urllib2.HTTPError` if an error occurs
   querying the server.

.. function:: accuraterip_sheet_lookup(sheet, total_pcm_frames, sample_rate[, server][, port])

   Given a :class:`Sheet` object, total number of PCM frames and sample rate,
   returns a
   ``{track_number:[(confidence, checksum, alt), ...], ...}``
   dict of values retrieved from the AccurateRip database
   where ``track_number`` is an int starting from 1,
   ``confidence`` is the number of people with the same people
   with a matching ``checksum`` of the track.

   May return a dict of empty lists if no AccurateRip entry is found.

   May return :exc:`urllib2.HTTPError` if an error occurs
   querying the server.

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

Cuesheets
---------

Sheet Objects
^^^^^^^^^^^^^

These objects represent a CDDA layout such as provided
by a ``.cue`` or ``.toc`` file.
This can be used to recreate the exact layout of the disc
when burning a set of tracks back to CD.

.. class:: Sheet(sheet_tracks[, catalog_number])

   ``sheet_tracks`` is a list of :class:`SheetTrack` objects,
   one per track on the CD.
   ``catalog_number`` is an optional catalog number string.

.. method:: Sheet.catalog()

   Returns the sheet's catalog number as a plain string,
   or ``None`` if it has no catalog number.

.. method:: Sheet.tracks()

   Returns an iterator of all the :class:`SheetTrack` objects
   in the sheet.

.. method:: Sheet.track(track_number)

   Given a ``track_number`` integer (typically starting from 1)
   returns the :class:`SheetTrack` object of that track
   or raises :exc:`KeyError` if the track number is not found
   in the cuesheet.

.. method:: Sheet.image_formatted()

   Returns ``True`` if the sheet is properly formatted for CD images.

.. method:: Sheet.pcm_lengths(total_pcm_frames, sample_rate)

   Given a stream's total number of PCM frames and sample rate,
   iterates over a set of track length integers, in PCM frames,
   for each track in the sheet.

   The lengths are measured from the current track's maximum index offset
   to the next track's maximum index offset,
   except for the final track which is measured from its maximum index offset
   to the end of the stream.

SheetTrack Objects
^^^^^^^^^^^^^^^^^^

These objects represent a track on a given cuesheet.

.. class:: SheetTrack(number, indexes[, audio][, ISRC])

   ``number`` is the track's number on the CD, typically starting from 1.
   ``indexes`` is a list of :class:`SheetIndex` objects
   for each index in the track.
   ``audio`` is ``True`` if the track contains audio data,
   ``False`` if it contains binary data.
   If omitted, it's assumed to be ``True``.
   ``ISRC``, if given, is a plain string of the track's ISRC information.

.. method:: SheetTrack.indexes()

   Returns an iterator of all the :class:`SheetIndex` objects
   in the track.

.. method:: SheetTrack.index(index_number)

   Given a ``index_number`` integer (often starting from 1)
   returns the :class:`SheetIndex` object of that index
   or raises :exc:`KeyError` if the index is not found
   in the track.

.. method:: SheetTrack.number()

   Returns the number of the track as an integer.

.. method:: SheetTrack.ISRC()

   Returns the ISRC of the track as a plain string, or ``None``.

.. method:: SheetTrack.audio()

   Returns ``True`` if the track contains audio data.

SheetIndex Objects
^^^^^^^^^^^^^^^^^^

.. class:: SheetIndex(number, offset)

   ``number`` is the number of the index in the track,
   often starting from 1.
   A number of 0 indicates a pre-gap index.
   ``offset`` is the index's offset from the start of the
   stream as a :class:`Fraction` number of seconds
   (from the standard library's ``fractions`` module).

.. method:: SheetIndex.number()

   Returns the track's index as an integer.

.. method:: SheetIndex.offset()

   Returns the track's offset from the start of the stream
   as a :class:`Fraction` number of seconds.

DVDAudio Objects
----------------

.. class:: DVDAudio(audio_ts_path[, device])

   This class is used to access a DVD-Audio.
   It contains a collection of titlesets.
   Each titleset contains a list of
   :class:`audiotools.dvda.DVDATitle` objects,
   and each :class:`audiotools.dvda.DVDATitle` contains a list of
   :class:`audiotools.dvda.DVDATrack` objects.
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
   The optional ``total_progress_message`` argument is a Unicode string
   which displays an additional progress bar of the queue's total progress.

.. method:: ExecProgressQueue.execute(function[, progress_text[, completion_output[, *args[, **kwargs]]]])

   Queues a Python function for execution.
   This function is passed the optional ``args`` and ``kwargs``
   arguments upon execution.
   However, this function is also passed an *additional* ``progress``
   keyword argument which is a function that takes ``current`` and
   ``total`` integer arguments.
   The executed function can then call that ``progress`` function
   at regular intervals to indicate its progress.

   If given, ``progress_text`` is a Unicode string to be displayed
   while the function is being executed.

   ``completion_output`` is displayed once the executed function is
   completed.
   It can be either a Unicode string or a function whose argument
   is the returned result of the executed function and which must
   output either a Unicode string or ``None``.
   If ``None``, no output text is generated for the completed job.

.. method:: ExecProgressQueue.run([max_processes])

   Executes all the queued functions, running ``max_processes`` number
   of functions at a time until the entire queue is empty.
   Returns the results of the called functions in the order
   in which they were added for execution.
   This operates by forking a new subprocess per function
   in which the running progress and function output are
   piped to the parent for display to the screen.

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

.. method:: Messenger.output_isatty()

   Returns ``True`` if the output method sends to a TTY rather than a file.

.. method:: Messenger.info_isatty()

   Returns ``True`` if the info method sends to a TTY rather than a file.

.. method:: Messenger.error_isatty()

   Returns ``True`` if the error method sends to a TTY rather than a file.

.. method:: Messenger.usage(string)

   Outputs usage text, Unicode ``string`` and a newline to stderr.

   >>> m.usage(u"<arg1> <arg2> <arg3>")
   *** Usage: audiotools <arg1> <arg2> <arg3>

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
   This is typically used in conjunction with :meth:`Messenger.ansi_uplines`.

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

.. method:: ProgressDisplay.add_row(output_line)

   ``output_line`` is a Unicode string indicating what
   we're displaying the progress of.
   Returns a :class:`ProgressRow` object which can be updated
   with the current progress for display.

.. method:: ProgressDisplay.remove_row(row_index)

   Removes the given row index and frees the slot for reuse.

.. method:: ProgressDisplay.display_rows()

   Outputs the current state of all progress rows.

.. method:: ProgressDisplay.clear_row()

   Clears all previously displayed output rows, if any.

.. class:: ProgressRow(progress_display, row_index, output_line)

   This is used by :class:`ProgressDisplay` and its subclasses
   for actual output generation.
   ``progress_display`` is a parent :class:`ProgressDisplay` object.
   ``row_index`` is this row's index on the screen.
   ``output_line`` is a unicode string.
   It is not typically instantiated directly.

.. method:: ProgressRow.update(current, total)

   Updates the current progress with ``current`` and ``total`` integer values.

.. method:: ProgressRow.finish()

   Indicate output is finished and the row will no longer be needed.

.. method:: ProgressRow.unicode(width)

   Returns the output line and its current progress as a Unicode string,
   formatted to the given width in onscreen characters.
   Screen width can be determined from the :meth:`Messenger.terminal_size`
   method.

.. class:: SingleProgressDisplay(messenger, progress_text)

   This is a subclass of :class:`ProgressDisplay` used
   for generating only a single line of progress output.
   As such, one only specifies a single row of Unicode ``progress_text``
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

output_text Objects
^^^^^^^^^^^^^^^^^^^

This class is for displaying portions of a Unicode string to
the screen and applying formatting such as color via ANSI escape
sequences.

The reason this is needed is because not all Unicode characters
are the same width when displayed to the screen.
So, for example, if one wishes to display a portion of a Unicode string to
a screen that's 80 ASCII characters wide, one can't simply perform:

>>> messenger.output(unicode_string[0:80])

since some of those Unicode characters might be double width,
which would cause the string to wrap.

.. class:: output_text(unicode_string[, fg_color][, bg_color][, style])

   ``unicode_string`` is the text to display.
   ``fg_color`` and ``bg_color`` may be one of
   ``"black"``, ``"red"``, ``"green"``, ``"yellow"``,
   ``"blue"``, ``"magenta"``, ``"cyan"``, or ``"white"``.
   ``style`` may be one of
   ``"bold"``, ``"underline"``, ``"blink"`` or ``"inverse"``.

.. method:: output_text.set_format([fg_color][, bg_color][, style])

   Applies the given format strings, replacing any existing format.

.. method:: output_text.format([is_tty])

   If formatting is present and ``is_tty`` is ``True``,
   returns a Unicode string with ANSI escape sequences applied.
   Otherwise, returns the Unicode string with no ANSI formatting.

.. method:: output_text.head(display_characters)

   Returns a new :class:`output_text` object that's been
   truncated up to the given number of display characters,
   but may return less.

   >>> s = u"".join(map(unichr, range(0x30a1, 0x30a1+25)))
   >>> len(s)
   25
   >>> u = unicode(output_text(s).head(40))
   >>> len(u)
   20
   >>> print repr(u)
   u'\u30a1\u30a2\u30a3\u30a4\u30a5\u30a6\u30a7\u30a8\u30a9\u30aa\u30ab\u30ac\u30ad\u30ae\u30af\u30b0\u30b1\u30b2\u30b3\u30b4'

.. note::

   Because some characters are double-width, this method
   along with :meth:`output_text.tail` and :meth:`output_text.split`
   may not return strings that are the same length as requested
   if the dividing point in the middle of a character.

.. method:: output_text.tail(display_characters)

   Returns a new :class:`output_text` object that's been
   truncated up to the given number of display characters.

   >>> s = u"".join(map(unichr, range(0x30a1, 0x30a1+25)))
   >>> len(s)
   25
   >>> u = unicode(output_text(s).tail(40))
   >>> len(u)
   20
   >>> print repr(u)
   u'\u30a6\u30a7\u30a8\u30a9\u30aa\u30ab\u30ac\u30ad\u30ae\u30af\u30b0\u30b1\u30b2\u30b3\u30b4\u30b5\u30b6\u30b7\u30b8\u30b9'

.. method:: output_text.split(display_characters)

   Returns a tuple of :class:`output_text` objects.
   The first is up to ``display_characters`` wide,
   while the second contains the remainder.

   >>> s = u"".join(map(unichr, range(0x30a1, 0x30a1+25)))
   >>> (head, tail) = display_unicode(s).split(40)
   >>> print repr(unicode(head))
   u'\u30a1\u30a2\u30a3\u30a4\u30a5\u30a6\u30a7\u30a8\u30a9\u30aa\u30ab\u30ac\u30ad\u30ae\u30af\u30b0\u30b1\u30b2\u30b3\u30b4'
   >>> print repr(unicode(tail))
   u'\u30b5\u30b6\u30b7\u30b8\u30b9'

.. method:: output_text.join(output_texts)

   Given an iterable collection of :class:`output_text` objects,
   returns an :class:`output_list` joined by our formatted text.

output_list Objects
^^^^^^^^^^^^^^^^^^^

output_list is an :class:`output_text` subclass
for formatting multiple :class:`output_text` objects as a unit.

.. class:: output_list(output_texts[, fg_color][, bg_color][, style])

   ``output_texts`` is an iterable collection of
   :class:`output_text` or unicode objects.
   ``fg_color`` and ``bg_color`` may be one of
   ``"black"``, ``"red"``, ``"green"``, ``"yellow"``,
   ``"blue"``, ``"magenta"``, ``"cyan"``, or ``"white"``.
   ``style`` may be one of
   ``"bold"``, ``"underline"``, ``"blink"`` or ``"inverse"``.

.. warning::

   Formatting is unlikely to nest properly since
   ANSI is un-escaped to the terminal default.
   Therefore, if the :class:`output_list` has formatting,
   its contained :class:`output_text` objects should not have formatting.
   Or if the :class:`output_text` objects do have formatting,
   the :class:`output_list` container should not have formatting.

.. method:: output_list.set_format([fg_color][, bg_color][, style])

   Applies the given format strings, replacing any existing format.

.. method:: output_list.format([is_tty])

   If formatting is present and ``is_tty`` is ``True``,
   returns a Unicode string with ANSI escape sequences applied.
   Otherwise, returns the Unicode string with no ANSI formatting.

.. method:: output_list.head(display_characters)

   Returns a new :class:`output_list` object that's been
   truncated up to the given number of display characters,
   but may return less.

.. method:: output_list.tail(display_characters)

   Returns a new :class:`output_list` object that's been
   truncated up to the given number of display characters.

.. method:: output_list.split(display_characters)

   Returns a tuple of :class:`output_text` objects.
   The first is up to ``display_characters`` wide,
   while the second contains the remainder.

.. method:: output_list.join(output_texts)

   Given an iterable collection of :class:`output_text` objects,
   returns an :class:`output_list` joined by our formatted text.

output_table Objects
^^^^^^^^^^^^^^^^^^^^

output_table is for formatting text into rows and columns.

.. class:: output_table()

.. method:: output_table.row()

   Adds new row to table and returns :class:`output_table_row` object
   which columns may be added to.

.. method:: output_table.blank_row()

   Adds empty row to table whose columns will be blank.

.. method:: output_table.divider_row(dividers)

   Takes a list of Unicode characters, one per column,
   and generates a row which will expand those characters
   as needed to fill each column.

.. method:: output_table.format([is_tty])

   Yields one formatted Unicode string per row.
   If ``is_tty`` is ``True``, rows may contain ANSI escape sequences
   for color and style.

output_table_row Objects
^^^^^^^^^^^^^^^^^^^^^^^^

output_table_row is a container for table columns
and is returned from :meth:`output_table.row()`
rather than instantiated directly.

.. class:: output_table_row()

.. method:: output_table_row.__len__()

   Returns the total number of columns in the table.

.. method:: output_table_row.add_column(text[, alignment="left"])

   Adds text, which may be a Unicode string or
   :class:`output_text` object.
   ``alignment`` may be ``"left"``, ``"center"`` or ``"right"``.

.. method:: output_table_row.column_width(column)

   Returns the width of the given column in printable characters.

.. method:: output_table_row.format(column_widths[, is_tty])

   Given a list of column widths, returns the table row
   as a Unicode string such that each column is padded to the
   corresponding width depending on its alignment.
   If ``is_tty`` is ``True``, columns may contain ANSI escape
   sequences for color and style.

Exceptions
----------

.. exception:: UnknownAudioType

   Raised by :func:`filename_to_type` if the file's suffix is unknown.

.. exception:: AmbiguousAudioType

   Raised by :func:`filename_to_type` if the file's suffix
   applies to more than one audio class.

.. exception:: DecodingError

   Raised by :class:`PCMReader`'s .close() method if
   a helper subprocess exits with an error,
   typically indicating a problem decoding the file.

.. exception:: DuplicateFile

   Raised by :func:`open_files` if the same file
   is included more than once and ``no_duplicates`` is indicated.

.. exception:: DuplicateOutputFile

   Raised by :func:`audiotools.ui.process_output_options`
   if the same output file is generated more than once.

.. exception:: EncodingError

   Raised by :meth:`AudioFile.from_pcm` and :meth:`AudioFile.convert`
   if an error occurs when encoding an input file.
   This includes errors from the input stream,
   a problem writing the output file in the given location,
   or EncodingError subclasses such as
   :exc:`UnsupportedBitsPerSample` if the input stream
   is formatted in a way the output class does not support.

.. exception:: InvalidFile

   Raised by :meth:`AudioFile.__init__` if the file
   is invalid in some way.

.. exception:: InvalidFilenameFormat

   Raised by :meth:`AudioFile.track_name` if the format string
   contains broken fields.

.. exception:: InvalidImage

   Raised by :meth:`Image.new` if the image cannot be parsed correctly.

.. exception:: OutputFileIsInput

   Raised by :func:`process_output_options` if an output file
   is the same as any of the input files.

.. exception:: SheetException

   A parent exception of :exc:`audiotools.cue.CueException`
   and :exc:`audiotools.toc.TOCException`,
   to be raised by :func:`read_sheet` if a .toc or .cue file
   is unable to be parsed correctly.

.. exception:: UnsupportedBitsPerSample

   Subclass of :exc:`EncodingError`, indicating
   the input stream's bits-per-sample is not supported
   by the output class.

.. exception:: UnsupportedChannelCount

   Subclass of :exc:`EncodingError`, indicating
   the input stream's channel count is not supported
   by the output class.

.. exception:: UnsupportedChannelMask

   Subclass of :exc:`EncodingError`, indicating
   the input stream's channel mask is not supported
   by the output class.

.. exception:: UnsupportedFile

   Raised by :func:`open` if the given file is not something
   identifiable, or we do not have the installed binaries to support.

.. exception:: UnsupportedTracknameField

   Raised by :meth:`AudioFile.track_name` if a track name
   field is not supported.
