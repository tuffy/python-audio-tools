:mod:`audiotools.cdio` --- the CD Input/Output Module
=====================================================

.. module:: audiotools.cdio
   :synopsis: a Module for Accessing Raw CDDA Data



The :mod:`audiotools.cdio` module contains the CDDA class
for accessing raw CDDA data.
One does not typically use this module directly.
Instead, the :class:`audiotools.CDDA` class provides encapsulation
to hide many of these low-level details.

CDDA Objects
------------

.. class:: CDDA(device)

   This class is used to access a specific CD-ROM device,
   which should be given as a string such as ``"/dev/cdrom"``
   during instantiation.

   Note that audio CDs are accessed by sectors, each 1/75th of a
   second long - or 588 PCM frames.
   Thus, many of this object's methods take and return sector
   integer values.

.. method:: CDDA.total_tracks()

   Returns the total number of tracks on the CD as an integer.

   >>> cd = CDDA("/dev/cdrom")
   >>> cd.total_tracks()
   17

.. method:: CDDA.track_offsets(track_number)

   Given a track_number integer (starting from 1),
   returns a pair of sector values.
   The first is the track's first sector on the CD.
   The second is the track's last sector on the CD.

   >>> cd.track_offsets(1)
   (0, 15774)
   >>> cd.track_offsets(2)
   (15775, 31836)

.. method:: CDDA.first_sector()

   Returns the first sector of the entire CD as an integer, typically 0.

   >>> cd.first_sector()
   0

.. method:: CDDA.last_sector()

   Returns the last sector of the entire CD as an integer.

   >>> cd.last_sector()
   240449

.. method:: CDDA.length_in_seconds()

   Returns the length of the entire CD in seconds as an integer.

   >>> cd.length_in_seconds()
   3206

.. method:: CDDA.track_type(track_number)

   Given a track_number integer (starting from 1),
   returns the type of track it is as an integer.

.. method:: CDDA.set_speed(speed)

   Sets the CD-ROM's reading speed to the new integer value.

.. method:: CDDA.seek(sector)

   Sets our current position on the CD to the given sector.
   For example, to begin reading audio data from the second track:

   >>> cd.track_offsets(2)[0]
   15775
   >>> cd.seek(15775)

.. method:: CDDA.read_sector()

   Reads a single sector from the CD as a :class:`pcm.FrameList` object
   and moves our current read position ahead by 1.

   >>> f = cd.read_sector()
   >>> f
   <pcm.FrameList object at 0x2ca16f0>
   >>> len(f)
   1176

.. method:: CDDA.read_sectors(sectors)

   Given a number of sectors, reads as many as possible
   from the CD as a :class:`pcm.FrameList` object
   and moves our current read position ahead by that many sectors.

   >>> f = cd.read_sectors(10)
   >>> f
   <pcm.FrameList object at 0x7f022e0d6c60>
   >>> len(f)
   11760

.. function:: set_read_callback(function)

   Sets a global callback function which takes two integer values
   as arguments.
   The second argument is a cdparanoia value corresponding
   to errors fixed, if any:

   ===== ========================== ======================
   Value CDParanoia Value           Meaning
   ----- -------------------------- ----------------------
       0 PARANOIA_CB_READ           Read off adjust ???
       1 PARANOIA_CB_VERIFY         Verifying jitter
       2 PARANOIA_CB_FIXUP_EDGE     Fixed edge jitter
       3 PARANOIA_CB_FIXUP_ATOM     Fixed atom jitter
       4 PARANOIA_CB_SCRATCH        Unsupported
       5 PARANOIA_CB_REPAIR         Unsupported
       6 PARANOIA_CB_SKIP           Skip exhausted retry
       7 PARANOIA_CB_DRIFT          Skip exhausted retry
       8 PARANOIA_CB_BACKOFF        Unsupported
       9 PARANOIA_CB_OVERLAP        Dynamic overlap adjust
      10 PARANOIA_CB_FIXUP_DROPPED  Fixed dropped bytes
      11 PARANOIA_CB_FIXUP_DUPED    Fixed duplicate bytes
      12 PARANOIA_CB_READERR        Hard read error
   ===== ========================== ======================
