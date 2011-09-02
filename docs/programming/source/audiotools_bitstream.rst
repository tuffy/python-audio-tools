:mod:`audiotools.bitstream` --- the Bitstream Module
====================================================

.. module:: audiotools.bitstream
   :synopsis: the Bitstream Module

The :mod:`audiotools.bitstream` module contains objects for parsing
binary data.
Unlike Python's built-in struct module, these routines are specialized
to handle data that's not strictly byte-aligned.

BitstreamReader Objects
-----------------------

.. class:: BitstreamReader(file, is_little_endian[, buffer_size=4096])

   This is a file-like object for pulling individual bits or bytes
   out of a larger binary file stream.

   When operating on a raw file object
   (such as one opened with :func:`open`)
   this uses a single byte buffer.
   This allows the underlying file to be seeked safely whenever
   the :class:`BitstreamReader` is byte-aligned.
   However, when operating on a Python-based file object
   (with :func:`read` and :func:`close` methods)
   this uses an internal string up to ``buffer_size`` bytes large
   in order to minimize Python function calls.

   ``is_little_endian`` indicates which endianness format to use
   when consuming bits.

.. method:: BitstreamReader.read(bits)

   Given a number of bits to read from the stream,
   returns an unsigned integer.
   Bits must be: ``0 ≤ bits ≤ 32`` .
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.read64(bits)

   Given a number of bits to read from the stream,
   returns an unsigned long.
   Bits must be: ``0 ≤ bits ≤ 64`` .
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.read_signed(bits)

   Given a number of bits to read from the stream as a two's complement value,
   returns a signed integer.
   Bits must be: ``1 ≤ bits ≤ 32`` .
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.read_signed64(bits)

   Given a number of bits to read from the stream as a two's complement value,
   returns a signed integer.
   Bits must be: ``1 ≤ bits ≤ 64`` .
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.skip(bits)

   Skips the given number of bits in the stream as if read.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.skip_bytes(bytes)

   Skips the given number of bytes in the stream as if read.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.unary(stop_bit)

   Reads the number of bits until the next ``stop_bit``,
   which must be ``0`` or ``1``.
   Returns that count as an unsigned integer.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.limited_unary(stop_bit, maximum_bits)

   Reads the number of bits until the next ``stop_bit``,
   which must be ``0`` or ``1``, up to a maximum of ``maximum_bits``.
   Returns that count as an unsigned integer,
   or returns ``-1`` if the maximum bits are exceeded before
   ``stop_bit`` is encountered.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.byte_align()

   Discards bits as necessary to position the stream on a byte boundary.

.. method:: BitstreamReader.parse(format_string)

   Given a format string representing a set of individual reads,
   returns a list of those reads.

   ====== ================
   format method performed
   ====== ================
   "#u"   read(#)
   "#s"   read_signed(#)
   "#U"   read64(#)
   "#S"   read_signed64(#)
   "#p"   skip(#)
   "#P"   skip_bytes(#)
   "#b"   read_bytes(#)
   "a"    byte_align()
   ====== ================

   For instance:

   >>> r.parse("3u 4s 36U") == [r.read(3), r.read_signed(4), r.read64(36)]

   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.read_huffman_code(huffmantree)

   Given a :class:`HuffmanTree` object, returns the next
   Huffman code from the stream as defined in the tree.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.unread_bit(bit)

   Pushes a single bit back onto the stream, which must be ``0`` or ``1``.
   Only a single bit is guaranteed to be unreadable.

.. method:: BitstreamReader.read_bytes(bytes)

   Returns the given number of 8-bit bytes from the stream
   as a binary string.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: set_endianness(is_little_endian)

   Sets the stream's endianness where ``False`` indicates
   big-endian, while ``True`` indicates little-endian.
   The stream is automatically byte-aligned prior
   to changing its byte order.

.. method:: BitstreamReader.mark()

   Pushes the stream's current position onto a mark stack
   which may be returned to with calls to :meth:`rewind`.

.. warning::

   Placing a mark when reading from a Python-based file object requires the
   :class:`BitstreamReader` to store all the data between the marked
   position and the current position,
   since there's no guarantee such an object has a working seek method.
   Therefore, one must always :meth:`unmark` the stream
   as soon as the mark is no longer needed.

   If marks are left on the stream, :class:`BitstreamReader` will
   generate a warning at deallocation-time.

.. method:: BitstreamReader.rewind()

   Returns the stream to the most recently marked position on the mark stack.
   This has no effect on the mark stack itself.

.. method:: BitstreamReader.unmark()

   Removes the most recently marked position from the mark stack.
   This has no effect on the stream's current position.

.. method:: BitstreamReader.add_callback(callback)

   Adds a callable function to the stream's callback stack.
   ``callback(b)`` takes a single byte as an argument.
   This callback is called upon each byte read from the stream.
   If multiple callbacks are added, they are all called in reverse order.

.. method:: BitstreamReader.call_callbacks(byte)

   Calls all the callbacks on the stream's callback stack
   with the given byte, as if it had been read from the stream.

.. method:: BitstreamReader.pop_callback()

   Removes and returns the most recently added function from the callback stack.

.. method:: BitstreamReader.substream(bytes)

   Returns a new :class:`BitstreamReader` object which contains
   ``bytes`` amount of data read from the current stream
   and defined with the current stream's endianness.
   May raise an :exc:`IOError` if the current stream has
   insufficient bytes.
   Any callbacks defined in the current stream are applied
   to the bytes read for the substream when this method is called.
   Any marks or callbacks in the current stream are *not*
   transferred to the substream.
   In all other respects, the substream acts like any other
   :class:`BitstreamReader`.
   However, attempting to have the substream read beyond its
   defined byte count will trigger :exc:`IOError` exceptions.

.. method:: BitstreamReader.substream_append(substream, bytes)

   Append an additional ``bytes`` amount of data
   from the current :class:`BitstreamReader` object
   to the given :class:`BitstreamReader` substream object.
   May raise an :exc:`IOError` if the current stream has
   insufficient bytes.
   Any callbacks defined in the current stream are applied
   to the bytes read for the substream when this method is called.

.. method:: BitstreamReader.close()

   Closes the stream and any underlying file object,
   by calling its own ``close`` method.


BitstreamWriter Objects
-----------------------

.. add_callback
.. build
.. byte_align
.. call_callbacks
.. close
.. flush
.. pop_callback
.. set_endianness
.. unary
.. write
.. write64
.. flush
.. pop_callback
.. set_endianness
.. unary
.. write
.. write64
.. write_bytes
.. write_signed
.. write_signed64

BitstreamRecorder Objects
-------------------------

BitstreamAccumulator Objects
----------------------------

HuffmanTree Objects
-------------------
