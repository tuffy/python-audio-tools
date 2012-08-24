:mod:`audiotools.cue` --- the Cuesheet Parsing Module
=====================================================

.. module:: audiotools.cue
   :synopsis: a Module for Parsing and Building CD Cuesheet Files.



The :mod:`audiotools.cue` module contains the Cuesheet class
used for parsing and building cuesheet files representing CD images.

.. function:: read_cuesheet(filename)

   Takes a filename string and returns a new :class:`Cuesheet` object.
   Raises :exc:`CueException` if some error occurs when reading
   the file.

.. exception:: CueException

   A subclass of :exc:`audiotools.SheetException` raised
   when some parsing or reading error occurs when reading a cuesheet file.

Cuesheet Objects
----------------

.. class:: Cuesheet()

   This class is used to represent a .cue file.
   It is not meant to be instantiated directly but returned from
   the :func:`read_cuesheet` function.
   The :meth:`__str__` value of a Cuesheet corresponds
   to a formatted file on disk.

.. method:: Cuesheet.catalog()

   Returns the cuesheet's catalog number as a plain string,
   or ``None`` if the cuesheet contains no catalog number.

.. method:: Cuesheet.single_file_type()

   Returns ``True`` if the cuesheet is formatted for a single input file.
   Returns ``False`` if the cuesheet is formatted for several
   individual tracks.

.. method:: Cuesheet.indexes()

   Returns an iterator of index lists.
   Each index is a tuple of CD sectors corresponding to a
   track's offset on disk.

.. method:: Cuesheet.pcm_lengths(total_length, sample_rate)

   Takes the total length of the entire CD, in PCM frames,
   and the sample rate of the stream, in Hz.
   Returns a list of PCM frame lengths for all audio tracks within
   the cuesheet.
   This list of lengths can be used to split a single CD image
   file into several individual tracks.

.. method:: Cuesheet.ISRCs()

   Returns a dictionary of track_number -> ISRC values
   for all tracks whose ISRC value is not empty.

.. classmethod:: Cuesheet.file(sheet, filename)

   Takes a :class:`Cuesheet`-compatible object with
   :meth:`catalog`, :meth:`indexes`, :meth:`ISRCs` methods
   along with a filename string.
   Returns a new :class:`Cuesheet` object.
   This is used to convert other sort of Cuesheet-like objects
   into actual Cuesheets.
