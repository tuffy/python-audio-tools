:mod:`audiotools.toc` --- the TOC File Parsing Module
=====================================================

.. module:: audiotools.toc
   :synopsis: a Module for Parsing and Building CD TOC Files.



The :mod:`audiotools.toc` module contains the TOCFile class
used for parsing and building TOC files representing CD images.

.. function:: read_tocfile(filename)

   Takes a filename string and returns a new :class:`TOCFile` object.
   Raises :exc:`TOCException` if some error occurs when reading
   the file.

.. exception:: TOCException

   A subclass of :exc:`audiotools.SheetException` raised
   when some parsing or reading error occurs when reading a TOC file.

TOCFile Objects
----------------

.. class:: TOCFile()

   This class is used to represent a .toc file.
   It is not meant to be instantiated directly but returned from
   the :func:`read_tocfile` function.

.. method:: TOCFile.catalog()

   Returns the TOC file's catalog number as a plain string,
   or ``None`` if the TOC file contains no catalog number.

.. method:: TOCFile.indexes()

   Returns an iterator of index lists.
   Each index is a tuple of CD sectors corresponding to a
   track's offset on disk.

.. method:: TOCFile.pcm_lengths(total_length)

   Takes the total length of the entire CD in PCM frames.
   Returns a list of PCM frame lengths for all audio tracks within
   the TOC file.
   This list of lengths can be used to split a single CD image
   file into several individual tracks.

.. method:: TOCFile.ISRCs()

   Returns a dictionary of track_number -> ISRC values
   for all tracks whose ISRC value is not empty.

.. classmethod:: TOCFile.file(sheet, filename)

   Takes a :class:`cue.Cuesheet`-compatible object with
   :meth:`catalog`, :meth:`indexes`, :meth:`ISRCs` methods
   along with a filename string.
   Returns a new :class:`TOCFile` object.
   This is used to convert other sort of Cuesheet-like objects
   into actual TOC files.
