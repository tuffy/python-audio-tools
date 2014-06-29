:mod:`audiotools.cdio` --- the CD Input/Output Module
=====================================================

.. module:: audiotools.cdio
   :synopsis: a Module for Accessing Raw CDDA Data



The :mod:`audiotools.cdio` module contains the CDDA class
for accessing raw CDDA data.

CDDAReader Objects
------------------

.. class:: CDDAReader(device, [perform_logging])

   A :class:`audiotools.PCMReader` object which treats the CD audio
   as a single continuous stream of audio data.
   ``device`` may be a physical CD device (like ``/dev/cdrom``) or
   a CD image file (like ``CDImage.cue``).
   If ``perform_logging`` is indicated and ``device`` is a physical
   drive, reads will perform logging.

.. data:: CDDAReader.sample_rate

   The sample rate of this stream, always ``44100``.

.. data:: CDDAReader.channels

   The channel count of this stream, always ``2``.

.. data:: CDDAReader.channel_mask

   This channel mask of this stream, always ``3``.

.. data:: CDDAReader.bits_per_sample

   The bits-per-sample of this stream, always ``16``.

.. method:: CDDAReader.read(pcm_frames)

   Try to read a :class:`pcm.FrameList` object with the given number
   of PCM frames, if possible.
   This method will return sector-aligned chunks of data,
   each divisible by 588 frames.
   Once the end of the CD is reached, subsequent calls will return
   empty FrameLists.

   May raise :exc:`IOError` if a problem occurs reading the CD.

.. method:: CDDAReader.seek(pcm_frames)

   Try to seek to the given absolute position on the disc as a PCM
   frame value.
   Returns the position actually reached as a PCM frame value.
   This method will always seek to a sector-aligned position,
   each divisible by 588 frames.

.. method:: CDDAReader.close()

   Closes the stream for further reading.
   Subsequent calls to :meth:`CDDAReader.read` and
   :meth:`CDDAReader.seek` will raise :exc:`ValueError`.

.. data:: CDDAReader.is_cd_image

   Whether the disc is a physical device or CD image.
   This is useful for determining whether disc read offset
   should be applied.

.. data:: CDDAReader.first_sector

   The first sector of the disc as an integer.
   This is mostly for calculating disc IDs for various lookup services.

.. data:: CDDAReader.last_sector

   The last sector of the disc as an integer.

.. data:: CDDAReader.track_lengths

   A dict whose keys are track numbers and whose values
   are the lengths of those tracks in PCM frames.

.. data:: CDDAReader.track_offsets

   A disc whose keys are track numbers and whose values
   are the offsets of those tracks in PCM frames.

.. method:: CDDAReader.set_speed(speed)

   Sets the reading speed of the drive to the given integer.
   This has no effect on CD images.

.. method:: CDDAReader.log()

   Returns the read log as a dictionary.
   If logging is active, these values will be updated on
   each call to :meth:`CDDAReader.read`.
   If logging is inactive or not supported, all values will be 0.

.. method:: CDDAReader.reset_log()

   Resets all log values to 0.
   This is useful if one wants to get the log values for
   many tracks individually.
