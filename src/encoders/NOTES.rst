Encoder Implementation
^^^^^^^^^^^^^^^^^^^^^^

Encoding binary file formats is typically a CPU-intensive problem
that's ill-suited for pure Python.
The solution is to implement encoding in C via a new function
in the ``audiotools.encoders`` module.
We'll be using a hypothetical `foo` file format as an example.

Step 1. Add encoders/foo.c
^^^^^^^^^^^^^^^^^^^^^^^^^^

This should contain our encoding function definition:

* ``PyObject* encoders_encode_foo(PyObject *dummy, PyObject *args, PyObject *keywds)``

At this point, it's enough for the function to return ``None`` objects.

Step 2. Add function to encoders.h
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The prototype should be added, and the function should be
added to ``module_methods``.

Step 3. Add src/encoders/foo.c to setup.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Its ``.c`` source file should be added to the ``encodersmodule`` extension
so that it gets compiled properly.
At this point, we should be able to compile the ``audiotools.encoders``
module, see our new ``encode_foo`` function and call it without any
problems.

Step 4. Read the encode_foo function arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It should require a filename output string and PCMReader Python object
as our output and input, respectively.
In addition, it may take any number of encoding parameters.
If there are a nontrivial number of them, it's best to parse
them as keywords which will make the function easier to handle
at the Python level.

Step 5. Implement the encode_foo function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This function should use ``pcmr_read`` from ``pcmreader.h``
to pull ``pcm.FrameList`` objects from our PCMReader argument
and place them in an ``ia_array`` struct for encoding
to the filename via a bitstream writer.
Encoding should continue until this array is empty.

* Odds are, we'll need a specific number of PCM frames from the reader.
  In this case, one will need to wrap a PCMReader in a ``BufferedPCMReader``
  at the Python level.
* Make sure to wrap ``PyEval_SaveThread`` and ``PyEval_RestoreThread``
  around as much of the encoding process as possible.
  That is, we'll want to stop interfacing with the interpreter
  and drop to C - so avoid raising exceptions directly in sub-functions.
  It's better to have encoding functions return status results instead
  which can be transformed into an exception once
  the thread state has been restored.

Step 6. Convert encoder for standalone use
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It should be compilable via the ``-DSTANDALONE`` flag
and added to ``Makefile.sa``.
Standalone encoders *do not* have to generate finished files;
the Python interpreter may be necessary to complete a file encode.
However, such encoders should run through all the steps
that the Python encoding function would.

These encoders are for debugging purposes.
They should run through ``valgrind`` without any problems
and be profilable via ``gprof``.

Encoding is often a tricky business in which code paths
go places one wouldn't expect.
By isolating the encoding function from Python itself,
bugs are easier to find and fix.
So while it seems like extra work, it's sure to pay off sooner or later.

Step 7. Add unit tests
^^^^^^^^^^^^^^^^^^^^^^

Make sure a comprehensive set of encoding options are checked.

* test small files, even those a few samples long
* test full scale deflection, which are streams that
  alternate between highest and lowest values
* test sine streams, including a wide set of sample rates,
  channel counts, bits per sample and so on
* test wasted bits-per-sample,
  which are streams whose low bit values are all 0
* test different block sizes
* test option variations,
  which means trying *all* the different encoding options
* test noise streams under different option variations
* test fractional frames,
  which contain only a portion of a whole block

With any luck, these tests should expose any leftover bugs in the encoder.
If not, try to round-trip the encoder over one's entire lossless
audio collection.
And if *that* doesn't find any more bugs, the encoder's probably okay to use.

Step 8. Add encoder to FooAudio.from_pcm()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We'll probably need to wrap this function's pcmreader
in a ``BufferedPCMReader``.
Also, we'll have to map a compression level string
to a set of arguments to pass to ``encode_foo``.
