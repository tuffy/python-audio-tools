:mod:`audiotools.resample` --- the Resampler Module
===================================================

.. module:: audiotools.resample
   :synopsis: a Module for Resampling PCM Data



The :mod:`audiotools.resample` module contains a resampler for
modifying the sample rate of PCM data.
This class is not usually instantiated directly;
instead, one can use :class:`audiotools.PCMConverter`
which calculates the resampling ratio and handles unprocessed
samples automatically.

Resampler Objects
-----------------

.. class:: Resampler(channels, ratio, quality)

   This class performs the actual resampling and maintains the
   resampler's state.
   ``channels`` is the number of channels in the stream being resampled.
   ``ratio`` is the new sample rate divided by the current sample rate.
   ``quality`` is an integer value between 0 and 4, where 0 is the best
   quality.

   For example, to convert a 2 channel, 88200Hz audio stream to
   44100Hz, one starts by building a resampler as follows:

   >>> resampler = Resampler(2, float(44100) / float(88200), 0)

.. method:: Resampler.process(float_frame_list, last)

   Given a :class:`FloatFrameList` object and whether this
   is the last chunk of PCM data from the stream,
   returns a pair of new :class:`FloatFrameList` objects.
   The first is the processed samples at the new rate.
   The second is a set of unprocessed samples
   which must be pushed through again on the next call to
   :meth:`process`.
