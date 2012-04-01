Meta Data Formats
=================

Although it's more convenient to manipulate the high-level
:class:`audiotools.MetaData` base class, one sometimes needs to be
able to view and modify the low-level implementation also.

ApeTag
------

.. class:: ApeTag(tags[, contains_header][, contains_footer])

   This is an APEv2_ tag used by the WavPack, Monkey's Audio
   and Musepack formats, among others.
   During initialization, it takes a list of :class:`ApeTagItem` objects
   and optional ``contains_header``, ``contains_footer`` booleans.
   It can then be manipulated like a regular Python dict
   with keys as strings and values as :class:`ApeTagItem` objects.
   Note that this is also a :class:`audiotools.MetaData` subclass
   with all of the same methods.

   For example:

   >>> tag = ApeTag([ApeTagItem(0, False, 'Title', u'Track Title'.encode('utf-8'))])
   >>> tag.track_name
   u'Track Title'
   >>> tag['Title']
   ApeTagItem(0,False,'Title','Track Title')
   >>> tag['Title'] = ApeTagItem(0, False, 'Title', u'New Title'.encode('utf-8'))
   >>> tag.track_name
   u'New Title'
   >>> tag.track_name = u'Yet Another Title'
   >>> tag['Title']
   ApeTagItem(0, False, 'Title', 'Yet Another Title')

   The fields are mapped between :class:`ApeTag` and
   :class:`audiotools.MetaData` as follows:

   =============== ================================
   APEv2           Metadata
   --------------- --------------------------------
   ``Title``       ``track_name``
   ``Track``       ``track_number``/``track_total``
   ``Media``       ``album_number``/``album_total``
   ``Album``       ``album_name``
   ``Artist``      ``artist_name``
   ``Performer``   ``performer_name``
   ``Composer``    ``composer_name``
   ``Conductor``   ``conductor_name``
   ``ISRC``        ``ISRC``
   ``Catalog``     ``catalog``
   ``Copyright``   ``copyright``
   ``Publisher``   ``publisher``
   ``Year``        ``year``
   ``Record Date`` ``date``
   ``Comment``     ``comment``
   =============== ================================

   Note that ``Track`` and ``Media`` may be "/"-separated integer values
   where the first is the current number and the second is the total number.

   >>> tag = ApeTag([ApeTagItem(0, False, 'Track', u'1'.encode('utf-8'))])
   >>> tag.track_number
   1
   >>> tag.track_total
   0
   >>> tag = ApeTag([ApeTagItem(0, False, 'Track', u'2/3'.encode('utf-8'))])
   >>> tag.track_number
   2
   >>> tag.track_total
   3

.. classmethod:: ApeTag.read(file)

   Takes an open file object and returns an :class:`ApeTag` object
   of that file's APEv2 data, or ``None`` if the tag cannot be found.

.. method:: ApeTag.build(writer)

   Given a :class:`audiotools.bitstream.BitstreamWriter`
   object positioned at the end of the file,
   this writes the ApeTag to that stream.

.. method:: ApeTag.total_size()

   Returns the minimum size of the entire APEv2 tag, in bytes.

.. class:: ApeTagItem(item_type, read_only, key, data)

   This is the container for :class:`ApeTag` data.
   ``item_type`` is an integer with one of the following values:

   = =============
   1 UTF-8 data
   2 binary data
   3 external data
   4 reserved
   = =============

   ``read_only`` is a boolean set to ``True`` if the tag-item is read-only.
   ``key`` is an ASCII string.
   ``data`` is a regular Python string (not unicode).

.. method:: ApeTagItem.build()

   Returns this tag item's data as a string.

.. classmethod:: ApeTagItem.binary(key, data)

   A convenience classmethod which takes strings of key and value data
   and returns a populated :class:`ApeTagItem` object of the
   appropriate type.

.. classmethod:: ApeTagItem.external(key, data)

   A convenience classmethod which takes strings of key and value data
   and returns a populated :class:`ApeTagItem` object of the
   appropriate type.

.. classmethod:: ApeTagItem.string(key, unicode)

   A convenience classmethod which takes a key string and value unicode
   and returns a populated :class:`ApeTagItem` object of the
   appropriate type.

FLAC
----

.. class:: FlacMetaData(blocks)

   This is a FLAC_ tag which is prepended to FLAC and Ogg FLAC files.
   It is initialized with a list of FLAC metadata block
   objects which it stores internally as a list.
   It also supports all :class:`audiotools.MetaData` methods.

   For example:

   >>> tag = FlacMetaData([Flac_VORBISCOMMENT(
   ...                     [u'TITLE=Track Title'], u'Vendor String')])
   >>> tag.track_name
   u'Track Title'
   >>> tag.get_block(Flac_VORBISCOMMENT.BLOCK_ID)
   Flac_VORBISCOMMENT([u'TITLE=Track Title'], u'Vendor String')
   >>> tag.replace_blocks(Flac_VORBISCOMMENT.BLOCK_ID,
   ...                    [Flac_VORBISCOMMENT([u'TITLE=New Track Title'], u'Vendor String')])
   >>> tag.track_name
   u'New Track Title'

.. method:: FlacMetaData.has_block(block_id)

   Returns ``True`` if the given block ID integer is present
   in this metadata's list of blocks.

.. method:: FlacMetaData.add_block(block)

   Adds the given block to this metadata's list of blocks.
   Blocks are added such that STREAMINFO will always be first.

.. method:: FlacMetaData.get_block(block_id)

   Returns the first instance of the given block ID.
   May raise :exc:`IndexError` if the block ID is not present.

.. method:: FlacMetaData.get_blocks(block_id)

   Returns all instances of the given block ID as a list,
   which may be empty if no matching blocks are present.

.. method:: FlacMetaData.replace_blocks(block_id, blocks)

   Replaces all instances of the given block ID
   with those taken from the list of blocks.
   If insufficient blocks are found to replace,
   this uses :meth:`FlacMetaData.add_block` to populate the remainder.
   If additional blocks are found, they are removed.

.. method:: FlacMetaData.blocks()

   Yields a set of all blocks this metadata contains.

.. classmethod:: FlacMetaData.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`
   positioned past the FLAC file's ``"fLaC"`` file header,
   returns a parsed :class:`FlacMetaData` object.
   May raise :exc:`IOError` or :exc:`ValueError` if
   some error occurs parsing the metadata.

.. method:: FlacMetaData.raw_info()

   Returns this metadata as a human-readable unicode string.

.. method:: FlacMetaData.size()

   Returns the size of all metadata blocks
   including the 32-bit block headers
   but not including the file's 4-byte ``"fLaC"`` ID.

STREAMINFO
^^^^^^^^^^

.. class:: Flac_STREAMINFO(minimum_block_size, maximum_block_size, minimum_frame_size, maximum_frame_size, sample_rate, channels, bits_per_sample, total_samples, md5sum)

   All values are non-negative integers except for ``md5sum``,
   which is a 16-byte binary string.
   All are stored in this metadata block as-is.

.. data:: Flac_STREAMINFO.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_STREAMINFO.copy()

   Returns a copy of this metadata block.

.. method:: Flac_STREAMINFO.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_STREAMINFO.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`, returns a parsed :class:`Flac_STREAMINFO` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_STREAMINFO.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_STREAMINFO.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

PADDING
^^^^^^^

.. class:: Flac_PADDING(length)

   Length is the length of the padding, in bytes.

.. data:: Flac_PADDING.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_PADDING.copy()

   Returns a copy of this metadata block.

.. method:: Flac_PADDING.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_PADDING.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`, returns a parsed :class:`Flac_PADDING` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_PADDING.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_PADDING.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

APPLICATION
^^^^^^^^^^^

.. class:: Flac_APPLICATION(application_id, data)

   ``application_id`` is a 4-byte binary string.
   ``data`` is a binary string.

.. data:: Flac_APPLICATION.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_APPLICATION.copy()

   Returns a copy of this metadata block.

.. method:: Flac_APPLICATION.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_APPLICATION.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`, returns a parsed :class:`Flac_APPLICATION` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_APPLICATION.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_APPLICATION.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

SEEKTABLE
^^^^^^^^^

.. class:: Flac_SEEKTABLE(seekpoints)

   ``seekpoints`` is a list of
   ``(PCM frame offset, byte offset, PCM frame count)`` tuples
   for each seek point in the seektable.

.. data:: Flac_SEEKTABLE.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_SEEKTABLE.copy()

   Returns a copy of this metadata block.

.. method:: Flac_SEEKTABLE.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_SEEKTABLE.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`, returns a parsed :class:`Flac_SEEKTABLE` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_SEEKTABLE.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_SEEKTABLE.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

.. method:: Flac_SEEKTABLE.clean(fixes_performed)

   Returns a fixed FLAC seektable with empty seek points removed
   and ``byte offset`` / ``PCM frame count`` values reordered
   to be incrementing.
   Any fixes performed are appended to the ``fixes_performed``
   list as unicode strings.

VORBISCOMMENT
^^^^^^^^^^^^^

.. class:: Flac_VORBISCOMMENT(comment_strings, vendor_string)

   ``comment_strings`` is a list of unicode strings
   and ``vendor_string`` is a unicode string.

   >>> Flac_VORBISCOMMENT([u"TITLE=Foo", u"ARTIST=Bar"], u"Python Audio Tools")

.. data:: Flac_VORBISCOMMENT.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_VORBISCOMMENT.copy()

   Returns a copy of this metadata block.

.. method:: Flac_VORBISCOMMENT.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_VORBISCOMMENT.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`, returns a parsed :class:`Flac_VORBISCOMMENT` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_VORBISCOMMENT.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_VORBISCOMMENT.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

.. classmethod:: Flac_VORBISCOMMENT.converted(metadata)

   Given a :class:`audiotools.MetaData`-compatible object,
   returns a :class:`Flac_VORBISCOMMENT` object.

CUESHEET
^^^^^^^^

.. class:: Flac_CUESHEET(catalog_number, lead_in_samples, is_cdda, tracks)

   ``catalog_number`` is a 128 byte binary string.
   ``lead_in_samples`` is a non-negative integer.
   ``is_cdda`` is 1 if the cuesheet is from an audio CD, 0 if not.
   ``tracks`` is a list of :class:`Flac_CUESHEET_track` objects.

.. data:: Flac_CUESHEET.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_CUESHEET.copy()

   Returns a copy of this metadata block.

.. method:: Flac_CUESHEET.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_CUESHEET.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`, returns a parsed :class:`Flac_CUESHEET` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_CUESHEET.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_CUESHEET.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

.. classmethod:: Flac_CUESHEET.converted(cuesheet, total_frames[, sample rate])

   Given a cuesheet-compatible object,
   total length of the file in PCM frames and an optional sample rate,
   returns a new :class:`Flac_CUESHEET` object.

.. method:: Flac_CUESHEET.catalog()

   Returns the cuesheet's catalog number as a 128 byte binary string.

.. method:: Flac_CUESHEET.ISRCs()

   Returns a dict of track number integers -> ISRC binary strings.
   Any tracks without ISRC values will not be present in the dict.

.. method:: Flac_CUESHEET.indexes([sample_rate])

   Returns a list of ``(start, end)`` integer tuples
   indicating all the index points in the cuesheet.

.. method:: Flac_CUESHEET.pcm_lengths(total_length)

   Given a total length of the file in PCM frames,
   returns a list of PCM frame lengths for each track in the cuesheet.

.. class:: Flac_CUESHEET_track(offset, number, ISRC, track_type, pre_emphasis, index_points)

   ``offset`` is the track's offset.
   ``number`` number is the track's number on the CD, typically starting from 1.
   ``ISRC`` is the track's ISRC number as a binary string.
   ``track_type`` is 0 for audio, 1 for non-audio.
   ``pre_emphasis`` is 0 for tracks with no pre-emphasis, 1 for tracks with pre-emphasis.
   ``index_points`` is a list of :class:`Flac_CUESHEET_index` objects.

.. method:: Flac_CUESHEET_track.copy()

   Returns a copy of this cuesheet track.

.. method:: Flac_CUESHEET_track.raw_info()

   Returns this cuesheet track as a human-readable unicode string.

.. classmethod:: Flac_CUESHEET_track.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`,
   returns a parsed :class:`Flac_CUESHEET_track` object.

.. method:: Flac_CUESHEET_track.build(writer)

   Writes this cuesheet track to the given :class:`audiotools.bitstream.BitstreamWriter`.

.. class:: Flac_CUESHEET_index(offset, number)

   ``offset`` is the index point's offset.
   ``number`` is the index point's number in the set.

.. method:: Flac_CUESHEET_index.copy()

   Returns a copy of this cuesheet index.

.. classmethod:: Flac_CUESHEET_index.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`,
   returns a parsed :class:`Flac_CUESHEET_index` object.

.. method:: Flac_CUESHEET_index.build(writer)

   Writes this index point to the given :class:`audiotools.bitstream.BitstreamWriter`.

PICTURE
^^^^^^^

.. class:: Flac_PICTURE(picture_type, mime_type, description, width, height, color_depth, color_count, data)

   ``picture_type`` is one of the following:

   == ===================================
   0  Other
   1  32x32 pixels 'file icon' (PNG only)
   2  Other file icon
   3  Cover (front)
   4  Cover (back)
   5  Leaflet page
   6  Media (e.g. label side of CD)
   7  Lead artist/lead performer/soloist
   8  Artist/performer
   9  Conductor
   10 Band/Orchestra
   11 Composer
   12 Lyricist/text writer
   13 Recording Location
   14 During recording
   15 During performance
   16 Movie/video screen capture
   17 A bright colored fish
   18 Illustration
   19 Band/artist logotype
   20 Publisher/Studio logotype
   == ===================================

   ``mime_type`` and ``description`` are unicode strings.
   ``width`` and ``height`` are integer number of pixels.
   ``color_depth`` is an integer number of bits per pixel.
   ``color_count`` is an integer number of colors for images
   with indexed colors, or 0 for formats such as JPEG with no indexed colors.
   ``data`` is a binary string of raw image data.

   This is a subclass of :class:`audiotools.Image`
   which shares all the same methods and attributes.

.. data:: Flac_IMAGE.BLOCK_ID

   This metadata's block ID as a non-negative integer.

.. method:: Flac_IMAGE.copy()

   Returns a copy of this metadata block.

.. method:: Flac_IMAGE.raw_info()

   Returns this metadata block as a human-readable unicode string.

.. classmethod:: Flac_IMAGE.parse(reader)

   Given a :class:`audiotools.bitstream.BitstreamReader`,
   returns a parsed :class:`Flac_IMAGE` object.
   This presumes its 32-bit metadata header has already been read.

.. method:: Flac_IMAGE.build(writer)

   Writes this metadata block to the given :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 32-bit metadata header.

.. method:: Flac_IMAGE.size()

   Returns the size of the metadata block,
   not including its 32-bit metadata header.

.. method:: Flac_IMAGE.converted(image)

   Given an :class:`Flac_IMAGE`-compatible object,
   returns a new :class:`Flac_IMAGE` block.

.. method:: Flac_IMAGE.clean(fixes_performed)

   Returns a new :class:`Flac_IMAGE` block with
   metadata fields cleaned up according to the metrics
   of the contained raw image data.
   Any fixes are appended to the ``fixes_performed`` list
   as unicode strings.

ID3v1
-----

.. class:: ID3v1Comment(track_name, artist_name, album_name, year, comment, track_number, genre)

   All fields except track_number and genre are binary strings.

   >>> tag = ID3v1Comment(u'Track Title', u'', u'', u'', u'', 1, 0)
   >>> tag.track_name
   u'Track Title'
   >>> tag.track_name = u'New Track Name'
   >>> tag.track_name
   u'New Track Name'

.. method:: ID3v1Comment.raw_info()

   Returns this metadata as a human-readable unicode string.

.. classmethod:: ID3v1Comment.parse(mp3_file)

   Given a seekable file object of an MP3 file,
   returns an :class:`ID3v1Comment` object.
   Raises :exc:`ValueError` if the comment is invalid.

.. method:: ID3v1Comment.build(mp3_file)

   Given a file object positioned at the end of an MP3 file,
   appends this ID3v1 comment to that file.

ID3v2.2
-------

.. class:: ID3v22Comment(frames)

   This is an ID3v2.2_ tag, one of the three ID3v2 variants used by MP3 files.
   During initialization, it takes a list of :class:`ID3v22_Frame`-compatible
   objects.
   It can then be manipulated like a regular Python dict with keys
   as 3 character frame identifiers and values as lists of :class:`ID3v22_Frame`
   objects - since each frame identifier may occur multiple times.

   For example:

   >>> tag = ID3v22Comment([ID3v22_T__Frame('TT2', 0, u'Track Title')])
   >>> tag.track_name
   u'Track Title'
   >>> tag['TT2']
   [<audiotools.__id3__.ID3v22_T__Frame instance at 0x1004c17a0>]
   >>> tag['TT2'] = [ID3v22_T__Frame('TT2', 0, u'New Track Title')]
   >>> tag.track_name
   u'New Track Title'

   Fields are mapped between ID3v2.2 frame identifiers,
   :class:`audiotools.MetaData` and :class:`ID3v22Frame` objects as follows:

   ========== ================================ ========================
   Identifier MetaData                         Object
   ---------- -------------------------------- ------------------------
   ``TT2``    ``track_name``                   :class:`ID3v22_T__Frame`
   ``TRK``    ``track_number``/``track_total`` :class:`ID3v22_T__Frame`
   ``TPA``    ``album_number``/``album_total`` :class:`ID3v22_T__Frame`
   ``TAL``    ``album_name``                   :class:`ID3v22_T__Frame`
   ``TP1``    ``artist_name``                  :class:`ID3v22_T__Frame`
   ``TP2``    ``performer_name``               :class:`ID3v22_T__Frame`
   ``TP3``    ``conductor_name``               :class:`ID3v22_T__Frame`
   ``TCM``    ``composer_name``                :class:`ID3v22_T__Frame`
   ``TMT``    ``media``                        :class:`ID3v22_T__Frame`
   ``TRC``    ``ISRC``                         :class:`ID3v22_T__Frame`
   ``TCR``    ``copyright``                    :class:`ID3v22_T__Frame`
   ``TPB``    ``publisher``                    :class:`ID3v22_T__Frame`
   ``TYE``    ``year``                         :class:`ID3v22_T__Frame`
   ``TRD``    ``date``                         :class:`ID3v22_T__Frame`
   ``COM``    ``comment``                      :class:`ID3v22_COM_Frame`
   ``PIC``    ``images()``                     :class:`ID3v22_PIC_Frame`
   ========== ================================ ========================

ID3v2.2 Frame
^^^^^^^^^^^^^

.. class:: ID3v22_Frame(frame_id, data)

   This is the base class for the various ID3v2.2 frames.
   ``frame_id`` is a 3 character string and ``data`` is
   the frame's contents as a string.

.. method:: ID3v22Frame.copy()

   Returns a new copy of this frame.

.. method:: ID3v22Frame.raw_info()

   Returns this frame as a human-readable unicode string.

.. classmethod:: ID3v22Frame.parse(frame_id, frame_size, reader)

   Given a 3 byte frame ID, frame size and
   :class:`audiotools.bitstream.BitstreamReader`
   (positioned past the 6 byte frame header)
   returns a parsed :class:`ID3v22Frame` object.

.. method:: ID3v22Frame.build(writer)

   Writes frame to the given
   :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 6 byte frame header.

.. method:: ID3v22Frame.size()

   Returns the frame's size, not including its 6 byte frame header.

.. method:: ID3v22Frame.clean(fixes_performed)

   Returns a new :class:`ID3v22Frame` object that's been cleaned
   of any problems.
   Any fixes performed are appended to ``fixes_performed``
   as unicode strings.

ID3v2.2 Text Frames
^^^^^^^^^^^^^^^^^^^

.. class:: ID3v22_T__Frame(frame_id, encoding, data)

   This :class:`ID3v22_Frame`-compatible object is a container
   for textual data.
   ``frame_id`` is a 3 character string, ``data`` is a binary string
   and ``encoding`` is one of the following integers representing a
   text encoding:

   = ========
   0 Latin-1_
   1 UCS-2_
   = ========

.. method:: ID3v22_T__Frame.number()

   Returns the first integer portion of the frame data as an int
   if the frame is container for numerical data such as
   ``TRK`` or ``TPA``.

.. method:: ID3v22_T__Frame.total()

   Returns the second integer portion of the frame data as an int
   if the frame is a numerical container and has a "total" field.
   For example:

   >>> f = ID3v22_T__Frame('TRK', 0, '1/2')
   >>> f.number()
   1
   >>> f.total()
   2

.. classmethod:: ID3v22_T__Frame.converted(frame_id, unicode_string)

   Given a 3 byte frame ID and unicode string,
   returns a new :class:`ID3v22_T__Frame` object.

.. class:: ID3v22_TXX_Frame(encoding, description, data)

   This subclass of :class:`ID3v22_T__Frame` contains
   an additional ``description`` binary string field
   to hold user-defined textual data.

ID3v2.2 Web Frames
^^^^^^^^^^^^^^^^^^

.. class:: ID3v22_W__Frame(frame_id, url)

   This :class:`ID3v22_Frame`-compatible object is a container
   for web links.
   ``frame_id`` is a 3 character string, ``url`` is a binary string.

.. class:: ID3v22_WXX_Frame(encoding, description, url)

   This subclass of :class:`ID3v22_W__Frame` contains
   an additional ``description`` binary string field
   to hold user-defined web link data.

ID3v2.2 COM Frame
^^^^^^^^^^^^^^^^^

.. class:: ID3v22_COM_Frame(encoding, language, short_description, data)

   This :class:`ID3v22_Frame`-compatible object is for holding
   a potentially large block of comment data.
   ``encoding`` is the same as in text frames:

   = ========
   0 Latin-1_
   1 UCS-2_
   = ========

   ``language`` is a 3 character string, such as ``"eng"`` for English.
   ``short_description`` is a :class:`C_string` object.
   ``data`` is a binary string.

.. classmethod:: ID3v22_COM_Frame.converted(frame_id, unicode_string)

   Given a 3 byte ``"COM"`` frame ID and unicode string,
   returns a new :class:`ID3v22_COM_Frame` object.

ID3v2.2 PIC Frame
^^^^^^^^^^^^^^^^^

.. class:: ID3v22_PIC_Frame(image_format, picture_type, description, data)

   This is a subclass of :class:`audiotools.Image`, in addition
   to being a :class:`ID3v22_Frame`-compatible object.
   ``image_format`` is one of the following:

   ========== ======
   ``"PNG"``  PNG
   ``"JPG"``  JPEG
   ``"BMP"``  Bitmap
   ``"GIF"``  GIF
   ``"TIF"``  TIFF
   ========== ======

   ``picture_type`` is an integer representing one of the following:

   == ======================================
   0  Other
   1  32x32 pixels 'file icon' (PNG only)
   2  Other file icon
   3  Cover (front)
   4  Cover (back)
   5  Leaflet page
   6  Media (e.g. label side of CD)
   7  Lead artist / Lead performer / Soloist
   8  Artist / Performer
   9  Conductor
   10 Band / Orchestra
   11 Composer
   12 Lyricist / Text writer
   13 Recording Location
   14 During recording
   15 During performance
   16 Movie / Video screen capture
   17 A bright colored fish
   18 Illustration
   19 Band / Artist logotype
   20 Publisher / Studio logotype
   == ======================================

   ``description`` is a :class:`C_string`.
   ``data`` is a string of binary image data.

.. method:: ID3v22_PIC_Frame.type_string()

   Returns the ``picture_type`` as a plain string.

.. classmethod:: ID3v22_PIC_Frame.converted(frame_id, image)

   Given an :class:`audiotools.Image` object,
   returns a new :class:`ID3v22_PIC_Frame` object.


ID3v2.3
-------

.. class:: ID3v23Comment(frames)

   This is an ID3v2.3_ tag, one of the three ID3v2 variants used by MP3 files.
   During initialization, it takes a list of :class:`ID3v23_Frame`-compatible
   objects.
   It can then be manipulated like a regular Python dict with keys
   as 4 character frame identifiers and values as lists of :class:`ID3v23_Frame`
   objects - since each frame identifier may occur multiple times.

   For example:

   >>> tag = ID3v23Comment([ID3v23_T___Frame('TIT2', 0, u'Track Title')])
   >>> tag.track_name
   u'Track Title'
   >>> tag['TIT2']
   [ID3v23_T___Frame('TIT2', 0, u'Track Title')]
   >>> tag['TIT2'] = [ID3v23_T___Frame('TIT2', 0, u'New Track Title')]
   >>> tag.track_name
   u'New Track Title'

   Fields are mapped between ID3v2.3 frame identifiers,
   :class:`audiotools.MetaData` and :class:`ID3v23_Frame` objects as follows:

   ========== ================================ ==========================
   Identifier MetaData                         Object
   ---------- -------------------------------- --------------------------
   ``TIT2``   ``track_name``                   :class:`ID3v23_T___Frame`
   ``TRCK``   ``track_number``/``track_total`` :class:`ID3v23_T___Frame`
   ``TPOS``   ``album_number``/``album_total`` :class:`ID3v23_T___Frame`
   ``TALB``   ``album_name``                   :class:`ID3v23_T___Frame`
   ``TPE1``   ``artist_name``                  :class:`ID3v23_T___Frame`
   ``TPE2``   ``performer_name``               :class:`ID3v23_T___Frame`
   ``TPE3``   ``conductor_name``               :class:`ID3v23_T___Frame`
   ``TCOM``   ``composer_name``                :class:`ID3v23_T___Frame`
   ``TMED``   ``media``                        :class:`ID3v23_T___Frame`
   ``TSRC``   ``ISRC``                         :class:`ID3v23_T___Frame`
   ``TCOP``   ``copyright``                    :class:`ID3v23_T___Frame`
   ``TPUB``   ``publisher``                    :class:`ID3v23_T___Frame`
   ``TYER``   ``year``                         :class:`ID3v23_T___Frame`
   ``TRDA``   ``date``                         :class:`ID3v23_T___Frame`
   ``COMM``   ``comment``                      :class:`ID3v23_COMM_Frame`
   ``APIC``   ``images()``                     :class:`ID3v23_APIC_Frame`
   ========== ================================ ==========================

ID3v2.3 Frame
^^^^^^^^^^^^^

.. class:: ID3v23_Frame(frame_id, data)

   This is the base class for the various ID3v2.3 frames.
   ``frame_id`` is a 4 character string and ``data`` is
   the frame's contents as a string.

.. method:: ID3v23_Frame.copy()

   Returns a new copy of this frame.

.. method:: ID3v23_Frame.raw_info()

   Returns this frame as a human-readable unicode string.

.. classmethod:: ID3v23_Frame.parse(frame_id, frame_size, reader)

   Given a 4 byte frame ID, frame size and
   :class:`audiotools.bitstream.BitstreamReader`
   (positioned past the 10 byte frame header)
   returns a parsed :class:`ID3v23_Frame` object.

.. method:: ID3v23_Frame.build(writer)

   Writes frame to the given
   :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 10 byte frame header.

.. method:: ID3v23_Frame.size()

   Returns the frame's size, not including its 10 byte frame header.

.. method:: ID3v23_Frame.clean(fixes_performed)

   Returns a new :class:`ID3v23_Frame` object that's been cleaned
   of any problems.
   Any fixes performed are appended to ``fixes_performed``
   as unicode strings.

ID3v2.3 Text Frames
^^^^^^^^^^^^^^^^^^^

.. class:: ID3v23_T___Frame(frame_id, encoding, data)

   This :class:`ID3v23_Frame`-compatible object is a container
   for textual data.
   ``frame_id`` is a 3 character string, ``data`` is a binary string
   and ``encoding`` is one of the following integers representing a
   text encoding:

   = ========
   0 Latin-1_
   1 UCS-2_
   = ========

.. method:: ID3v23_T___Frame.number()

   Returns the first integer portion of the frame data as an int
   if the frame is container for numerical data such as
   ``TRCK`` or ``TPOS``.

.. method:: ID3v23_T___Frame.total()

   Returns the second integer portion of the frame data as an int
   if the frame is a numerical container and has a "total" field.
   For example:

   >>> f = ID3v23_T___Frame('TRCK', 0, '1/2')
   >>> f.number()
   1
   >>> f.total()
   2

.. classmethod:: ID3v23_T___Frame.converted(frame_id, unicode_string)

   Given a 4 byte frame ID and unicode string,
   returns a new :class:`ID3v23_T___Frame` object.

.. class:: ID3v23_TXXX_Frame(encoding, description, data)

   This subclass of :class:`ID3v23_T___Frame` contains
   an additional ``description`` binary string field
   to hold user-defined textual data.

ID3v2.3 Web Frames
^^^^^^^^^^^^^^^^^^

.. class:: ID3v23_W___Frame(frame_id, url)

   This :class:`ID3v23_Frame`-compatible object is a container
   for web links.
   ``frame_id`` is a 4 character string, ``url`` is a binary string.

.. class:: ID3v23_WXXX_Frame(encoding, description, url)

   This subclass of :class:`ID3v23_W___Frame` contains
   an additional ``description`` binary string field
   to hold user-defined web link data.

ID3v2.3 COMM Frame
^^^^^^^^^^^^^^^^^^

.. class:: ID3v23_COMM_Frame(encoding, language, short_description, data)

   This :class:`ID3v23_Frame`-compatible object is for holding
   a potentially large block of comment data.
   ``encoding`` is the same as in text frames:

   = ========
   0 Latin-1_
   1 UCS-2_
   = ========

   ``language`` is a 3 character string, such as ``"eng"`` for English.
   ``short_description`` is a :class:`C_string` object.
   ``data`` is a binary string.

.. classmethod:: ID3v23_COMM_Frame.converted(frame_id, unicode_string)

   Given a 4 byte ``"COMM"`` frame ID and unicode string,
   returns a new :class:`ID3v23_COMM_Frame` object.

ID3v2.3 APIC Frame
^^^^^^^^^^^^^^^^^^

.. class:: ID3v23_APIC_Frame(mime_type, picture_type, description, data)

   This is a subclass of :class:`audiotools.Image`, in addition
   to being a :class:`ID3v23_Frame`-compatible object.
   ``mime_type`` is a :class:`C_string`.
   ``picture_type`` is an integer representing one of the following:

   == ======================================
   0  Other
   1  32x32 pixels 'file icon' (PNG only)
   2  Other file icon
   3  Cover (front)
   4  Cover (back)
   5  Leaflet page
   6  Media (e.g. label side of CD)
   7  Lead artist / Lead performer / Soloist
   8  Artist / Performer
   9  Conductor
   10 Band / Orchestra
   11 Composer
   12 Lyricist / Text writer
   13 Recording Location
   14 During recording
   15 During performance
   16 Movie / Video screen capture
   17 A bright colored fish
   18 Illustration
   19 Band / Artist logotype
   20 Publisher / Studio logotype
   == ======================================

   ``description`` is a :class:`C_string`.
   ``data`` is a string of binary image data.

.. method:: ID3v23_APIC_Frame.type_string()

   Returns the ``picture_type`` as a plain string.

.. classmethod:: ID3v23_APIC_Frame.converted(frame_id, image)

   Given an :class:`audiotools.Image` object,
   returns a new :class:`ID3v23_APIC_Frame` object.

ID3v2.4
-------

.. class:: ID3v24Comment(frames)

   This is an ID3v2.4_ tag, one of the three ID3v2 variants used by MP3 files.
   During initialization, it takes a list of :class:`ID3v24_Frame`-compatible
   objects.
   It can then be manipulated like a regular Python dict with keys
   as 4 character frame identifiers and values as lists of :class:`ID3v24_Frame`
   objects - since each frame identifier may occur multiple times.

   For example:

   >>> tag = ID3v24Comment([ID3v24_T___Frame('TIT2', 0, u'Track Title')])
   >>> tag.track_name
   u'Track Title'
   >>> tag['TIT2']
   [ID3v24_T___Frame('TIT2', 0, u'Track Title')]
   >>> tag['TIT2'] = [ID3v24_T___Frame('TIT2', 0, u'New Track Title')]
   >>> tag.track_name
   u'New Track Title'

   Fields are mapped between ID3v2.4 frame identifiers,
   :class:`audiotools.MetaData` and :class:`ID3v24_Frame` objects as follows:

   ========== ================================ ==========================
   Identifier MetaData                         Object
   ---------- -------------------------------- --------------------------
   ``TIT2``   ``track_name``                   :class:`ID3v24_T___Frame`
   ``TRCK``   ``track_number``/``track_total`` :class:`ID3v24_T___Frame`
   ``TPOS``   ``album_number``/``album_total`` :class:`ID3v24_T___Frame`
   ``TALB``   ``album_name``                   :class:`ID3v24_T___Frame`
   ``TPE1``   ``artist_name``                  :class:`ID3v24_T___Frame`
   ``TPE2``   ``performer_name``               :class:`ID3v24_T___Frame`
   ``TPE3``   ``conductor_name``               :class:`ID3v24_T___Frame`
   ``TCOM``   ``composer_name``                :class:`ID3v24_T___Frame`
   ``TMED``   ``media``                        :class:`ID3v24_T___Frame`
   ``TSRC``   ``ISRC``                         :class:`ID3v24_T___Frame`
   ``TCOP``   ``copyright``                    :class:`ID3v24_T___Frame`
   ``TPUB``   ``publisher``                    :class:`ID3v24_T___Frame`
   ``TYER``   ``year``                         :class:`ID3v24_T___Frame`
   ``TRDA``   ``date``                         :class:`ID3v24_T___Frame`
   ``COMM``   ``comment``                      :class:`ID3v24_COMM_Frame`
   ``APIC``   ``images()``                     :class:`ID3v24_APIC_Frame`
   ========== ================================ ==========================

ID3v2.4 Frame
^^^^^^^^^^^^^

.. class:: ID3v24_Frame(frame_id, data)

   This is the base class for the various ID3v2.4 frames.
   ``frame_id`` is a 4 character string and ``data`` is
   the frame's contents as a string.

.. method:: ID3v24_Frame.copy()

   Returns a new copy of this frame.

.. method:: ID3v24_Frame.raw_info()

   Returns this frame as a human-readable unicode string.

.. classmethod:: ID3v24_Frame.parse(frame_id, frame_size, reader)

   Given a 4 byte frame ID, frame size and
   :class:`audiotools.bitstream.BitstreamReader`
   (positioned past the 10 byte frame header)
   returns a parsed :class:`ID3v24_Frame` object.

.. method:: ID3v24_Frame.build(writer)

   Writes frame to the given
   :class:`audiotools.bitstream.BitstreamWriter`,
   not including its 10 byte frame header.

.. method:: ID3v24_Frame.size()

   Returns the frame's size, not including its 10 byte frame header.

.. method:: ID3v24_Frame.clean(fixes_performed)

   Returns a new :class:`ID3v24_Frame` object that's been cleaned
   of any problems.
   Any fixes performed are appended to ``fixes_performed``
   as unicode strings.

ID3v2.4 Text Frames
^^^^^^^^^^^^^^^^^^^

.. class:: ID3v24_T___Frame(frame_id, encoding, data)

   This :class:`ID3v24_Frame`-compatible object is a container
   for textual data.
   ``frame_id`` is a 3 character string, ``data`` is a binary string
   and ``encoding`` is one of the following integers representing a
   text encoding:

   = =========
   0 Latin-1_
   1 UTF-16_
   2 UTF-16BE_
   3 UTF-8_
   = =========

.. method:: ID3v24_T___Frame.number()

   Returns the first integer portion of the frame data as an int
   if the frame is container for numerical data such as
   ``TRCK`` or ``TPOS``.

.. method:: ID3v24_T___Frame.total()

   Returns the second integer portion of the frame data as an int
   if the frame is a numerical container and has a "total" field.
   For example:

   >>> f = ID3v24_T___Frame('TRCK', 0, '1/2')
   >>> f.number()
   1
   >>> f.total()
   2

.. classmethod:: ID3v24_T___Frame.converted(frame_id, unicode_string)

   Given a 4 byte frame ID and unicode string,
   returns a new :class:`ID3v24_T___Frame` object.

.. class:: ID3v24_TXXX_Frame(encoding, description, data)

   This subclass of :class:`ID3v24_T___Frame` contains
   an additional ``description`` binary string field
   to hold user-defined textual data.

ID3v2.4 Web Frames
^^^^^^^^^^^^^^^^^^

.. class:: ID3v24_W___Frame(frame_id, url)

   This :class:`ID3v24_Frame`-compatible object is a container
   for web links.
   ``frame_id`` is a 4 character string, ``url`` is a binary string.

.. class:: ID3v24_WXXX_Frame(encoding, description, url)

   This subclass of :class:`ID3v24_W___Frame` contains
   an additional ``description`` binary string field
   to hold user-defined web link data.

ID3v2.4 COMM Frame
^^^^^^^^^^^^^^^^^^

.. class:: ID3v24_COMM_Frame(encoding, language, short_description, data)

   This :class:`ID3v24_Frame`-compatible object is for holding
   a potentially large block of comment data.
   ``encoding`` is the same as in text frames:

   = =========
   0 Latin-1_
   1 UTF-16_
   2 UTF-16BE_
   3 UTF-8_
   = =========

   ``language`` is a 3 character string, such as ``"eng"`` for English.
   ``short_description`` is a :class:`C_string` object.
   ``data`` is a binary string.

.. classmethod:: ID3v24_COMM_Frame.converted(frame_id, unicode_string)

   Given a 4 byte ``"COMM"`` frame ID and unicode string,
   returns a new :class:`ID3v23_COMM_Frame` object.

ID3v2.4 APIC Frame
^^^^^^^^^^^^^^^^^^

.. class:: ID3v24_APIC_Frame(mime_type, picture_type, description, data)

   This is a subclass of :class:`audiotools.Image`, in addition
   to being a :class:`ID3v24_Frame`-compatible object.
   ``mime_type`` is a :class:`C_string`.
   ``picture_type`` is an integer representing one of the following:

   == ======================================
   0  Other
   1  32x32 pixels 'file icon' (PNG only)
   2  Other file icon
   3  Cover (front)
   4  Cover (back)
   5  Leaflet page
   6  Media (e.g. label side of CD)
   7  Lead artist / Lead performer / Soloist
   8  Artist / Performer
   9  Conductor
   10 Band / Orchestra
   11 Composer
   12 Lyricist / Text writer
   13 Recording Location
   14 During recording
   15 During performance
   16 Movie / Video screen capture
   17 A bright colored fish
   18 Illustration
   19 Band / Artist logotype
   20 Publisher / Studio logotype
   == ======================================

   ``description`` is a :class:`C_string`.
   ``data`` is a string of binary image data.

.. method:: ID3v24_APIC_Frame.type_string()

   Returns the ``picture_type`` as a plain string.

.. classmethod:: ID3v24_APIC_Frame.converted(frame_id, image)

   Given an :class:`audiotools.Image` object,
   returns a new :class:`ID3v24_APIC_Frame` object.

ID3 Comment Pair
----------------

Often, MP3 files are tagged with both an ID3v2 comment and an ID3v1 comment
for maximum compatibility.
This class encapsulates both comments into a single class.

.. class:: ID3CommentPair(id3v2_comment, id3v1_comment)

   ``id3v2_comment`` is an :class:`ID3v22Comment`, :class:`ID3v23Comment`
   or :class:`ID3v24Comment`.
   ``id3v1_comment`` is an :class:`ID3v1Comment`.
   When getting :class:`audiotools.MetaData` attributes,
   the ID3v2 comment is used by default.
   Set attributes are propagated to both.
   For example:

   >>> tag = ID3CommentPair(ID3v23Comment([ID3v23_T___Frame('TIT2', 0, 'Title 1')]),
   ...                      ID3v1Comment(u'Title 2',u'',u'',u'',u'',1, 0))
   >>> tag.track_name
   u'Title 1'
   >>> tag.track_name = u'New Track Title'
   >>> unicode(tag.id3v2['TIT2'][0])
   u'New Track Title'
   >>> tag.id3v1.track_name
   u'New Track Title'

.. data:: ID3CommentPair.id3v2

   The embedded :class:`ID3v22Comment`, :class:`ID3v23Comment`
   or :class:`ID3v24Comment`

.. data:: ID3CommentPair.id3v1

   The embedded :class:`ID3v1Comment`

M4A
---

.. class:: M4A_META_Atom(version, flags, leaf_atoms)

   This is the metadata format used by QuickTime-compatible formats such as
   M4A and Apple Lossless.
   ``version`` and ``flags`` are integers (typically 0)
   and ``leaf_atoms`` is a list of atom objects,
   one of which should be an ``ilst`` tree atom.
   In addition to being a :class:`audiotools.MetaData` subclass,
   this is also a :class:`M4A_Tree_Atom` subclass
   with several methods specific for metadata.
   As an example:

   >>> tag = M4A_META_Atom(0, 0,
   ...                     [M4A_Tree_Atom('ilst',
   ...                                    [M4A_ILST_Leaf_Atom('\xa9nam',
   ...                                                        [M4A_ILST_Unicode_Data_Atom(0, 1, "Track Name")])])])
   >>> tag.track_name
   u'Track Name'
   >>> tag['ilst']['\xa9nam']
   ... M4A_ILST_Leaf_Atom('\xa9nam', [M4A_ILST_Unicode_Data_Atom(0, 1, 'Track Name')])
   >>> tag['ilst'].replace_child(M4A_ILST_Leaf_Atom('\xa9nam',
   ...                                              [M4A_ILST_Unicode_Data_Atom(0, 1, 'New Track Name')])
   >>> tag.track_name
   u'New Track Name'

   Fields are mapped between :class:`M4AMetaData`,
   :class:`audiotools.MetaData` and iTunes as follows:

   ============= ================================ ============
   M4AMetaData   MetaData                         iTunes
   ------------- -------------------------------- ------------
   ``"\xA9nam"`` ``track_name``                   Name
   ``"\xA9ART"`` ``artist_name``                  Artist
   ``"\xA9day"`` ``year``                         Year
   ``"trkn"``    ``track_number``/``track_total`` Track Number
   ``"disk"``    ``album_number``/``album_total`` Album Number
   ``"\xA9alb"`` ``album_name``                   Album
   ``"\xA9wrt"`` ``composer_name``                Composer
   ``"\xA9cmt"`` ``comment``                      Comment
   ``"cprt"``    ``copyright``
   ============= ================================ ============

   Note that several of the 4 character keys are prefixed by
   the non-ASCII byte ``0xA9``.

.. method:: M4A_META_Atom.has_ilst_atom()

   Returns ``True`` if the atom has an ``ilst`` child atom.

.. method:: M4A_META_Atom.ilst_atom()

   Returns the first ``ilst`` child atom,
   or ``None`` if no ``ilst`` atom is present.

.. method:: M4A_META_Atom.add_ilst_atom()

   Appends a new, empty ``ilst`` atom after
   the first ``hdlr`` atom, if any.

.. method:: M4A_META_Atom.raw_info()

   Returns atom data as a human-readable unicode string.

.. classmethod:: M4A_META_Atom.parse(name, data_size, reader, parsers)

   Given a 4 byte atom name, size of the entire atom in bytes,
   a :class:`audiotools.bitstream.BitstreamReader`,
   and a dict of atom name strings -> atom classes,
   returns a new :class:`M4A_META_Atom` object.

   When parsing sub atoms, any atom name in the parsers dict
   is handled recursively via its value's ``parse`` classmethod.
   If the atom name is not present, the atom is treated as
   a generic :class:`M4A_Leaf_Atom`.

.. method:: M4A_META_Atom.build(writer)

   Writes the atom's contents to the given
   :class:`audiotools.bitstream.BitstreamWriter`
   recursively via its sub-atoms' ``build`` methods.
   This does *not* include the atom's 64-bit size / name header.

.. method:: M4A_META_Atom.size()

   Returns the size of the atom data in bytes,
   not including its 64-bit size / name header.

M4A Leaf Atom
^^^^^^^^^^^^^

.. class:: M4A_Leaf_Atom(name, data)

   ``name`` is a 4 byte atom name string.
   ``data`` is a string of raw atom data.

.. method:: M4A_Leaf_Atom.copy()

   Returns a duplicate copy of the atom.

.. method:: M4A_Leaf_Atom.raw_info()

   Returns atom data as a human-readable unicode string.

.. method:: M4A_Leaf_Atom.parse(name, size, reader, parsers)

   Given a 4 byte atom name, size of the entire atom in bytes,
   a :class:`audiotools.bitstream.BitstreamReader`
   and an unused dict of atom name strings -> atom classes,
   returns a new :class:`M4A_Leaf_Atom` object.

.. method:: M4A_Leaf_Atom.build(writer)

   Writes the atom's contents to the given
   :class:`audiotools.bitstream.BitstreamWriter`.
   This does *not* include the atom's 64-bit size / name header.

.. method:: M4A_Leaf_Atom.size()

   Returns the size of the atom data in bytes,
   not including its 64-bit size / name header.

M4A Tree Atom
^^^^^^^^^^^^^

.. class:: M4A_Tree_Atom(name, leaf_atoms)

   ``name`` is a 4 byte atom name string.
   ``leaf_atoms`` is a list of atom-compatible objects,
   typically :class:`M4A_Leaf_Atom`, :class:`M4A_Tree_Atom`
   or subclasses of either.

.. method:: M4A_Tree_Atom.copy()

   Returns a duplicate copy of the atom.

.. method:: M4A_Tree_Atom.raw_info()

   Returns atom data as a human-readable unicode string.

.. method:: M4A_Tree_Atom.parse(name, data_size, reader, parsers)

   Given a 4 byte atom name, size of the entire atom in bytes,
   a :class:`audiotools.bitstream.BitstreamReader`,
   and a dict of atom name strings -> atom classes,
   returns a new :class:`M4A_META_Atom` object.

   When parsing sub atoms, any atom name in the parsers dict
   is handled recursively via its value's ``parse`` classmethod.
   If the atom name is not present, the atom is treated as
   a generic :class:`M4A_Leaf_Atom`.

.. method:: M4A_Tree_Atom.build(writer)

   Writes the atom's contents to the given
   :class:`audiotools.bitstream.BitstreamWriter`
   recursively via its sub-atoms' ``build`` methods.
   This does *not* include the atom's 64-bit size / name header.

.. method:: M4A_Tree_Atom.size()

   Returns the size of the atom data in bytes,
   not including its 64-bit size / name header.

.. method:: M4A_Tree_Atom.get_child(atom_name)

   Given a 4 byte atom name string,
   returns the first instance of that child atom.
   Raises :exc:`KeyError` if the child is not found.

.. method:: M4A_Tree_Atom.has_child(atom_name)

   Given a 4 byte atom name string,
   returns ``True`` if that child atom is present.

.. method:: M4A_Tree_Atom.add_child(atom_object)

   Appends an atom-compatible object,
   to this atom's list of children.

.. method:: M4A_Tree_Atom.remove_child(atom_name)

   Given a 4 byte atom name string,
   removes the first instance of that child, if any.

.. method:: M4A_Tree_Atom.replace_child(atom_object)

   Replaces the first child atom with the same name
   with the given atom-compatible object.

.. method:: M4A_Tree_Atom.child_offset(*child_path)

   Given a list of 4 byte atom name strings,
   recursively searches :class:`M4A_Tree_Atom`-compatible
   sub-children and returns the byte offset
   of the final child atom.
   Raises :exc:`KeyError` if the child atom cannot be found.

M4A ILST Leaf Atom
^^^^^^^^^^^^^^^^^^

This atom is a subclass of :class:`M4A_Tree_Atom`
specialized for holding M4A metadata fields
and mapping them to Python values.

.. class:: M4A_ILST_Leaf_Atom(name, leaf_atoms)

   ``name`` is a 4 byte atom name string.
   ``leaf_atoms`` is a list of atom-compatible objects,

.. method:: M4A_ILST_Leaf_Atom.__unicode__()

   Returns the unicode value of this leaf's first ``data`` child atom.

   >>> nam = M4A_ILST_Leaf_Atom("\xa9nam",
   ...                          [M4A_ILST_Unicode_Data_Atom(0, 1, "Track Name")])
   >>> unicode(nam)
   u"Track Name"

.. method:: M4A_ILST_Leaf_Atom.__int__()

   Returns the integer value of this leaf's first ``data`` child atom.

   >>> trkn = M4A_ILST_Leaf_Atom("trkn",
   ...                           [M4A_ILST_TRKN_Data_Atom(1, 2)])
   >>> int(trkn)
   1

.. method:: M4A_ILST_Leaf_Atom.total()

   Returns the total integer value of this leaf's first ``data`` child atom.

   >>> trkn = M4A_ILST_Leaf_Atom("trkn",
   ...                           [M4A_ILST_TRKN_Data_Atom(1, 2)])
   >>> trkn.total()
   2

M4A ILST Unicode Data Atom
^^^^^^^^^^^^^^^^^^^^^^^^^^

This atom is a subclass of :class:`M4A_Leaf_Atom`
specialized for holding unicode data.

.. class:: M4A_ILST_Unicode_Data_Atom(type, flags, data)

   ``type`` is an integer (typically 0),
   ``flags`` is an integer (typically 1),
   ``data`` is a binary string of UTF-8-encoded data.
   The atom's ``name`` field is always ``"data"``.

.. method:: M4A_ILST_Unicode_Data_Atom.__unicode__()

   Returns the unicode value of this atom's data.

   >>> nam = M4A_ILST_Unicode_Data_Atom(0, 1, "Track Name")
   >>> unicode(nam)
   u"Track Name"

M4A ILST Track Number Atom
^^^^^^^^^^^^^^^^^^^^^^^^^^

This atom is a subclass of :class:`M4A_Leaf_Atom`
specialized for holding track number data.

.. class:: M4A_ILST_TRKN_Data_Atom(track_number, track_total)

   ``track_number`` and ``track_total`` are both integers.
   Its ``name`` field is always ``"data"``.

.. method:: M4A_ILST_TRKN_Data_Atom.__int__()

   Returns this atom's ``track_number`` value.

   >>> trkn = M4A_ILST_TRKN_Data_Atom(1, 2)
   >>> int(trkn)
   1

.. method:: M4A_ILST_TRKN_Data_Atom.total()

   Returns this atom's ``track_total`` value.

   >>> trkn = M4A_ILST_TRKN_Data_Atom(1, 2)
   >>> trkn.total()
   2

M4A ILST Disc Number Atom
^^^^^^^^^^^^^^^^^^^^^^^^^

This atom is a subclass of :class:`M4A_Leaf_Atom`
specialized for holding disc number data.

.. class:: M4A_ILST_DISK_Data_Atom(disc_number, disc_total)

   ``disc_number`` and ``disc_total`` are both integers.
   Its ``name`` field is always ``"data"``.

.. method:: M4A_ILST_DISK_Data_Atom.__int__()

   Returns this atom's ``disc_number`` value.

   >>> disk = M4A_ILST_DISK_Data_Atom(3, 4)
   >>> int(disk)
   3

.. method:: M4A_ILST_DISK_Data_Atom.total()

   Returns this atom's ``disc_total`` value.

   >>> trkn = M4A_ILST_DISK_Data_Atom(3, 4)
   >>> trkn.total()
   4

M4A ILST Cover Art Atom
^^^^^^^^^^^^^^^^^^^^^^^

This atom is a subclass of :class:`M4A_Leaf_Atom` and of
:class:`audiotools.Image`.

.. class:: M4A_ILST_COVR_Data_Atom(version, flags, image_data)

   ``version`` is an integer (typically 0).
   ``flags`` is an integer (typically 0).
   ``image_data`` is a binary string of cover art data.
   Its ``name`` field is always ``"data"``.

   This atom parses its raw image data to populate
   its :class:`audiotools.Image`-specific methods and fields.

Vorbis Comment
--------------

.. class:: VorbisComment(comment_strings, vendor_string)

   This is a VorbisComment_ tag used by FLAC, Ogg FLAC, Ogg Vorbis,
   Ogg Speex and other formats in the Ogg family.
   ``comment_strings`` is a list of unicode strings.
   ``vendor_string`` is a unicode string.
   Once initialized, :class:`VorbisComment` can be manipulated like a
   regular Python dict in addition to its standard
   :class:`audiotools.MetaData` methods.

   For example:

   >>> tag = VorbisComment([u'TITLE=Track Title'], u'Vendor String')
   >>> tag.track_name
   u'Track Title'
   >>> tag[u'TITLE']
   [u'New Title']
   >>> tag[u'TITLE'] = [u'New Title']
   >>> tag.track_name
   u'New Title'

   Fields are mapped between :class:`VorbisComment` and
   :class:`audiotools.MetaData` as follows:

   ================= ==================
   VorbisComment     Metadata
   ----------------- ------------------
   ``TITLE``         ``track_name``
   ``TRACKNUMBER``   ``track_number``
   ``TRACKTOTAL``    ``track_total``
   ``DISCNUMBER``    ``album_number``
   ``DISCTOTAL``     ``album_total``
   ``ALBUM``         ``album_name``
   ``ARTIST``        ``artist_name``
   ``PERFORMER``     ``performer_name``
   ``COMPOSER``      ``composer_name``
   ``CONDUCTOR``     ``conductor_name``
   ``SOURCE MEDIUM`` ``media``
   ``ISRC``          ``ISRC``
   ``CATALOG``       ``catalog``
   ``COPYRIGHT``     ``copyright``
   ``PUBLISHER``     ``publisher``
   ``DATE``          ``year``
   ``COMMENT``       ``comment``
   ================= ==================

   Note that if the same key is used multiple times,
   the metadata attribute only indicates the first one:

   >>> tag = VorbisComment([u"TITLE=Title1", u"TITLE=Title2"], u"Vendor String")
   >>> tag.track_name
   u'Title1'

.. _APEv2: http://wiki.hydrogenaudio.org/index.php?title=APEv2

.. _ID3v1: http://www.id3.org/ID3v1

.. _FLAC: http://flac.sourceforge.net/format.html#metadata_block

.. _VorbisComment: http://www.xiph.org/vorbis/doc/v-comment.html

.. _ID3v2.2: http://www.id3.org/id3v2-00

.. _ID3v2.3: http://www.id3.org/d3v2.3.0

.. _ID3v2.4: http://www.id3.org/id3v2.4.0-structure

.. _Latin-1: http://en.wikipedia.org/wiki/Latin-1

.. _UCS-2: http://en.wikipedia.org/wiki/UTF-16

.. _UTF-16: http://en.wikipedia.org/wiki/UTF-16

.. _UTF-16BE: http://en.wikipedia.org/wiki/UTF-16

.. _UTF-8: http://en.wikipedia.org/wiki/UTF-8
