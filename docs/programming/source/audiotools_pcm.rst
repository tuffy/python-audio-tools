:mod:`audiotools.pcm` --- the PCM FrameList Module
==================================================

.. module:: audiotools.pcm
   :synopsis: the PCM FrameList Module


The :mod:`audiotools.pcm` module contains the FrameList and FloatFrameList
classes for handling blobs of raw PCM data.

FrameList Objects
-----------------

.. class:: FrameList(string, channels, bits_per_sample, is_big_endian, is_signed)

   This class implements a PCM FrameList, which can be envisioned as a
   2D array of signed integers where
   each row represents a PCM frame of samples and
   each column represents a channel.

   During initialization, ``string`` is a collection of raw bytes,
   ``bits_per_sample`` is an integer and ``is_big_endian`` and ``is_signed``
   are booleans.
   This provides a convenient way to transforming raw data from
   file-like objects into :class:`FrameList` objects.
   Once instantiated, a :class:`FrameList` object is immutable.

.. data:: FrameList.frames

   The amount of PCM frames within this object, as a non-negative integer.

.. data:: FrameList.channels

   The amount of channels within this object, as a positive integer.

.. data:: FrameList.bits_per_sample

   The size of each sample in bits, as a positive integer.

.. method:: FrameList.frame(frame_number)

   Given a non-negative ``frame_number`` integer,
   returns the samples at the given frame as a new :class:`FrameList` object.
   This new FrameList will be a single frame long, but have the same
   number of channels and bits_per_sample as the original.
   Raises :exc:`IndexError` if one tries to get a frame number outside
   this FrameList's boundaries.

.. method:: FrameList.channel(channel_number)

   Given a non-negative ``channel_number`` integer,
   returns the samples at the given channel as a new :class:`FrameList` object.
   This new FrameList will be a single channel wide, but have the same
   number of frames and bits_per_sample as the original.
   Raises :exc:`IndexError` if one tries to get a channel number outside
   this FrameList's boundaries.

.. method:: FrameList.split(frame_count)

   Returns a pair of :class:`FrameList` objects.
   The first contains up to ``frame_count`` number of PCM frames.
   The second contains the remainder.
   If ``frame_count`` is larger than the number of frames in the FrameList,
   the first will contain all of the frames and the second will be empty.

.. method:: FrameList.copy()

   Returns a new :class:`FrameList` object as an exact copy of this one.

.. method:: FrameList.to_float()

   Converts this object's values to a new :class:`FloatFrameList` object
   by transforming all samples to the range -1.0 to 1.0.

.. method:: FrameList.frame_count(bytes)

   A convenience method which converts a given byte count to the
   maximum number of frames those bytes could contain, or a minimum of 1.

   >>> FrameList("",2,16,False,True).frame_count(8)
   2

FloatFrameList Objects
----------------------

.. class:: FloatFrameList(floats, channels)

   This class implements a FrameList of floating point samples,
   which can be envisioned as a 2D array of signed floats where
   each row represents a PCM frame of samples,
   each column represents a channel and each value is
   within the range of -1.0 to 1.0.

   During initialization, ``floats`` is a list of float values
   and ``channels`` is an integer number of channels.

.. data:: FloatFrameList.frames

   The amount of PCM frames within this object, as a non-negative integer.

.. data:: FloatFrameList.channels

   The amount of channels within this object, as a positive integer.

.. method:: FloatFrameList.frame(frame_number)

   Given a non-negative ``frame_number`` integer,
   returns the samples at the given frame as a new :class:`FloatFrameList`
   object.
   This new FloatFrameList will be a single frame long, but have the same
   number of channels and bits_per_sample as the original.
   Raises :exc:`IndexError` if one tries to get a frame number outside
   this FloatFrameList's boundaries.

.. method:: FloatFrameList.channel(channel_number)

   Given a non-negative ``channel_number`` integer,
   returns the samples at the given channel as a new :class:`FloatFrameList`
   object.
   This new FloatFrameList will be a single channel wide, but have the same
   number of frames and bits_per_sample as the original.
   Raises :exc:`IndexError` if one tries to get a channel number outside
   this FloatFrameList's boundaries.

.. method:: FloatFrameList.split(frame_count)

   Returns a pair of :class:`FloatFrameList` objects.
   The first contains up to ``frame_count`` number of PCM frames.
   The second contains the remainder.
   If ``frame_count`` is larger than the number of frames in the
   FloatFrameList, the first will contain all of the frames and the
   second will be empty.

.. method:: FloatFrameList.copy()

   Returns a new :class:`FloatFrameList` object as an exact copy of this one.

.. method:: FrameList.to_int(bits_per_sample)

   Given a ``bits_per_sample`` integer, converts this object's
   floating point values to a new :class:`FrameList` object.

