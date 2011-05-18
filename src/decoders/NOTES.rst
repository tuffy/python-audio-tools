Decoder Implementation
----------------------

Decoding binary file formats is a typically a nontrivial problem
that pure Python alone isn't fast enough to handle.
The solution is to implement decoding in C via a new
class in the ``audiotools.decoders`` module.
However, implementing these classes is a tricky business
with lots of little pieces to remember.
These notes are to ensure that a new implementation remembers
all those pieces.
We'll be using a hypothetical `foo` file format as an example.

Step 1. Add decoders/foo.h
^^^^^^^^^^^^^^^^^^^^^^^^^^

This should contain the base object struct ``decoders_FooDecoder``
(with ``PyObject_HEAD`` as its first attribute).
It should also include the ``PyGetSetDef`` and ``PyMethodDef``
arrays, function prototypes and big ``PyTypeObject decoders_FooDecoderType``
definition.

``PyGetSetDef`` functions include:

* ``static PyObject* FooDecoder_sample_rate(decoders_FooDecoder *self, void *closure)``
* ``static PyObject* FooDecoder_bits_per_sample(decoders_FooDecoder *self, void *closure)``
* ``static PyObject* FooDecoder_channels(decoders_FooDecoder *self, void *closure)``
* ``static PyObject* FooDecoder_channel_mask(decoders_FooDecoder *self, void *closure)``

While ``PyMethodDef`` functions include:

* ``static PyObject* FooDecoder_read(decoders_FooDecoder *self, PyObject *args)``
* ``static PyObject* FooDecoder_analyze_frame(decoders_FooDecoder *self, PyObject *args)``
* ``static PyObject* FooDecoder_close(decoders_FooDecoder *self, PyObject *args)``

In addition, in order to allocate/deallocate objects correctly,
one will need prototypes for:

* ``static PyObject* FooDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds)``
* ``void FooDecoder_dealloc(decoders_FooDecoder *self)``
* ``int FooDecoder_init(decoders_FooDecoder *self, PyObject *args, PyObject *kwds)``

These get attached to the ``decoders_FooDecoderType`` struct directly.

This typically looks like:
::

  PyGetSetDef FooDecoder_getseters[] = {
    {"sample_rate", (getter)FooDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)FooDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels", (getter)FooDecoder_channels, NULL, "channels", NULL},
    {"channel_mask", (getter)FooDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
  };

  PyMethodDef FooDecoder_methods[] = {
    {"read", (PyCFunction)FooDecoder_read, METH_VARARGS, ""},
    {"analyze_frame", (PyCFunction)FooDecoder_analyze_frame, METH_NOARGS, ""},
    {"close", (PyCFunction)FooDecoder_close, METH_NOARGS, ""},
    {NULL}
  };

  PyTypeObject decoders_FooDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.FooDecoder",     /*tp_name*/
    sizeof(decoders_FooDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FooDecoder_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "FooDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    FooDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    FooDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FooDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    FooDecoder_new,            /* tp_new */
  };

Step 2. Add decoders/foo.c
^^^^^^^^^^^^^^^^^^^^^^^^^^

At this point, ``FooDecoder_new`` needs to be implemented to
perform allocation and return an object,
``FooDecoder_dealloc`` needs to deallocate that object,
and ``FooDecoder_init`` needs to return 0.
All our other functions can simply return ``Py_None``.
We'll work on filling these in to work later on.

This typically looks like:
::

  PyObject*
  FooDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_FooDecoder *self;

    self = (decoders_FooDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
  }

  void
  FooDecoder_dealloc(decoders_FooDecoder *self) {
    /*additional memory deallocation here*/

    self->ob_type->tp_free((PyObject*)self);
  }

  int
  FooDecoder_init(decoders_FooDecoder *self, PyObject *args, PyObject *kwds) {
    return 0;
  }

  PyObject*
  FooDecoder_function(decoders_FooDecoder* self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
  }

Step 3. Add decoders_FooDecoderType to decoders.c
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our new type will need to be added to the extern list,
like: ``extern PyTypeObject decoders_FooDecoderType``.
In addition, we'll need to make it ready in the ``initdecoders``
function *and* incref/add the type object in that same function.

Step 4. Add src/decoders/foo.c to setup.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure its source is added to the ``decodersmodule`` extension,
so that our new decoder compiles along with the rest of it.
At this point, it should compile, show up in ``audiotools.decoders``
and we should be able to make a new ``decoders.Foo`` object
with the proper attributes and methods - even if they don't do anything yet.

Step 5. Implement our init and attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``FooDecoder_init`` should probably take a filename or something.
  It should allocate memory, read data from the file and
  error out quickly if the given file isn't correct.
* ``FooDecoder_sample_rate``, ``FooDecoder_bits_per_sample``,
  ``FooDecoder_channels`` and ``FooDecoder_channel_mask`` should
  all return integers.

Step 6. Update FooDecoder_dealloc to correspond with FooDecoder_init
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

That is, anything opened or allocated by ``FooDecoder_init`` should be
closed or deallocated by ``FooDecoder_dealloc``
prior to deallocating the object itself.
However, be sure that dealloc works with partial inits!
That is, if init fails partway through, dealloc will still be
called on the half-allocated object.
Those pieces must be freed or closed properly in that event.

Step 7. Implement FooDecoder_read
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``FooDecoder_read`` is given an integer argument (which it can safely ignore)
and returns ``pcm.FrameList`` objects.
The easiest way to construct these objects is by passing
``ia_array`` structs to the ``decoders/pcm.h`` and ``decoders/pcm.c``
static helper functions.
Actually turning input files into arrays of PCM output is left as
an exercise for the implementer.

However, there's a few vital things to note during implementation.

* Don't allocate memory outside of the ``init`` function.
  Not only will you not want to allocate/deallocate little blocks
  of memory all the time, but this is also crucial to ensuring
  that read failures are handled smoothly.
* Wrap *all* bitstream reads in ``bs_try`` / ``bs_etry`` 'exception' blocks.
  Any bitstream read can potentially fail, so you'll want to ensure
  that a failed read can ``longjmp`` back up to the error handler -
  which will likely raise an ``IOError`` exception in the read call.
  This is a big reason not to allocate memory except in the initializer,
  since jumping back to an error handler won't give one a chance
  to deallocate it beforehand.
  Instead, by "anchoring" all memory to the main class,
  ``FooDecoder_dealloc`` can take care of it all at once.
* Set the ``PyEval_SaveThread`` and ``PyEval_RestoreThread`` block
  as wide as possible over the read method.
  This allows other Python threads to operate while a read is in progress,
  which is absolutely essential for making the format usable by
  ``audiotools.player.Player`` and friends.
  Just remember that access to the Python interpreter is
  prohibited until ``PyEval_RestoreThread`` is called,
  so exceptions called by the reader will have to be handled carefully.



Step 8. Make sure the file's end case works
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some formats have an end-of-stream marker.
Some require counting down samples.
Whatever the format has, make sure the reader doesn't
trigger ``IOError`` exceptions instead of returning
empty ``pcm.FrameList`` objects once the end is reached.

Step 9. Have FooAudio.to_pcm() return our class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the decoder is decoding things properly,
have ``audiotools.FooAudio.to_pcm()`` return our class for decoding.
At this point the decoder should be ready for use!
