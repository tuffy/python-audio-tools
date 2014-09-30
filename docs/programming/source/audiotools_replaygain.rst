:mod:`audiotools.replaygain` --- the ReplayGain Calculation Module
==================================================================

.. module:: audiotools.replaygain
   :synopsis: a Module for Calculating and Applying ReplayGain Values

The :mod:`audiotools.replaygain` module contains the ReplayGain
class for calculating the ReplayGain gain and peak values for a set of
PCM data, and the ReplayGainReader class for applying those
gains to a :class:`audiotools.PCMReader` stream.

ReplayGain Objects
------------------

.. class:: ReplayGain(sample_rate)

   This class performs ReplayGain calculation for a stream of
   the given ``sample_rate``.
   Raises :exc:`ValueError` if the sample rate is not supported.

.. attribute:: ReplayGain.sample_rate

   The sample rate given when the object was initialized.

.. method:: ReplayGain.update(framelist)

   Given a 1 or 2 channel :class:`pcm.FrameList` object,
   updates the current gain values with its data.
   May raise :exc:`ValueError` if the framelist contains
   too many channels.

.. method:: ReplayGain.title_gain()

   Returns the gain value of the current title as a
   positive or negative floating point value.
   May raise :exc:`ValueError` if not enough samples have been
   submitted for processing.

.. method:: ReplayGain.title_peak()

   Returns the peak value of the title as a floating point value
   between 0.0 and 1.0.

.. method:: ReplayGain.album_gain()

   Returns the gain value of the entire album as a
   positive or negative floating point value.
   May raise :exc:`ValueError` if not enough samples have been
   submitted for processing.

.. method:: ReplayGain.album_peak()

   Returns the peak value of the entire album as a floating point value
   between 0.0 and 1.0.

.. method:: ReplayGain.next_title()

   Indicates the current track is finished and resets the stream
   to process the next track.
   This method should be called after :meth:`ReplayGain.title_gain`
   and :meth:`ReplayGain.title_peak` have been used to
   extract the title's gain values, but before data has
   been submitted for the next title or :meth:`ReplayGain.album_gain`
   :meth:`ReplayGain.album_peak` have been called to get
   the entire album's gain values.

ReplayGainReader Objects
------------------------

.. class:: ReplayGainReader(pcmreader, gain, peak)

   This class wraps around an existing :class:`PCMReader` object.
   It takes floating point ``gain`` and ``peak`` values
   and modifies the pcmreader's output as necessary
   to match those values.
   This has the effect of raising or lowering a stream's sound volume
   to ReplayGain's reference value.
