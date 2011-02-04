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

.. method:: Replaygain.update(frame_list)

   Takes a :class:`pcm.FrameList` object and updates our ongoing
   ReplayGain calculation.
   Raises :exc:`ValueError` if some error occurs during calculation.

.. method:: ReplayGain.title_gain()

   Returns a pair of floats.
   The first is the calculated gain value since our last call
   to :meth:`title_gain`.
   The second is the calculated peak value since our last call
   to :meth:`title_gain`.

.. method:: ReplayGain.album_gain()

   Returns a pair of floats.
   The first is the calculated gain value of the entire stream.
   The first is the calculated peak value of the entire stream.

ReplayGainReader Objects
------------------------

.. class:: ReplayGainReader(pcmreader, gain, peak)

   This class wraps around an existing :class:`PCMReader` object.
   It takes floating point ``gain`` and ``peak`` values
   and modifies the pcmreader's output as necessary
   to match those values.
   This has the effect of raising or lowering a stream's sound volume
   to ReplayGain's reference value.
