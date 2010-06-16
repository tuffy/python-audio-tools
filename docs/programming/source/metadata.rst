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

   This is the container for :class:``ApeTag`` data.
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

.. .. class:: FlacMetaData

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

.. method:: build_tag()

   Returns this tag as a string.

.. classmethod:: build_id3v1(song_title, artist, album, year, comment, track_number)

   A convenience method which takes several unicode strings
   (except for ``track_number``, an integer) and returns
   a complete ID3v1 tag as a string.

.. classmethod:: read_id3v1_comment(filename)

   Takes an MP3 filename string and returns a tuple of that file's
   ID3v1 tag data, or tag data with empty fields if no ID3v1 tag is found.

.. .. class:: ID3v22Comment

.. .. class:: ID3v23Comment

.. .. class:: ID3v24Comment

.. .. class:: ID3CommentPair

M4A
---

.. class:: M4AMetaData(ilst_atoms)

   This is the metadata format used by QuickTime-compatible formats such as
   M4a and Apple Lossless.
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

.. method:: to_atom(previous_meta)

   This takes the previous M4A ``meta`` atom as a string and returns
   a new :class:`__Qt_Atom__` object of our new ``meta`` atom
   with any non-``ilst`` atoms ported from the old atom to the new atom.

.. classmethod:: binary_atom(key, value)

   Takes a 4 character atom name key and binary string value.
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: text_atom(key, value)

   Takes a 4 character atom name key and unicode value.
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: trkn_atom(track_number, track_total)

   Takes track number and track total integers
   (the ``trkn`` key is assumed).
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: disk_atom(disk_number, disk_total)

   Takes album number and album total integers
   (the ``disk`` key is assumed).
   Returns a 1 element :class:`ILST_Atom` list suitable
   for adding to our internal dictionary.

.. classmethod:: covr_atom(image_data)

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


.. method:: build()

   Returns this object's complete Vorbis Comment data as a string.

.. _APEv2: http://wiki.hydrogenaudio.org/index.php?title=APEv2

.. _ID3v1: http://www.id3.org/ID3v1

.. _VorbisComment: http://www.xiph.org/vorbis/doc/v-comment.html
