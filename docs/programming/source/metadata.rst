Meta Data Formats
=================

Although it's more convenient to manipulate the high-level
:class:`audiotools.MetaData` base class, one sometimes needs to be
able to view and modify the low-level implementation also.

ApeTag
------

.. class:: ApeTag(tags[, tag_length])

   This is an APEv2_ tag used by the WavPack, Monkey's Audio
   and Musepack formats, among others.
   During initialization, it takes a list of :class:`ApeTagItem` objects
   and an optional length integer (typically set only by
   :func:`get_metadata` methods which already know the tag's total length).
   It can then be manipulated like a regular Python dict
   with keys as strings and values as :class:`ApeTagItem` objects.
   Note that this is also a :class:`audiotools.MetaData` subclass
   with all of the same methods.

   For example:

   >>> tag = ApeTag([ApeTagItem(0,False,'Title',u'Track Title'.encode('utf-8'))])
   >>> tag.track_name
   u'Track Title'
   >>> tag['Title']
   ApeTagItem(0,False,'Title','Track Title')
   >>> tag['Title'] = ApeTagItem(0,False,'Title',u'New Title'.encode('utf-8'))
   >>> tag.track_name
   u'New Title'
   >>> tag.track_name = u'Yet Another Title'
   >>> tag['Title']
   ApeTagItem(0,False,'Title','Yet Another Title')

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

   >>> tag = ApeTag([ApeTagItem(0,False,'Track',u'1'.encode('utf-8'))])
   >>> tag.track_number
   1
   >>> tag.track_total
   0
   >>> tag = ApeTag([ApeTagItem(0,False,'Track',u'2/3'.encode('utf-8'))])
   >>> tag.track_number
   2
   >>> tag.track_total
   3

.. classmethod:: ApeTag.read(file)

   Takes an open file object and returns an :class:`ApeTag` object
   of that file's APEv2 data, or ``None`` if the tag cannot be found.

.. method:: ApeTag.build()

   Returns this tag's complete APEv2 data as a string.

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
   It is initialized with a list of :class:`FlacMetaDataBlock`
   objects which it stores internally in one of several fields.
   It also supports all :class:`audiotools.MetaData` methods.

   For example:

   >>> tag = FlacMetaData([FlacMetaDataBlock(
   ...                     type=4,
   ...                     data=FlacVorbisComment({u'TITLE':[u'Track Title']}).build())])
   >>> tag.track_name
   u'Track Title'
   >>> tag.vorbis_comment[u'TITLE']
   [u'Track Title']
   >>> tag.vorbis_comment = a.FlacVorbisComment({u'TITLE':[u'New Track Title']})
   >>> tag.track_name
   u'New Track Title'

   Its fields are as follows:

.. data:: FlacMetaData.streaminfo

   A :class:`FlacMetaDataBlock` object containing raw ``STREAMINFO`` data.
   Since FLAC's :func:`set_metadata` method will override this attribute
   as necessary, one will rarely need to parse it or set it.

.. data:: FlacMetaData.vorbis_comment

   A :class:`FlacVorbisComment` object containing text data
   such as track name and artist name.
   If the FLAC file doesn't have a ``VORBISCOMMENT`` block,
   :class:`FlacMetaData` will set an empty one at initialization time
   which will then be written out by a call to :func:`set_metadata`.

.. data:: FlacMetaData.cuesheet

   A :class:`FlacCueSheet` object containing ``CUESHEET`` data, or ``None``.

.. data:: FlacMetaData.image_blocks

   A list of :class:`FlacPictureComment` objects, each representing
   a ``PICTURE`` block.
   The list may be empty.

.. data:: FlacMetaData.extra_blocks

   A list of raw :class:`FlacMetaDataBlock` objects containing
   any unknown or unsupported FLAC metadata blocks.
   Note that padding is not stored here.
   ``PADDING`` blocks are discarded at initialization time
   and then re-created as needed by calls to :func:`set_metadata`.

.. method:: FlacMetaData.metadata_blocks()

   Returns an iterator over all the current blocks as
   :class:`FlacMetaDataBlock`-compatible objects and without
   any padding block at the end.

.. method:: FlacMetaData.build([padding_size])

   Returns a string of this :class:`FlacMetaData` object's contents.

.. class:: FlacMetaDataBlock(type, data)

   This is a simple container for FLAC metadata block data.
   ``type`` is one of the following block type integers:

   = ==================
   0 ``STREAMINFO``
   1 ``PADDING``
   2 ``APPLICATION``
   3 ``SEEKTABLE``
   4 ``VORBIS_COMMENT``
   5 ``CUESHEET``
   6 ``PICTURE``
   = ==================

   ``data`` is a string.

.. method:: FlacMetaDataBlock.build_block([last])

   Returns the entire metadata block as a string, including the header.
   Set ``last`` to 1 to indicate this is the final metadata block in the stream.

.. class:: FlacVorbisComment(vorbis_data[, vendor_string])

   This is a subclass of :class:`VorbisComment` modified to be
   FLAC-compatible.
   It utilizes the same initialization information and field mappings.

.. method:: FlacVorbisComment.build_block([last])

   Returns the entire metadata block as a string, including the header.
   Set ``last`` to 1 to indicate this is the final metadata block in the stream.
.. class:: FlacPictureComment(type, mime_type, description, width, height, color_depth, color_count, data)

   This is a subclass of :class:`audiotools.Image` with additional
   methods to make it FLAC-compatible.

.. method:: FlacPictureComment.build()

   Returns this picture data as a block data string, without the metadata
   block headers.
   Raises :exc:`FlacMetaDataBlockTooLarge` if the size of its
   picture data exceeds 16777216 bytes.

.. method:: FlacPictureComment.build_block([last])

   Returns the entire metadata block as a string, including the header.
   Set ``last`` to 1 to indicate this is the final metadata block in the stream.

.. class:: FlacCueSheet(container[, sample_rate])

   This is a :class:`audiotools.cue.Cuesheet`-compatible object
   with :func:`catalog`, :func:`ISRCs`, :func:`indexes` and
   :func:`pcm_lengths` methods, in addition to those needed to make it
   FLAC metadata block compatible.
   Its ``container`` argument is an :class:`audiotools.Con.Container` object
   which is returned by calling :func:`FlacCueSheet.CUESHEET.parse`
   on a raw input data string.

.. method:: FlacCueSheet.build_block([last])

   Returns the entire metadata block as a string, including the header.
   Set ``last`` to 1 to indicate this is the final metadata block in the stream.

.. classmethod:: FlacCueSheet.converted(sheet, total_frames[, sample_rate])

   Takes another :class:`audiotools.cue.Cuesheet`-compatible object
   and returns a new :class:`FlacCueSheet` object.



ID3v1
-----

.. class:: ID3v1Comment(metadata)

   This is an ID3v1_ tag which is often appended to MP3 files.
   During initialization, it takes a tuple of 6 values -
   in the same order as returned by :func:`ID3v1Comment.read_id3v1_comment`.
   It can then be manipulated like a regular Python list,
   in addition to the regular :class:`audiotools.MetaData` methods.
   However, since ID3v1 is a near completely subset
   of :class:`audiotools.MetaData`
   (the genre integer is the only field not represented),
   there's little need to reference its items by index directly.

   For example:

   >>> tag = ID3v1Comment((u'Track Title',u'',u'',u'',u'',1))
   >>> tag.track_name
   u'Track Title'
   >>> tag[0] = u'New Track Name'
   >>> tag.track_name
   u'New Track Name'

   Fields are mapped between :class:`ID3v1Comment` and
   :class:`audiotools.MetaData` as follows:

   ===== ================
   Index Metadata
   ----- ----------------
   0     ``track_name``
   1     ``artist_name``
   2     ``album_name``
   3     ``year``
   4     ``comment``
   5     ``track_number``
   ===== ================

.. method:: ID3v1Comment.build_tag()

   Returns this tag as a string.

.. classmethod:: ID3v1Comment.build_id3v1(song_title, artist, album, year, comment, track_number)

   A convenience method which takes several unicode strings
   (except for ``track_number``, an integer) and returns
   a complete ID3v1 tag as a string.

.. classmethod:: ID3v1Comment.read_id3v1_comment(filename)

   Takes an MP3 filename string and returns a tuple of that file's
   ID3v1 tag data, or tag data with empty fields if no ID3v1 tag is found.

ID3v2.2
-------

.. class:: ID3v22Comment(frames)

   This is an ID3v2.2_ tag, one of the three ID3v2 variants used by MP3 files.
   During initialization, it takes a list of :class:`ID3v22Frame`-compatible
   objects.
   It can then be manipulated list a regular Python dict with keys
   as 3 character frame identifiers and values as lists of :class:`ID3v22Frame`
   objects - since each frame identifier may occur multiple times.

   For example:

   >>> tag = ID3v22Comment([ID3v22TextFrame('TT2',0,u'Track Title')])
   >>> tag.track_name
   u'Track Title'
   >>> tag['TT2']
   [<audiotools.__id3__.ID3v22TextFrame instance at 0x1004c17a0>]
   >>> tag['TT2'] = [ID3v22TextFrame('TT2',0,u'New Track Title')]
   >>> tag.track_name
   u'New Track Title'

   Fields are mapped between ID3v2.2 frame identifiers,
   :class:`audiotools.MetaData` and :class:`ID3v22Frame` objects as follows:

   ========== ================================ ========================
   Identifier MetaData                         Object
   ---------- -------------------------------- ------------------------
   ``TT2``    ``track_name``                   :class:`ID3v22TextFrame`
   ``TRK``    ``track_number``/``track_total`` :class:`ID3v22TextFrame`
   ``TPA``    ``album_number``/``album_total`` :class:`ID3v22TextFrame`
   ``TAL``    ``album_name``                   :class:`ID3v22TextFrame`
   ``TP1``    ``artist_name``                  :class:`ID3v22TextFrame`
   ``TP2``    ``performer_name``               :class:`ID3v22TextFrame`
   ``TP3``    ``conductor_name``               :class:`ID3v22TextFrame`
   ``TCM``    ``composer_name``                :class:`ID3v22TextFrame`
   ``TMT``    ``media``                        :class:`ID3v22TextFrame`
   ``TRC``    ``ISRC``                         :class:`ID3v22TextFrame`
   ``TCR``    ``copyright``                    :class:`ID3v22TextFrame`
   ``TPB``    ``publisher``                    :class:`ID3v22TextFrame`
   ``TYE``    ``year``                         :class:`ID3v22TextFrame`
   ``TRD``    ``date``                         :class:`ID3v22TextFrame`
   ``COM``    ``comment``                      :class:`ID3v22ComFrame`
   ``PIC``    ``images()``                     :class:`ID3v22PicFrame`
   ========== ================================ ========================

.. class:: ID3v22Frame(frame_id, data)

   This is the base class for the various ID3v2.2 frames.
   ``frame_id`` is a 3 character string and ``data`` is
   the frame's contents as a string.

.. method:: ID3v22Frame.build()

   Returns the frame's contents as a string of binary data.

.. classmethod:: ID3v22Frame.parse(container)

   Given a :class:`audiotools.Con.Container` object with data
   parsed from ``audiotools.ID3v22Frame.FRAME``,
   returns an :class:`ID3v22Frame` or one of its subclasses,
   depending on the frame identifier.

.. class:: ID3v22TextFrame(frame_id, encoding, string)

   This is a container for textual data.
   ``frame_id`` is a 3 character string, ``string`` is a unicode string
   and ``encoding`` is one of the following integers representing a
   text encoding:

   = =======
   0 Latin-1
   1 UCS-2
   = =======

.. method:: ID3v22TextFrame.__int__()

   Returns the first integer portion of the frame data as an int.

.. method:: ID3v22TextFrame.total()

   Returns the integer portion of the frame data after the first slash
   as an int.
   For example:

   >>> tag['TRK'] = [ID3v22TextFrame('TRK',0,u'1/2')]
   >>> tag['TRK']
   [<audiotools.__id3__.ID3v22TextFrame instance at 0x1004c6830>]
   >>> int(tag['TRK'][0])
   1
   >>> tag['TRK'][0].total()
   2

.. classmethod:: ID3v22TextFrame.from_unicode(frame_id, s)

   A convenience method for building :class:`ID3v22TextFrame` objects
   from a frame identifier and unicode string.
   Note that if ``frame_id`` is ``"COM"``, this will build an
   :class:`ID3v22ComFrame` object instead.

.. class:: ID3v22ComFrame(encoding, language, short_description, content)

   This frame is for holding a potentially large block of comment data.
   ``encoding`` is the same as in text frames:

   = =======
   0 Latin-1
   1 UCS-2
   = =======

   ``language`` is a 3 character string, such as ``"eng"`` for english.
   ``short_description`` and ``content`` are unicode strings.

.. classmethod:: ID3v22ComFrame.from_unicode(s)

   A convenience method for building :class:`ID3v22ComFrame` objects
   from a unicode string.

.. class:: ID3v22PicFrame(data, format, description, pic_type)

   This is a subclass of :class:`audiotools.Image`, in addition
   to being an ID3v2.2 frame.
   ``data`` is a string of binary image data.
   ``format`` is a 3 character unicode string identifying the image type:

   ========== ======
   ``u"PNG"`` PNG
   ``u"JPG"`` JPEG
   ``u"BMP"`` Bitmap
   ``u"GIF"`` GIF
   ``u"TIF"`` TIFF
   ========== ======

   ``description`` is a unicode string.
   ``pic_type`` is an integer representing one of the following:

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
   17 A bright coloured fish
   18 Illustration
   19 Band / Artist logotype
   20 Publisher / Studio logotype
   == ======================================

.. method:: ID3v22PicFrame.type_string()

   Returns the ``pic_type`` as a plain string.

.. classmethod:: ID3v22PicFrame.converted(image)

   Given an :class:`audiotools.Image` object,
   returns a new :class:`ID3v22PicFrame` object.

ID3v2.3
-------

.. class:: ID3v23Comment(frames)

   This is an ID3v2.3_ tag, one of the three ID3v2 variants used by MP3 files.
   During initialization, it takes a list of :class:`ID3v23Frame`-compatible
   objects.
   It can then be manipulated list a regular Python dict with keys
   as 4 character frame identifiers and values as lists of :class:`ID3v23Frame`
   objects - since each frame identifier may occur multiple times.

   For example:

   >>> tag = ID3v23Comment([ID3v23TextFrame('TIT2',0,u'Track Title')])
   >>> tag.track_name
   u'Track Title'
   >>> tag['TIT2']
   [<audiotools.__id3__.ID3v23TextFrame instance at 0x1004c6680>]
   >>> tag['TIT2'] = [ID3v23TextFrame('TIT2',0,u'New Track Title')]
   >>> tag.track_name
   u'New Track Title'


   Fields are mapped between ID3v2.3 frame identifiers,
   :class:`audiotools.MetaData` and :class:`ID3v23Frame` objects as follows:

   ========== ================================ ========================
   Identifier MetaData                         Object
   ---------- -------------------------------- ------------------------
   ``TIT2``   ``track_name``                   :class:`ID3v23TextFrame`
   ``TRCK``   ``track_number``/``track_total`` :class:`ID3v23TextFrame`
   ``TPOS``   ``album_number``/``album_total`` :class:`ID3v23TextFrame`
   ``TALB``   ``album_name``                   :class:`ID3v23TextFrame`
   ``TPE1``   ``artist_name``                  :class:`ID3v23TextFrame`
   ``TPE2``   ``performer_name``               :class:`ID3v23TextFrame`
   ``TPE3``   ``conductor_name``               :class:`ID3v23TextFrame`
   ``TCOM``   ``composer_name``                :class:`ID3v23TextFrame`
   ``TMED``   ``media``                        :class:`ID3v23TextFrame`
   ``TSRC``   ``ISRC``                         :class:`ID3v23TextFrame`
   ``TCOP``   ``copyright``                    :class:`ID3v23TextFrame`
   ``TPUB``   ``publisher``                    :class:`ID3v23TextFrame`
   ``TYER``   ``year``                         :class:`ID3v23TextFrame`
   ``TRDA``   ``date``                         :class:`ID3v23TextFrame`
   ``COMM``   ``comment``                      :class:`ID3v23ComFrame`
   ``APIC``   ``images()``                     :class:`ID3v23PicFrame`
   ========== ================================ ========================

.. class:: ID3v23Frame(frame_id, data)

   This is the base class for the various ID3v2.3 frames.
   ``frame_id`` is a 4 character string and ``data`` is
   the frame's contents as a string.

.. method:: ID3v23Frame.build()

   Returns the frame's contents as a string of binary data.

.. classmethod:: ID3v23Frame.parse(container)

   Given a :class:`audiotools.Con.Container` object with data
   parsed from ``audiotools.ID3v23Frame.FRAME``,
   returns an :class:`ID3v23Frame` or one of its subclasses,
   depending on the frame identifier.

.. class:: ID3v23TextFrame(frame_id, encoding, string)

   This is a container for textual data.
   ``frame_id`` is a 4 character string, ``string`` is a unicode string
   and ``encoding`` is one of the following integers representing a
   text encoding:

   = =======
   0 Latin-1
   1 UCS-2
   = =======

.. method:: ID3v23TextFrame.__int__()

   Returns the first integer portion of the frame data as an int.

.. method:: ID3v23TextFrame.total()

   Returns the integer portion of the frame data after the first slash
   as an int.
   For example:

   >>> tag['TRAK'] = [ID3v23TextFrame('TRAK',0,u'3/4')]
   >>> tag['TRAK']
   [<audiotools.__id3__.ID3v23TextFrame instance at 0x1004c17a0>]
   >>> int(tag['TRAK'][0])
   3
   >>> tag['TRAK'][0].total()
   4

.. classmethod:: ID3v23TextFrame.from_unicode(frame_id, s)

   A convenience method for building :class:`ID3v23TextFrame` objects
   from a frame identifier and unicode string.
   Note that if ``frame_id`` is ``"COMM"``, this will build an
   :class:`ID3v23ComFrame` object instead.

.. class:: ID3v23ComFrame(encoding, language, short_description, content)

   This frame is for holding a potentially large block of comment data.
   ``encoding`` is the same as in text frames:

   = =======
   0 Latin-1
   1 UCS-2
   = =======

   ``language`` is a 3 character string, such as ``"eng"`` for english.
   ``short_description`` and ``content`` are unicode strings.

.. classmethod:: ID3v23ComFrame.from_unicode(s)

   A convenience method for building :class:`ID3v23ComFrame` objects
   from a unicode string.

.. class:: ID3v23PicFrame(data, mime_type, description, pic_type)

   This is a subclass of :class:`audiotools.Image`, in addition
   to being an ID3v2.3 frame.
   ``data`` is a string of binary image data.
   ``mime_type`` is a string of the image's MIME type, such as
   ``"image/jpeg"``.

   ``description`` is a unicode string.
   ``pic_type`` is an integer representing one of the following:

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
   17 A bright coloured fish
   18 Illustration
   19 Band / Artist logotype
   20 Publisher / Studio logotype
   == ======================================

.. classmethod:: ID3v23PicFrame.converted(image)

   Given an :class:`audiotools.Image` object,
   returns a new :class:`ID3v23PicFrame` object.

ID3v2.4
-------

.. class:: ID3v24Comment(frames)

   This is an ID3v2.4_ tag, one of the three ID3v2 variants used by MP3 files.
   During initialization, it takes a list of :class:`ID3v24Frame`-compatible
   objects.
   It can then be manipulated list a regular Python dict with keys
   as 4 character frame identifiers and values as lists of :class:`ID3v24Frame`
   objects - since each frame identifier may occur multiple times.

   For example:

   >>> import audiotools as a
   >>> tag = ID3v24Comment([ID3v24TextFrame('TIT2',0,u'Track Title')])
   >>> tag.track_name
   u'Track Title'
   >>> tag['TIT2']
   [<audiotools.__id3__.ID3v24TextFrame instance at 0x1004c17a0>]
   >>> tag['TIT2'] = [ID3v24TextFrame('TIT2',0,'New Track Title')]
   >>> tag.track_name
   u'New Track Title'

   Fields are mapped between ID3v2.4 frame identifiers,
   :class:`audiotools.MetaData` and :class:`ID3v24Frame` objects as follows:

   ========== ================================ ========================
   Identifier MetaData                         Object
   ---------- -------------------------------- ------------------------
   ``TIT2``   ``track_name``                   :class:`ID3v24TextFrame`
   ``TRCK``   ``track_number``/``track_total`` :class:`ID3v24TextFrame`
   ``TPOS``   ``album_number``/``album_total`` :class:`ID3v24TextFrame`
   ``TALB``   ``album_name``                   :class:`ID3v24TextFrame`
   ``TPE1``   ``artist_name``                  :class:`ID3v24TextFrame`
   ``TPE2``   ``performer_name``               :class:`ID3v24TextFrame`
   ``TPE3``   ``conductor_name``               :class:`ID3v24TextFrame`
   ``TCOM``   ``composer_name``                :class:`ID3v24TextFrame`
   ``TMED``   ``media``                        :class:`ID3v24TextFrame`
   ``TSRC``   ``ISRC``                         :class:`ID3v24TextFrame`
   ``TCOP``   ``copyright``                    :class:`ID3v24TextFrame`
   ``TPUB``   ``publisher``                    :class:`ID3v24TextFrame`
   ``TYER``   ``year``                         :class:`ID3v24TextFrame`
   ``TRDA``   ``date``                         :class:`ID3v24TextFrame`
   ``COMM``   ``comment``                      :class:`ID3v24ComFrame`
   ``APIC``   ``images()``                     :class:`ID3v24PicFrame`
   ========== ================================ ========================

.. class:: ID3v24Frame(frame_id, data)

   This is the base class for the various ID3v2.3 frames.
   ``frame_id`` is a 4 character string and ``data`` is
   the frame's contents as a string.

.. method:: ID3v24Frame.build()

   Returns the frame's contents as a string of binary data.

.. classmethod:: ID3v24Frame.parse(container)

   Given a :class:`audiotools.Con.Container` object with data
   parsed from ``audiotools.ID3v24Frame.FRAME``,
   returns an :class:`ID3v24Frame` or one of its subclasses,
   depending on the frame identifier.

.. class:: ID3v24TextFrame(frame_id, encoding, string)

   This is a container for textual data.
   ``frame_id`` is a 4 character string, ``string`` is a unicode string
   and ``encoding`` is one of the following integers representing a
   text encoding:

   = ========
   0 Latin-1
   1 UTF-16
   2 UTF-16BE
   3 UTF-8
   = ========

.. method:: ID3v24TextFrame.__int__()

   Returns the first integer portion of the frame data as an int.

.. method:: ID3v24TextFrame.total()

   Returns the integer portion of the frame data after the first slash
   as an int.
   For example:

   >>> tag['TRAK'] = [ID3v24TextFrame('TRAK',0,u'5/6')]
   >>> tag['TRAK']
   [<audiotools.__id3__.ID3v24TextFrame instance at 0x1004c17a0>]
   >>> int(tag['TRAK'][0])
   5
   >>> tag['TRAK'][0].total()
   6

.. classmethod:: ID3v24TextFrame.from_unicode(frame_id, s)

   A convenience method for building :class:`ID3v24TextFrame` objects
   from a frame identifier and unicode string.
   Note that if ``frame_id`` is ``"COMM"``, this will build an
   :class:`ID3v24ComFrame` object instead.

.. class:: ID3v24ComFrame(encoding, language, short_description, content)

   This frame is for holding a potentially large block of comment data.
   ``encoding`` is the same as in text frames:

   = ========
   0 Latin-1
   1 UTF-16
   2 UTF-16BE
   3 UTF-8
   = ========

   ``language`` is a 3 character string, such as ``"eng"`` for english.
   ``short_description`` and ``content`` are unicode strings.

.. classmethod:: ID3v24ComFrame.from_unicode(s)

   A convenience method for building :class:`ID3v24ComFrame` objects
   from a unicode string.

.. class:: ID3v24PicFrame(data, mime_type, description, pic_type)

   This is a subclass of :class:`audiotools.Image`, in addition
   to being an ID3v2.4 frame.
   ``data`` is a string of binary image data.
   ``mime_type`` is a string of the image's MIME type, such as
   ``"image/jpeg"``.

   ``description`` is a unicode string.
   ``pic_type`` is an integer representing one of the following:

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
   17 A bright coloured fish
   18 Illustration
   19 Band / Artist logotype
   20 Publisher / Studio logotype
   == ======================================

.. classmethod:: ID3v23PicFrame.converted(image)

   Given an :class:`audiotools.Image` object,
   returns a new :class:`ID3v24PicFrame` object.

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
   Set attributes are propogated to both.
   For example:

   >>> tag = ID3CommentPair(ID3v23Comment([ID3v23TextFrame('TIT2',0,u'Title 1')]),
   ...                      ID3v1Comment((u'Title 2',u'',u'',u'',u'',1)))
   >>> tag.track_name
   u'Title 1'
   >>> tag.track_name = u'New Track Title'
   >>> unicode(tag.id3v2['TIT2'][0])
   u'New Track Title'
   >>> tag.id3v1[0]
   u'New Track Title'

.. data:: ID3CommentPair.id3v2

   The embedded :class:`ID3v22Comment`, :class:`ID3v23Comment`
   or :class:`ID3v24Comment`

.. data:: ID3CommentPair.id3v1

   The embedded :class:`ID3v1Comment`

M4A
---

.. class:: M4AMetaData(ilst_atoms)

   This is the metadata format used by QuickTime-compatible formats such as
   M4A and Apple Lossless.
   Due to its relative complexity, :class:`M4AMetaData`'s
   implementation is more low-level than others.
   During initialization, it takes a list of :class:`ILST_Atom`-compatible
   objects.
   It can then be manipulated like a regular Python dict with keys
   as 4 character atom name strings and values as a list of
   :class:`ILST_Atom` objects.
   It is also a :class:`audiotools.MetaData` subclass.
   Note that ``ilst`` atom objects are relatively opaque and easier to handle
   via convenience builders.

   As an example:

   >>> tag = M4AMetaData(M4AMetaData.text_atom(chr(0xA9) + 'nam',u'Track Name'))
   >>> tag.track_name
   u'Track Name'
   >>> tag[chr(0xA9) + 'nam']
   [ILST_Atom('\xa9nam',[__Qt_Atom__('data','\x00\x00\x00\x01\x00\x00\x00\x00Track Name',0)])]
   >>> tag[chr(0xA9) + 'nam'] = M4AMetaData.text_atom(chr(0xA9) + 'nam',u'New Track Name')
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
   ``"aART"``    ``performer_name``               Album Artist
   ``"trkn"``    ``track_number``/``track_total`` Track Number
   ``"disk"``    ``album_number``/``album_total`` Album Number
   ``"\xA9alb"`` ``album_name``                   Album
   ``"\xA9wrt"`` ``composer_name``                Composer
   ``"\xA9cmt"`` ``comment``                      Comment
   ``"cprt"``    ``copyright``
   ============= ================================ ============

   Note that several of the 4 character keys are prefixed by
   the non-ASCII byte ``0xA9``.

.. method:: M4AMetaData.to_atom(previous_meta)

   This takes the previous M4A ``meta`` atom as a string and returns
   a new :class:`__Qt_Atom__` object of our new ``meta`` atom
   with any non-``ilst`` atoms ported from the old atom to the new atom.

.. classmethod:: M4AMetaData.binary_atom(key, value)

   Takes a 4 character atom name key and binary string value.
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: M4AMetaData.text_atom(key, value)

   Takes a 4 character atom name key and unicode value.
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: M4AMetaData.trkn_atom(track_number, track_total)

   Takes track number and track total integers
   (the ``trkn`` key is assumed).
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: M4AMetaData.disk_atom(disk_number, disk_total)

   Takes album number and album total integers
   (the ``disk`` key is assumed).
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: M4AMetaData.covr_atom(image_data)

   Takes a binary string of cover art data
   (the ``covr`` key is assumed).
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. class:: ILST_Atom(type, sub_atoms)

   This is initialized with a 4 character atom type string
   and a list of :class:`__Qt_Atom__`-compatible sub-atom objects
   (typically a single ``data`` atom containing the metadata field's value).
   It's less error-prone to use :class:`M4AMetaData`'s convenience
   classmethods rather than building :class:`ILST_Atom` objects by hand.

   Its :func:`__unicode__` method is particularly useful because
   it parses its sub-atoms and returns a human-readable value
   depending on whether it contains textual data or not.


Vorbis Comment
--------------

.. class:: VorbisComment(vorbis_data[, vendor_string])

   This is a VorbisComment_ tag used by FLAC, Ogg FLAC, Ogg Vorbis,
   Ogg Speex and other formats in the Ogg family.
   During initialization ``vorbis_data`` is a dictionary
   whose keys are unicode strings and whose values are lists
   of unicode strings - since each key in a Vorbis Comment may
   occur multiple times with different values.
   The optional ``vendor_string`` unicode string is typically
   handled by :func:`get_metadata` and :func:`set_metadata`
   methods, but it can also be accessed via the ``vendor_string`` attribute.
   Once initialized, :class:`VorbisComment` can be manipulated like a
   regular Python dict in addition to its standard
   :class:`audiotools.MetaData` methods.

   For example:

   >>> tag = VorbisComment({u'TITLE':[u'Track Title']})
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

   >>> tag = VorbisComment({u'TITLE':[u'Title1',u'Title2']})
   >>> tag.track_name
   u'Title1'


.. method:: VorbisComment.build()

   Returns this object's complete Vorbis Comment data as a string.

.. _APEv2: http://wiki.hydrogenaudio.org/index.php?title=APEv2

.. _ID3v1: http://www.id3.org/ID3v1

.. _FLAC: http://flac.sourceforge.net/format.html#metadata_block

.. _VorbisComment: http://www.xiph.org/vorbis/doc/v-comment.html

.. _ID3v2.2: http://www.id3.org/id3v2-00

.. _ID3v2.3: http://www.id3.org/d3v2.3.0

.. _ID3v2.4: http://www.id3.org/id3v2.4.0-structure

