..
  Audio Tools, a module and set of tools for manipulating audio data
  Copyright (C) 2007-2015  Brian Langenberger

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

:mod:`audiotools.pcmconverter` --- the PCM Conversion Module
============================================================

.. module:: audiotools.pcmconverter
   :synopsis: a Module for Converting PCM Streams


The :mod:`audiotools.pcmconverter` module contains
:class:`audiotools.PCMReader` wrapper classes
for converting streams to different sample rates,
channel counts, channel assignments and so on.

These classes are combined by :class:`audiotools.PCMConverter`
as needed to modify a stream from one format to another.


Averager Objects
----------------

.. class:: Averager(pcmreader)

   This class takes a :class:`audiotools.PCMReader`-compatible
   object and constructs a new :class:`audiotools.PCMReader`-compatible
   whose channels have been averaged together into a single channel.

.. data:: Averager.sample_rate

   The sample rate of this audio stream, in Hz, as a positive integer.

.. data:: Averager.channels

   The number of channels of this audio stream, which is always 1.

.. data:: Averager.channel_mask

   The channel mask of this audio stream, which is always ``0x4``.

.. data:: Averager.bits_per_sample

   The number of bits-per-sample in this audio stream as a positive integer.

.. method:: Averager.read(pcm_frames)

   Try to read a :class:`audiotools.pcm.FrameList` object with the given
   number of PCM frames, if possible.
   This method is *not* guaranteed to read that amount of frames.
   It may return less, particularly at the end of an audio stream.
   It may even return FrameLists larger than requested.
   However, it must always return a non-empty FrameList until the
   end of the PCM stream is reached.
   May raise :exc:`IOError` if there is a problem reading the
   source file, or :exc:`ValueError` if the source file has
   some sort of error.

.. method:: Averager.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.
   May raise a :exc:`DecodingError`, typically indicating that
   a helper subprocess used for decoding has exited with an error.

BPSConverter Objects
--------------------

.. class:: BPSConveter(pcmreader, bits_per_sample)

   This class takes a :class:`audiotools.PCMReader`-compatible
   object and new ``bits_per_sample`` integer,
   and constructs a new :class:`audiotools.PCMReader`-compatible
   object with that amount of bits-per-sample
   by truncating or extending bits to each sample as needed.

.. data:: BPSConverter.sample_rate

   The sample rate of this audio stream, in Hz, as a positive integer.

.. data:: BPSConverter.channels

   The number of channels in this audio stream as a positive integer.

.. data:: BPSConverter.channel_mask

   The channel mask of this audio stream as a non-negative integer.

.. data:: BPSConverter.bits_per_sample

   The number of bits-per-sample in this audio stream as
   indicated at init-time.

.. method:: BPSConverter.read(pcm_frames)

   Try to read a :class:`audiotools.pcm.FrameList` object with the given
   number of PCM frames, if possible.
   This method is *not* guaranteed to read that amount of frames.
   It may return less, particularly at the end of an audio stream.
   It may even return FrameLists larger than requested.
   However, it must always return a non-empty FrameList until the
   end of the PCM stream is reached.
   May raise :exc:`IOError` if there is a problem reading the
   source file, or :exc:`ValueError` if the source file has
   some sort of error.

.. method:: BPSConverter.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.
   May raise a :exc:`DecodingError`, typically indicating that
   a helper subprocess used for decoding has exited with an error.

Downmixer Objects
-----------------

.. class:: Downmixer(pcmreader)

   This class takes a :class:`audiotools.PCMReader`-compatible
   object, presumably with more than two channels, and
   constructs a :class:`audiotools.PCMReader`-compatible object
   with only two channels mixed in Dolby Pro Logic format
   such that a rear channel can be restored.

   If the stream has fewer than 5.1 channels, those channels
   are padded with silence.
   Additional channels beyond 5.1 are ignored.

.. data:: Downmixer.sample_rate

   The sample rate of this audio stream, in Hz, as a positive integer.

.. data:: Downmixer.channels

   The number of channels in this audio stream, which is always 2.

.. data:: Downmixer.channel_mask

   The channel mask of this audio stream, which is always ``0x3``.

.. data:: Downmixer.bits_per_sample

   The number of bits-per-sample in this audio stream as a positive integer.

.. method:: Downmixer.read(pcm_frames)

   Try to read a :class:`audiotools.pcm.FrameList` object with the given
   number of PCM frames, if possible.
   This method is *not* guaranteed to read that amount of frames.
   It may return less, particularly at the end of an audio stream.
   It may even return FrameLists larger than requested.
   However, it must always return a non-empty FrameList until the
   end of the PCM stream is reached.
   May raise :exc:`IOError` if there is a problem reading the
   source file, or :exc:`ValueError` if the source file has
   some sort of error.

.. method:: Downmixer.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.
   May raise a :exc:`DecodingError`, typically indicating that
   a helper subprocess used for decoding has exited with an error.

Resampler Objects
-----------------

.. class:: Resampler(pcmreader, sample_rate)

   This class takes a :class:`audiotools.PCMReader`-compatible object
   and new ``sample_rate`` integer, and constructs a new
   :class:`audiotools.PCMReader`-compatible object with that sample rate.

.. data:: Resampler.sample_rate

   The sample rate of this audio stream, in Hz,
   as given at init-time.

.. data:: Resampler.channels

   The number of channels in this audio stream as a positive integer.

.. data:: Resampler.channel_mask

   The channel mask of this audio stream as a non-negative integer.

.. data:: Resampler.bits_per_sample

   The number of bits-per-sample in this audio stream as a positive integer.

.. method:: Resampler.read(pcm_frames)

   Try to read a :class:`audiotools.pcm.FrameList` object with the given
   number of PCM frames, if possible.
   This method is *not* guaranteed to read that amount of frames.
   It may return less, particularly at the end of an audio stream.
   It may even return FrameLists larger than requested.
   However, it must always return a non-empty FrameList until the
   end of the PCM stream is reached.
   May raise :exc:`IOError` if there is a problem reading the
   source file, or :exc:`ValueError` if the source file has
   some sort of error.

.. method:: Resampler.close()

   Closes the audio stream.
   If any subprocesses were used for audio decoding, they will also be
   closed and waited for their process to finish.
   May raise a :exc:`DecodingError`, typically indicating that
   a helper subprocess used for decoding has exited with an error.
