:mod:`audiotools.bitstream` --- the Bitstream Module
====================================================

.. module:: audiotools.bitstream
   :synopsis: the Bitstream Module

The :mod:`audiotools.bitstream` module contains objects for parsing
binary data.
Unlike Python's built-in struct module, these routines are specialized
to handle data that's not strictly byte-aligned.

.. function:: format_size(format_string)

   Given a format string as used by :meth:`BitstreamReader.parse`
   or :meth:`BitstreamWriter.build`,
   returns the size of that string as an integer number of bits
   that would be read from or written to the stream.

   >>> format_size("3u 4s 36U")
   43

.. function:: parse(format_string, is_little_endian, data)

   Given a format string as used by :meth:`BitstreamReader.parse`,
   whether the data is little-endian, and a string of binary data,
   returns a list of values as would be returned by
   :meth:`BitstreamReader.parse`.

   This is roughly equivalent to:

   >>> return BitstreamReader(StringIO(data), is_little_endian).parse(format_string)

.. function:: build(format_string, is_little_endian, values)

   Given a format string as used by :meth:`BitstreamWriter.build`,
   whether the data is little-endian, and a sequence of Python values,
   returns the binary string as would be returned by
   :meth:`BitstreamWriter.build`.

   This is roughly equivalent to

   >>> s = StringIO()
   >>> BitstreamWriter(s, is_little_endian).build(format_string, values)
   >>> return s

BitstreamReader Objects
-----------------------

This is a file-like object for pulling individual bits or bytes
out of a larger binary file stream.

.. warning::

   BitstreamReaders process the given file object in chunks
   of the given buffer size.
   This means the position of the file is likely to be further along
   than one might expect given the number of bits already read.
   The BitstreamReader's mark, rewind and seek methods
   will handle buffering correctly and are preferable
   to intermingling BitstreamReader and ``file`` operations.

.. class:: BitstreamReader(file, is_little_endian[, buffer_size=4096])

   ``file`` may be a regular file object, a file-like object
   with ``read`` and ``close`` methods, or a plain string.

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
   ``True`` for big-endian streams, ``False`` for little-endian.

.. method:: BitstreamReader.read(bits)

   Given a number of bits to read from the stream,
   returns an unsigned integer.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.read_signed(bits)

   Given a number of bits to read from the stream as a two's complement value,
   returns a signed integer.
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

.. method:: BitstreamReader.skip_unary(stop_bit)

   Skips a number of bits until the next ``stop_bit``,
   which must be ``0`` or ``1``.
   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.byte_align()

   Discards bits as necessary to position the stream on a byte boundary.

.. method:: BitstreamReader.byte_aligned()

   Returns ``True`` if the stream is positioned on a byte boundary.

.. method:: BitstreamReader.parse(format_string)

   Given a format string representing a set of individual reads,
   returns a list of those reads.

   ====== ================
   format method performed
   ====== ================
   "#u"   read(#)
   "#s"   read_signed(#)
   "#p"   skip(#)
   "#P"   skip_bytes(#)
   "#b"   read_bytes(#)
   "a"    byte_align()
   ====== ================

   For instance:

   >>> r.parse("3u 4s 36U") == [r.read(3), r.read_signed(4), r.read(36)]

   The ``*`` format multiplies the next format by the given amount.
   For example, to read 4, signed 8 bit values:

   >>> r.parse("4* 8s") == [r.read_signed(8) for i in range(4)]

   May raise :exc:`IOError` if an error occurs reading the stream.

.. method:: BitstreamReader.read_huffman_code(huffman_tree)

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

.. method:: BitstreamReader.mark([mark_id])

   Pushes the stream's current position onto a mark stack
   with the given optional mark ID.
   That position may be returned to with calls to :meth:`rewind`.

   If marks are left on the stream, :class:`BitstreamReader` will
   generate a warning at deallocation-time.

.. method:: BitstreamReader.has_mark([mark_id])

   Returns ``True`` if the given ID has been marked in the stream.

.. method:: BitstreamReader.rewind([mark_id])

   Returns the stream to the most recently marked position on the
   mark stack with the given mark ID.
   This has no effect on the mark stack itself.

.. method:: BitstreamReader.unmark([mark_id])

   Removes the most recently marked position from the mark stack
   with the given mark ID.
   This has no effect on the stream's current position.

.. method:: BitstreamReader.seek(position, [whence])

   Positions the stream at the given byte relative
   to whence, which may be 0 for the beginning of the stream
   (the default), 1 for the current position and 2 for the stream end.

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

.. method:: BitstreamReader.close()

   Closes the stream and any underlying file object,
   by calling its ``close`` method.

.. method:: BitstreamReader.__enter__()

   Returns the reader's context manager.

.. method:: BitstreamReader.__exit__(exc_type, exc_value, traceback)

   Exits the reader's context manager by calling :meth:`file.close`
   on the wrapped file object.
   If one wishes to keep the stream open for further reading,
   don't use a context manager and simply delete the reader object.
   But again, be aware that buffering may make its current position
   different than one might expect.

BitstreamWriter Objects
-----------------------

This is a file-like object for pushing individual bits or bytes
into a larger binary file stream.

.. warning::

   BitstreamWriters process the given file object in chunks
   of the given buffer size.
   This means the position of the file is likely to be not as far along
   as one might expect given the number of bits already written.
   The BitstreamWriters's mark and rewind methods
   will handle buffering correctly and are preferable
   to intermingling BitstreamWriter and ``file`` operations.

.. class:: BitstreamWriter(file, is_little_endian[, buffer_size=4096])

   When operating on a raw file object
   (such as one opened with :func:`open`)
   this uses a single byte buffer.
   This allows the underling file to be seeked safely
   whenever :class:`BitstreamWriter` is byte-aligned.
   However, when operating on a Python-based file object
   (with :func:`write` and :func:`close` methods)
   this uses an internal string up to ``buffer_size`` bytes large
   in order to minimize Python function calls.

.. method:: BitstreamWriter.write(bits, value)

   Writes the given unsigned integer value to the stream
   using the given number of bits.
   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.write_signed(bits, value)

   Writes the given signed integer value to the stream
   using the given number of bits.
   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.unary(stop_bit, value)

   If ``stop_bit`` is ``1``, writes ``value`` number of ``0``
   bits to the stream followed by a ``1`` bit.
   If ``stop_bit`` is ``0``, writes ``value`` number of ``1``
   bits to the stream followed by a ``0`` bit.
   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.write_huffman_code(huffman_tree, value)

   Given a :class:`HuffmanTree` object and an integer value to write,
   determines the proper output code and writes it to disk.
   Raises :exc:`ValueError` if the integer value is not present
   in the tree.

.. method:: BitstreamWriter.byte_align()

   Writes ``0`` bits as necessary until the stream is aligned
   on a byte boundary.
   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.byte_aligned()

   Returns ``True`` if the stream is positioned on a byte boundary.

.. method:: BitstreamWriter.build(format_string, value_list)

   Given a format string representing a set of individual writes,
   and a list of values to write,
   performs those writes to the stream.

   ====== ============= =====================
   format value         method performed
   ====== ============= =====================
   "#u"   unsigned int  write(#, u)
   "#s"   signed int    write(#, s)
   "#p"   N/A           write(#, 0)
   "#P"   N/A           write(# * 8, 0)
   "#b"   string        write_bytes(#, s)
   "a"    N/A           byte_align()
   ====== ============= =====================

   For instance:

   >>> w.build("3u 4s 36U", [1, -2, 3L])

   is equivalent to:

   >>> w.write(3,1)
   >>> w.write_signed(4, -2)
   >>> w.write(36, 3L)

   The ``*`` format multiplies the next format by the given amount.

   >>> r.build("4* 8s", [-2, -1, 0, 1])

   is equivalent to:

   >>> w.write_signed(8, -2)
   >>> w.write_signed(8, -1)
   >>> w.write_signed(8, 0)
   >>> w.write_signed(8, 1)

   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.write_bytes(string)

   Writes the given binary string to the stream
   with a number of bytes equal to its length.
   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.flush()

   Flushes cached bytes to the stream.
   Partially written bytes are *not* flushed to the stream.
   May raise :exc:`IOError` if an error occurs writing the stream.

.. method:: BitstreamWriter.set_endianness(is_little_endian)

   Sets the stream's endianness where ``False`` indicates
   big-endian, while ``True`` indicates little-endian.
   The stream is automatically byte-aligned prior
   to changing its byte order.

.. method:: BitstreamWriter.add_callback(callback)

   Adds a callable function to the stream's callback stack.
   ``callback(b)`` takes a single byte as an argument.
   This callback is called upon each byte written to the stream.
   If multiple callbacks are added, they are all called in reverse order.

.. method:: BitstreamWriter.call_callbacks(byte)

   Calls all the callbacks on the stream's callback stack
   with the given byte, as if it had been written to the stream.

.. method:: BitstreamWriter.pop_callback()

   Removes and returns the most recently added function from the callback stack.

.. method:: BitstreamWriter.mark([mark_id])

   Pushes the stream's current position onto a mark stack
   with the given optional mark ID.
   That position may be returned to with calls to :meth:`rewind`.

.. warning::

   Unlike with :class:`BitstreamReader` where marks can be placed
   anywhere, a :class:`BitstreamWriter` requires the stream
   to be byte-aligned before marks can be placed.
   Otherwise it will raise :exc:`IOError`.

.. method:: BitstreamWriter.has_mark([mark_id])

   Returns ``True`` if the given mark ID is currently in the stream.

.. method:: BitstreamWriter.rewind([mark_id])

   Returns the streams's position to the latest mark
   with the given ID.
   This has no effect on the mark stack itself.

.. warning::

   Unlike with :class:`BitstreamReader` in which a placed mark
   can be returned to anytime, a :class:`BitstreamWriter` requires
   the stream to be byte-aligned before a rewind can be performed.
   Otherwise it will raise :exc:`IOError`.

.. method:: BitstreamWriter.unmark([mark_id])

   Removes the most recently marked position from the mark stack
   with the given mark ID.
   This has no effect on the stream's current position
   and the stream is not required to be byte-aligned.

.. method:: BitstreamWriter.close()

   Flushes cached bytes to the stream and closes the underlying
   file object with its ``close`` method.

.. method:: BitstreamWriter.__enter__()

   Returns the writers's context manager.

.. method:: BitstreamWriter.__exit__(exc_type, exc_value, traceback)

   Exits the writer's context manager by calling :meth:`file.close`
   on the wrapped file object.
   If one wishes to keep the stream open for further writing,
   don't use a context manager and simply delete the writer object.
   But again, be aware that buffering may make its current position
   different than one might expect.

BitstreamRecorder Objects
-------------------------

This is a file-like object for recording the writing of individual
bits or bytes, for possible output into a :class:`BitstreamWriter`.

.. class:: BitstreamRecorder(is_little_endian)

   ``is_little_endian`` indicates whether to record a big-endian
   or little-endian output stream.

.. method:: BitstreamRecorder.write(bits, value)

   Records the given unsigned integer value to the stream
   using the given number of bits.
   Bits must be: ``0 <= bits <= 32`` .
   Value must be: ``0 <= value < (2 ** bits)`` .

.. method:: BitstreamRecorder.write64(bits, value)

   Records the given unsigned integer value to the stream
   using the given number of bits.
   Bits must be: ``0 <= bits <= 64`` .
   Value must be: ``0 <= value < (2 ** bits)`` .

.. method:: BitstreamRecorder.write_signed(bits, value)

   Records the given signed integer value to the stream
   using the given number of bits.
   Bits must be: ``0 <= bits <= 32`` .
   Value must be: ``-(2 ** (bits - 1)) <= value < 2 ** (bits - 1)`` .

.. method:: BitstreamRecorder.write_signed64(bits, value)

   Records the given signed integer value to the stream
   using the given number of bits.
   Bits must be: ``0 <= bits <= 64`` .
   Value must be: ``-(2 ** (bits - 1)) <= value < 2 ** (bits - 1)`` .

.. method:: BitstreamRecorder.unary(stop_bit, value)

   If ``stop_bit`` is ``1``, records ``value`` number of ``0``
   bits to the stream followed by a ``1`` bit.
   If ``stop_bit`` is ``0``, records ``value`` number of ``1``
   bits to the stream followed by a ``0`` bit.

.. method:: BitstreamRecorder.write_huffman_code(huffman_tree, value)

   Given a :class:`HuffmanTree` object and an integer value to write,
   determines the proper output code and records it for writing.
   Raises :exc:`ValueError` if the integer value is not present
   in the tree.

.. method:: BitstreamRecorder.byte_align()

   Records ``0`` bits as necessary until the stream is aligned
   on a byte boundary.

.. method:: BitstreamRecorder.byte_aligned()

   Returns ``True`` if the stream is positioned on a byte boundary.

.. method:: BitstreamRecorder.build(format_string, value_list)

   Given a format string representing a set of individual writes,
   and a list of values to write,
   records those writes to the stream.

   ====== ============= =====================
   format value         method performed
   ====== ============= =====================
   "#u"   unsigned int  write(#, u)
   "#s"   signed int    write(#, s)
   "#U"   unsigned long write64(#, ul)
   "#S"   signed long   write_signed64(#, sl)
   "#p"   N/A           write(#, 0)
   "#P"   N/A           write(# * 8, 0)
   "#b"   string        write_bytes(#, s)
   "a"    N/A           byte_align()
   ====== ============= =====================

   For instance:

   >>> w.build("3u 4s 36U", [1, -2, 3L])

   is equivalent to:

   >>> w.write(3,1)
   >>> w.write_signed(4, -2)
   >>> w.write64(36, 3L)

.. method:: BitstreamRecorder.write_bytes(string)

   Records the given binary string to the stream
   with a number of bytes equal to its length.

.. method:: BitstreamRecorder.set_endianness(is_little_endian)

   Sets the stream's endianness where ``False`` indicates
   big-endian, while ``True`` indicates little-endian.
   The stream is automatically byte-aligned prior
   to changing its byte order.

.. method:: BitstreamRecorder.add_callback(callback)

   Adds a callable function to the stream's callback stack.
   ``callback(b)`` takes a single byte as an argument.
   This callback is called upon each byte recorded to the stream.
   If multiple callbacks are added, they are all called in reverse order.

.. method:: BitstreamRecorder.call_callbacks(byte)

   Calls all the callbacks on the stream's callback stack
   with the given byte, as if it had been recorded to the stream.

.. method:: BitstreamRecorder.pop_callback()

   Removes and returns the most recently added function from the callback stack.

.. method:: BitstreamRecorder.close()

   Does nothing.
   This is merely a placeholder for compatibility with
   :class:`BitstreamWriter`.

.. method:: BitstreamRecorder.flush()

   Does nothing.
   This is merely a placeholder for compatibility with
   :class:`BitstreamWriter`.

.. method:: BitstreamRecorder.bits()

   Returns the count of bits recorded as an integer.

.. method:: BitstreamRecorder.bytes()

   Returns the count of bytes recorded as an integer.

.. method:: BitstreamRecorder.copy(bitstreamwriter)

   Given a :class:`BitstreamWriter`, :class:`BitstreamRecorder`
   or :class:`BitstreamAccumulator` object,
   copies all recorded output to that stream,
   including any partially written bytes.

.. method:: BitstreamRecorder.data()

   Returns a binary string of recorded data,
   not including any partially written bytes.

.. method:: BitstreamRecorder.split(target, remainder, bytes)

   Copies the given number of recorded bytes to ``target``
   and the remaining bytes to ``remainder``,
   which are :class:`BitstreamWriter`, :class:`BitstreamRecorder`,
   :class:`BitstreamAccumulator` objects, or ``None``.
   It is possible for ``target`` or ``remainder`` to be
   the same object as the recorder performing :meth:`BitstreamRecorder.split`.

.. method:: BitstreamRecorder.reset()

   Erases all recorded data and resets the stream for fresh recording.

.. method:: BitstreamRecorder.swap(bitstreamrecorder)

   Swaps the recorded data with the given :class:`BitstreamRecorder` object.
   This is often useful for finding the best output
   given many possible input permutations:

   >>> best_case = BitstreamRecorder(False)
   >>> write_data(best_case, default_arguments)
   >>> next_best = BitstreamRecorder(False)
   >>> for arguments in argument_list:
   ...     next_best.reset()
   ...     write_data(next_best, arguments)
   ...     if (next_best.bits() < best_case.bits()):
   ...         next_best.swap(best_case)
   >>> best_case.copy(output_writer)

   Unlike replacing the ``best_case`` object with ``next_best``,
   swapping and resetting allows :class:`BitstreamRecorder`
   to reuse allocated data buffers.

.. method:: BitstreamRecorder.__enter__()

   Returns the recorder's context manager.

.. method:: BitstreamRecorder.__exit__(exc_type, exc_value, traceback)

   Exits the recorders's context manager.

BitstreamAccumulator Objects
----------------------------

This is a file-like object for recording the size of writing
individual bits and bytes.
The actual writes themselves are not recorded.

.. class:: BitstreamAccumulator(is_little_endian)

   ``is_little_endian`` indicates whether to record a big-endian
   or little-endian output stream.

.. method:: BitstreamAccumulator.write(bits, value)

   Counts the given number of bits written to the stream.
   Bits must be: ``0 <= bits <= 32`` .
   Value must be: ``0 <= value < (2 ** bits)`` .

.. method:: BitstreamAccumulator.write64(bits, value)

   Counts the given number of bits written to the stream.
   Bits must be: ``0 <= bits <= 64`` .
   Value must be: ``0 <= value < (2 ** bits)`` .

.. method:: BitstreamAccumulator.write_signed(bits, value)

   Counts the given number of bits written to the stream.
   Bits must be: ``0 <= bits <= 32`` .
   Value must be: ``-(2 ** (bits - 1)) <= value < 2 ** (bits - 1)`` .

.. method:: BitstreamAccumulator.write_signed64(bits, value)

   Counts the given number of bits written to the stream.
   Bits must be: ``0 <= bits <= 64`` .
   Value must be: ``-(2 ** (bits - 1)) <= value < 2 ** (bits - 1)`` .

.. method:: BitstreamAccumulator.unary(stop_bit, value)

   Counts ``value`` number of bits, plus 1 additional stop bit.

.. method:: BitstreamWriter.write_huffman_code(huffman_tree, value)

   Given a :class:`HuffmanTree` object and an integer value to write,
   determines the proper output code and calculates its size
   when written to disk.
   Raises :exc:`ValueError` if the integer value is not present
   in the tree.

.. method:: BitstreamAccumulator.byte_align()

   Counts ``0`` bits as necessary until the stream is aligned
   on a byte boundary.

.. method:: BitstreamAccumulator.byte_aligned()

   Returns ``True`` if the stream is positioned on a byte boundary.

.. method:: BitstreamAccumulator.build(format_string, value_list)

   Given a format string representing a set of individual writes,
   and a list of values to write,
   counts the number of bits written to the stream.

   ====== ============= =====================
   format value         method performed
   ====== ============= =====================
   "#u"   unsigned int  write(#, u)
   "#s"   signed int    write(#, s)
   "#U"   unsigned long write64(#, ul)
   "#S"   signed long   write_signed64(#, sl)
   "#p"   N/A           write(#, 0)
   "#P"   N/A           write(# * 8, 0)
   "#b"   string        write_bytes(#, s)
   "a"    N/A           byte_align()
   ====== ============= =====================

   For instance:

   >>> w.build("3u 4s 36U", [1, -2, 3L])

   is equivalent to:

   >>> w.write(3,1)
   >>> w.write_signed(4, -2)
   >>> w.write64(36, 3L)

.. method:: BitstreamAccumulator.write_bytes(string)

   Counts the number of bytes in the given binary string.

.. method:: BitstreamAccumulator.set_endianness(is_little_endian)

   Sets the stream's endianness where ``False`` indicates
   big-endian, while ``True`` indicates little-endian.
   The stream is automatically byte-aligned prior
   to changing its byte order.

.. method:: BitstreamAccumulator.close()

   Does nothing.
   This is merely a placeholder for compatibility with
   :class:`BitstreamWriter`.

.. method:: BitstreamAccumulator.bits()

   Returns the counted number of bits as an integer.

.. method:: BitstreamAccumulator.bytes()

   Returns the counted number of bytes as an integer.

.. method:: BitstreamAccumulator.reset()

   Resets the counted number of bits to zero.

.. method:: BitstreamAccumulator.__enter__()

   Returns the accumulator's context manager.

.. method:: BitstreamAccumulator.__exit__(exc_type, exc_value, traceback)

   Exits the accumulator's context manager.

HuffmanTree Objects
-------------------

This is a compiled Huffman tree for use by :class:`BitstreamReader`
and :class:`BitstreamWriter`.

.. class:: HuffmanTree([bits_list, value, ...], is_little_endian)

   ``bits_list`` is a list of ``0`` or ``1`` values
   which, when read from the stream on a bit-by-bit basis,
   result in the final integer value.

   For example, given the following Huffman tree definition:

   .. image:: huffman.png

   we define our Huffman tree for a big-endian stream as follows:

   >>> HuffmanTree([(1, ),     1,
   ...              (0, 1),    2,
   ...              (0, 0, 1), 3,
   ...              (0, 0, 0), 4], False)

   Note that the bits in the tree are always consumed
   from the least-significant position to most-significant.
   This may differ from how they are consumed from the stream
   based on its ``is_little_endian`` value.

   The resulting object is passed to :meth:`BitstreamReader.read_huffman_code`
   to read the next value from a stream,
   and to :meth:`BitstreamWriter.write_huffman_code`
   to write a given value to the stream.

   May raise :exc:`ValueError` if the tree is incorrectly specified.
