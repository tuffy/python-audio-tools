:mod:`audiotools.ui` --- Reusable Python Audio Tools GUI Widgets
================================================================

This module contains a collection of reusable Urwid widgets
and helper functions for processing user input
and generating helper output in a consistent way.

.. function:: show_available_formats(messenger)

   Given a :class:`audiotools.Messenger` object,
   displays all the available file formats
   one can select with a utility's ``-t`` argument
   in a user-friendly way.

.. function:: show_available_qualities(messenger, audio_type)

   Given a :class:`audiotools.Messenger` object
   and an :class:`audiotools.AudioFile` subclass,
   displays all the available output qualities
   for that audio type one can select with a utility's ``-q`` argument.

.. function:: select_metadata(metadata_choices, messenger, [use_default])

   Given ``metadata_choices[choice][track]`` where each choice
   contains a list of :class:`audiotools.MetaData` objects
   and all choices must have the same number of objects,
   along with a :class:`audiotools.Messenger` object,
   queries the user for which metadata choice to use
   and returns that list of :class:`audiotools.MetaData` objects.

   If ``use_default`` is ``True``, this simply returns the metadata
   for the first choice.

.. function:: process_output_options(metadata_choices, input_filenames, output_directory, format_string, output_class, quality, messenger, [use_default])

   This function is for processing the input and output options
   for utilities such as ``track2track`` and ``cd2track``.

   ``metadata_choices[choice][track]`` is a list of
   :class:`audiotools.MetaData` objects
   and all choices must have the same number of objects.

   ``input_filenames`` is a list of :class:`audiotools.Filename` objects
   where the number of filenames must match the number of
   :class:`audiotools.MetaData` objects for each choice
   in ``metadata_choices``.

   ``output_directory`` is a string to the output directory,
   indicated by a utility's ``-d`` option.

   ``format_string`` is a UTF-8 encoded plain string of the
   output file format, indicated by a utility's ``--format`` option.

   ``output_class`` is an :class:`audiotools.AudioFile` class,
   indicated by a utility's ``-t`` option.

   ``quality`` is a string if the output quality to use,
   indicated by a utility's ``-q`` option.

   ``messenger`` is an :class:`audiotools.Messenger` object
   used for displaying output.

   ``use_default``, if indicated, is applied to this function's call to
   :func:`select_metadata` if necessary.

   Yields a ``(output_class, output_filename, output_quality, output_metadata)``
   tuple for each output file where ``output_class`` is an
   :class:`audiotools.AudioFile` object,
   ``output_filename`` is a :class:`audiotools.Filename` object,
   ``output_quality`` is a compression string,
   and ``output_metadata`` is a :class:`audiotools.MetaData` object.

   Raises :exc:`audiotools.UnsupportedTracknameField` or
   :exc:`audiotools.InvalidFilenameFormat` if the ``format_string``
   option is invalid.

   Raises :exc:`audiotools.DuplicateOutputFile` if the
   same output filename is generated more than once.

   Raises :exc:`audiotools.OutputFileIsInput` if
   one of the output files is the same as any of the input files.

.. function:: not_available_message(messenger)

   Given a :class:`audiotools.Messenger` object,
   displays a message about Urwid being unavailable
   and offers a suggestion on how to obtain it.

.. function:: xargs_suggestion(args)

   Given a list of argument strings (such as from ``sys.argv``)
   returns a Unicode string indicating how one might
   call the given program using ``xargs``.

PlayerTTY Objects
-----------------

.. class:: PlayerTTY(player)

   This is a base class for implementing the user interface
   for TTY-based audio players.

   ``player`` is a :class:`audiotools.player.Player`-compatible
   object.

.. method:: PlayerTTY.next_track()

   Stop playing the current track and begin playing the next one.
   This must be implemented in a subclass.

.. method:: PlayerTTY.previous_track()

   Stop playing the current track and begin playing the previous one.
   This must be implemented in a subclass.

.. method:: PlayerTTY.set_metadata(track_number, track_total, channels, sample_rate, bits_per_sample)

   Typically called by :meth:`PlayerTTY.next_track` and
   :meth:`PlayerTTY.previous_track`, this sets the current metadata
   to the given values for displaying to the user.

.. method:: PlayerTTY.toggle_play_pause()

   Calls :meth:`audiotools.player.Player.toggle_play_pause`
   on the internal :class:`audiotools.player.Player` object
   to suspend or resume output.

.. method:: PlayerTTY.stop()

   Calls :meth:`audiotools.player.Player.stop`
   on the internal :class:`audiotools.player.Player` object
   to stop playing the current file completely.

.. method:: PlayerTTY.progress()

   Returns the values from :meth:`audiotools.player.Player.progress`
   which indicate the current status of the playing file.

.. method:: PlayerTTY.progress_line(frames_sent, frames_total)

   Given the amount of PCM frames sent and total number of PCM frames
   as integers, returns a Unicode string of the current progress
   to be displayed to the user.

.. method:: PlayerTTY.run(messenger, stdin)

   Given a :class:`audiotools.Messenger` object
   and ``sys.stdin`` file object,
   this runs the player's output loop
   until the user indicates it should exit or the input is exhausted.

   Returns 0 on a successful exit, 1 if it exits with an error.

.. data:: AVAILABLE

   ``True`` if Urwid is available and is of a sufficiently high version.
   ``False`` if not.

Urwid Widgets
-------------

If Urwid is available, the following classes will be in this
module for use by utilities to generate interactive modes.
If not, the classes will not be defined.

OutputFiller Objects
^^^^^^^^^^^^^^^^^^^^

.. class:: OutputFiller(track_labels, metadata_choices, input_filenames, output_directory, format_string, output_class, quality, [completion_label])

   This is an Urwid Frame subclass for populating track data
   and options for multiple output file utilities such
   as ``track2track`` and ``cd2track``.

   ``track_labels`` is a list of Unicode strings, one per track

   ``metadata_choices[choice][track]`` is a list of
   :class:`audiotools.MetaData` objects per choice, one per track

   ``input_filenames`` is a list of :class:`audiotools.Filename` objects,
   one per track.

   ``output_directory`` is a string to the output directory,
   indicated by a utility's ``-d`` option.

   ``format_string`` is a UTF-8 encoded plain string of the
   output file format, indicated by a utility's ``--format`` option.

   ``output_class`` is an :class:`audiotools.AudioFile` class,
   indicated by a utility's ``-t`` option.

   ``quality`` is a string if the output quality to use,
   indicated by a utility's ``-q`` option.

   ``completion_label`` is an optional Unicode string
   to display in the widget's "apply" button
   used to complete the operation.

   This widget is typically executed as follows:

   >>> widget = audiotools.ui.OutputFiller(...)  # populate widget with metadata and command-line options
   >>> loop = urwid.MainLoop(widget,
   ...                       audiotools.ui.style(),
   ...                       unhandled_input=widget.handle_text,
   ...                       pop_ups=True)
   >>> loop.run()
   >>> if (not widget.cancelled()):
   ...     # do work here
   ... else:
   ...     # exit

.. method:: OutputFiller.output_tracks()

   Yields a ``(output_class, output_filename, output_quality, output_metadata)``
   tuple for each output file where ``output_class`` is an
   :class:`audiotools.AudioFile` object,
   ``output_filename`` is a :class:`audiotools.Filename` object,
   ``output_quality`` is a compression string,
   and ``output_metadata`` is a :class:`audiotools.MetaData` object.

.. note::

   This method returns freshly-created :class:`audiotools.MetaData` objects,
   whereas :func:`process_output_options` resuses the same objects
   passed to it.

   Because :class:`OutputFiller` may modify input metadata,
   we don't want to risk modifying objects used elsewhere.

.. method:: OutputFiller.output_directory()

   Returns the currently selected output directory as a plain string.

.. method:: OutputFiller.format_string()

   Returns the current format string as a plain, UTF-8 encoded string.

.. method:: OutputFiller.output_class()

   Returns the current :class:`audiotools.AudioFile`-compatible
   output class.

.. method:: OutputFiller.quality()

   Returns the current output quality as a plain string.

SingleOutputFiller Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: SingleOutputFiller(track_label, metadata_choices, input_filenames, output_file, output_class, quality, [completion_label])

   This is an Urwid Frame subclass for populating track data
   and options for a single output track utilities such as ``trackcat``.

   ``track_label`` is a Unicode string.

   ``metadata_choices[choice]`` is a list of :class:`audiotools.MetaData`
   objects for all possible choices for the given track.

   ``input_filenames`` is a list or set of :class:`audiotools.Filename`
   objects for all input files, which may include cuesheets
   or other auxiliary data.

   ``output_file`` is a plain string of the default output filename.

   ``output_class`` is an :class:`audiotools.AudioFile` class,
   indicated by a utility's ``-t`` option.

   ``quality`` is a string if the output quality to use,
   indicated by a utility's ``-q`` option.

   ``completion_label`` is an optional Unicode string
   to display in the widget's "apply" button
   used to complete the operation.

   This widget is typically executed as follows:

   >>> widget = audiotools.ui.SingleOutputFiller(...)  # populate widget with metadata and command-line options
   >>> loop = urwid.MainLoop(widget,
   ...                       audiotools.ui.style(),
   ...                       unhandled_input=widget.handle_text,
   ...                       pop_ups=True)
   >>> loop.run()
   >>> if (not widget.cancelled()):
   ...     # do work here
   ... else:
   ...     # exit

.. method:: SingleOutputFiller.output_track()

   Returns ``(output_class, output_filename, output_quality, output_metadata)``
   tuple to apply to the single output track.
   ``output_class`` is an :class:`audiotools.AudioFile` object,
   ``output_filename`` is a :class:`audiotools.Filename` object,
   ``output_quality`` is a compression string,
   and ``output_metadata`` is a :class:`audiotools.MetaData` object.

MetaDataFiller Objects
^^^^^^^^^^^^^^^^^^^^^^

.. class:: MetaDataFiller(track_labels, metadata_choices, status)

   This is an Urwid Pile subclass for selecting and editing
   a single set of metadata from multiple choices.
   It is used by :class:`OutputFiller` and :class:`SingleOutputFiller`
   as necessary to allow the user to edit metadata
   when setting options.

   ``track_labels`` is a list of Unicode strings, one per track.

   ``metadata_choices[choice][track]`` is a list of
   :class:`audiotools.MetaData` objects per choice, one per track

   ``status`` is an :class:`urwid.Text` object
   to display status text such as key shortcuts.

.. method:: MetaDataFiller.select_previous_item()

   Selects the previous item in the current set of metadata,
   such as the previous track or the previous field,
   depending on how the data is swiveled.

.. method:: MetaDataFiller.select_next_item()

   Selects the next item in the current set of metadata,
   such as the next track or the next field,
   depending on how the data is swiveled.

.. method:: MetaDataFiller.populated_metadata()

   Yields a new, populated :class:`audiotools.MetaData` object
   per track, depending on the current selection and its values.

MetaDataEditor Objects
^^^^^^^^^^^^^^^^^^^^^^

.. class:: MetaDataEditor(tracks, [on_text_change], [on_swivel_change])

   This is an Urwid Frame subclass for editing a single set of metadata
   across multiple tracks.

   ``tracks`` is a list of ``(id, label, metadata)`` tuples
   in the order they are to be displayed
   with ``id`` is some unique, hashable ID value,
   ``label`` is a Unicode string,
   and ``metadata`` is an :class:`audiotools.MetaData` object, or ``None``.

   ``on_text_change(widget, new_value)``
   is a callback for when any text field is modified.

   ``on_swivel_change(widget, selected, swivel)``
   is a callback for when tracks and fields are swapped.

.. method:: MetaDataEditor.select_previous_item()

   Selects the previous item in the current set of metadata,
   such as the previous track or the previous field,
   depending on how the data is swiveled.

.. method:: MetaDataEditor.select_next_item()

   Selects the next item in the current set of metadata,
   such as the next track or the next field,
   depending on how the data is swiveled.

.. method:: MetaDataEditor.metadata()

   Yields a ``(track_id, metadata)`` tuple per edited track
   where ``track_id`` is the unique, hashable value
   entered at init-time, and ``metadata`` is a newly created
   :class:`audiotools.MetaData` object.

BottomLineBox Objects
^^^^^^^^^^^^^^^^^^^^^

.. class:: BottomLineBox(original_widget, [title], [tlcorner], [tline], [lline], [trcorner], [blcorner], [rline], [bline], [bcorner])

   This is an Urwid LineBox subclass which places its title
   at the bottom instead of the top.

SelectOne Objects
^^^^^^^^^^^^^^^^^

.. class:: SelectOne(items, [selected_value], [on_change], [user_data], [label])

   This is an Urwid PopUpLauncher subclass designed to work
   as an HTML-style <SELECT> dropdown.

   ``items`` is a list of ``(label, value)`` tuples
   where ``label`` is a Unicode string and ``value``
   is any object with an ``__eq__`` method.

   ``selected_value`` indicates which object in items
   is currently selected.

   ``on_change(new_value, [user_data])`` is a callback
   which is called whenever the selected item is changed
   where ``new_value`` is the value from the ``item`` tuple.

   ``user_data`` is an object passed to the ``on_change`` callback.

   ``label`` is a Unicode label string for the selection box.

.. method:: SelectOne.make_selection(label, value)

   Given a Unicode ``label`` and ``value`` object,
   sets the selection to the given values.

.. method:: SelectOne.selection()

   Returns the selected ``value`` object.

.. method:: SelectOne.set_items(items, selected_value)

   Replaces all the items in the dropdown with new values.
   ``items`` is a list of ``(label, value)`` tuples
   where ``label`` is a Unicode string and ``value``
   is any object with an ``__eq__`` method.

   ``selected_value`` indicates which object in items
   is currently selected.

SelectDirectory Objects
^^^^^^^^^^^^^^^^^^^^^^^

.. class:: SelectDirectory(initial_directory, [on_change], [user_data])

   This is an Urwid Columns subclass consisting of an
   editable output directory box and a directory tree
   browser button.

   ``initial_directory`` is a plain string of the starting directory.

   ``on_change(widget, new_directory, user_data)`` is a callback
   which is called whenever the directory is changed.

   ``user_data`` is passed to the ``on_change`` callback.

.. method:: SelectDirectory.get_directory()

   Returns the currently selected directory as a plain string.

EditFilename Objects
^^^^^^^^^^^^^^^^^^^^

.. class:: EditFilename(initial_filename)

   This is an Urwid Edit subclass for editing a single output filename.

   ``initial_filename`` is a plain string of the starting filename.

.. method:: EditFilename.get_filename()

   Returns the edited filename as a plain string.

.. method:: EditFilename.set_filename(filename)

   Updates the field's value to the given filename,
   which is a plain string.

OutputOptions Objects
^^^^^^^^^^^^^^^^^^^^^

.. class:: OutputOptions(output_directory, format_string, audio_class, quality, input_filenames, metadatas, [extra_widgets])

   This is an Urwid Pile subclass for populating output options,
   including an output file previewer so one can see the results
   of changing the directory and format string in real-time.

   ``output_directory`` is a string to the output directory,
   indicated by a utility's ``-d`` option.

   ``format_string`` is a UTF-8 encoded plain string of the
   output file format, indicated by a utility's ``--format`` option.

   ``output_class`` is an :class:`audiotools.AudioFile` class,
   indicated by a utility's ``-t`` option.

   ``quality`` is a string if the output quality to use,
   indicated by a utility's ``-q`` option.

   ``input_filenames`` is a list of :class:`audiotools.Filename` objects,
   one per input track.

   ``metadatas`` is a list of :class:`audiotools.Metadata` objects,
   oner per input track.

   ``extra_widgets`` is a list of additional Urwid widgets
   to append to the pile.

.. method:: OutputOptions.set_metadatas(metadatas)

   ``metadatas`` is a list of :class:`audiotools.MetaData` objects
   (which may be ``None``), one per input track.

.. method:: OutputOptions.selected_options()

   Returns ``(output_class, output_quality, [output filenames])``
   tuple where ``output_class`` is an :class:`audiotools.AudioFile`,
   ``output_quality`` is a plain string
   and ``output_filenames`` is a list of :class:`audiotools.Filename`
   objects, one per input filename.

SingleOutputOptions Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: SingleOutputOptions(output_filename, audio_class, quality)

   This is an Urwid ListBox subclass for populating the options
   of a single output audio file.

   ``output_filename`` is a plain string of the default
   output filename.

   ``audio_class`` is an :class:`audiotools.AudioFile` object.

   ``quality`` is a plain string of the default output quality.

.. method:: SingleOutputOptions.selected_options()

   Returns ``(output_class, output_quality, output filename)``
   where ``output_class`` is an :class:`audiotools.AudioFile`,
   ``output_quality`` is a plain string
   and ``output_filename`` is a :class:`audiotools.Filename` object.

PlayerGUI Objects
^^^^^^^^^^^^^^^^^

.. class:: PlayerGUI(player, tracks, total_length)

   This is an Urwid Frame subclass for implementing
   an interactive audio player.
   It cannot be instantiated directly;
   a subclass must implement its ``select_track`` method
   to determine what to play next.

   ``player`` is a :class:`audiotools.player.Player`-compatible
   object.

   ``tracks`` is a list of ``(track_name, seconds_length, user_data)``
   tuples where ``track_name`` is a Unicode string,
   ``seconds_length`` is the length of the track in seconds
   and ``user_data`` is some Python object.

   ``total_length`` is the length of all tracks in seconds.

   This widget is typically used as follows:

   >>> player = PlayerGUISubclass(...)        # instantiate PlayerGUI subclass widget with input
   >>> loop = urwid.MainLoop(widget,          # setup MainLoop to execute widget
   ...                       audiotools.ui.style(),
   ...                       unhandled_input=player.handle_text)
   >>> loop.set_alarm_at(tm=time.time() + 1,  # set timer to update player's progress bar
   ...                   callback=audiotools.ui.timer,
   ...                   user_data=player)
   >>> loop.run()

.. method:: PlayerGUI.select_track(radio_button, new_state, user_data, [auto_play])

   Begins playing the selected audio track.
   This must be implemented by a subclass.

Extra Urwid Functions
^^^^^^^^^^^^^^^^^^^^^

.. function:: timer(main_loop, playergui)

   Updates the status of the given :class:`PlayerGUI` object
   at regular intervals so that its progress bar moves properly.

.. function:: style()

   Returns a list of widget style tuples
   for use with Urwid's ``MainLoop`` object
   in order to style all interactive modes consistently.
