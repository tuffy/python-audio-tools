#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""a module for reusable GUI widgets"""

import audiotools

try:
    import urwid
    AVAILABLE = True

    class DownEdit(urwid.Edit):
        """a subclass of urwid.Edit which performs a down-arrow keypress
        when the enter key is pressed,
        typically for moving to the next element in a form"""

        def __init__(self, *args, **kwargs):
            urwid.Edit.__init__(self, *args, **kwargs)
            self.__key_map__ = {"enter": "down"}

        def keypress(self, size, key):
            return urwid.Edit.keypress(self, size,
                                       self.__key_map__.get(key, key))

    class DownIntEdit(urwid.IntEdit):
        """a subclass of urwid.IntEdit which performs a down-arrow keypress
        when the enter key is pressed,
        typically for moving to the next element in a form"""

        def __init__(self, *args, **kwargs):
            urwid.IntEdit.__init__(self, *args, **kwargs)
            self.__key_map__ = {"enter": "down"}

        def keypress(self, size, key):
            return urwid.Edit.keypress(self, size,
                                       self.__key_map__.get(key, key))

    class FocusFrame(urwid.Frame):
        """a special Frame widget which performs callbacks on focus changes"""

        def __init__(self, *args, **kwargs):
            urwid.Frame.__init__(self, *args, **kwargs)
            self.focus_callback = None
            self.focus_callback_arg = None

        def set_focus_callback(self, callback, user_arg=None):
            """callback(widget, focus_part[, user_arg])
            called when focus is set"""

            self.focus_callback = callback
            self.focus_callback_arg = user_arg

        def set_focus(self, part):
            urwid.Frame.set_focus(self, part)
            if (self.focus_callback is not None):
                if (self.focus_callback_arg is not None):
                    self.focus_callback(self, part, self.focus_callback_arg)
                else:
                    self.focus_callback(self, part)

    def get_focus(widget):
        #something to smooth out the differences between Urwid versions

        if (hasattr(widget, "get_focus") and callable(widget.get_focus)):
            return widget.get_focus()
        else:
            return widget.focus_part


    class OutputFiller(urwid.Frame):
        """a class for selecting MetaData and populating output parameters
        for tracks"""

        def __init__(self, metadata_choices,
                     file_paths,
                     output_directory,
                     format_string,
                     output_class,
                     quality):
            """metadata_choices[c][t]
            is a MetaData object for choice number "c" and track number "t"
            all choices must have the same number of tracks

            file_paths is a list of strings for file input paths
            the number of file paths must equal the number of metadata objects
            in each metadata choice

            output_directory is a string of the default output dir

            format_string is a UTF-8 encoded format string

            output_class is the default AudioFile-compatible class

            quality is a string of the default output quality to use
            """

            self.__cancelled__ = True

            #ensure there's at least one set of choices
            assert(len(metadata_choices) > 0)

            #ensure file path count is equal to metadata track count
            assert(len(metadata_choices[0]) == len(file_paths))

            from audiotools.text import (LAB_CANCEL,
                                         LAB_NEXT,
                                         LAB_PREVIOUS)

            #setup status bars for output messages
            self.metadata_status = urwid.Text(u"")
            self.options_status = urwid.Text(u"")

            #setup a widget for populating metadata fields
            metadata_buttons = urwid.Filler(
                urwid.Columns(
                    widget_list=[urwid.Button(LAB_CANCEL,
                                              on_press=self.exit),
                                 urwid.Button(LAB_NEXT,
                                              on_press=self.next)],
                    dividechars=3,
                    focus_column=1))

            self.metadata = MetaDataFiller(metadata_choices,
                                           self.metadata_status,
                                           [("fixed", 1, metadata_buttons)])

            #setup a widget for populating output parameters
            options_buttons = urwid.Filler(
                urwid.Columns(
                    widget_list=[urwid.Button(LAB_PREVIOUS,
                                              on_press=self.previous),
                                 urwid.Button(u"Apply", #FIXME
                                              on_press=self.complete)],
                    dividechars=3,
                    focus_column=1))

            self.options = OutputOptions(
                output_dir=output_directory,
                format_string=format_string,
                audio_class=output_class,
                quality=quality,
                file_paths=file_paths,
                metadatas=[None for t in file_paths],
                extra_widgets=[("fixed", 1, options_buttons)])

            self.options.set_focus(options_buttons)

            #finish initialization
            urwid.Frame.__init__(self,
                                 body=self.metadata,
                                 footer=self.metadata_status)

        def exit(self, button):
            self.__cancelled__ = True
            raise urwid.ExitMainLoop()

        def previous(self, button):
            self.set_body(self.metadata)
            self.set_footer(self.metadata_status)

        def next(self, button):
            self.options.set_metadatas(
                list(self.metadata.populated_metadata()))
            self.set_body(self.options)
            self.set_footer(self.options_status)

        def complete(self, button):
            self.__cancelled__ = False
            raise urwid.ExitMainLoop()

        def cancelled(self):
            """returns True if the widget was cancelled,
            False if exited normally"""

            return self.__cancelled__

        def handle_text(self, i):
            if (self.get_body() is self.metadata):
                if (i == 'esc'):
                    self.exit(None)
                elif (i == 'f1'):
                    self.metadata.selected_match.select_previous_item()
                elif (i == 'f2'):
                    self.metadata.selected_match.select_next_item()
            else:
                if (i == 'esc'):
                    self.previous(None)

        def output_tracks(self):
            """yields (output_class,
                       output_path,
                       output_quality,
                       output_metadata) tuple for each input audio file"""

            (audiofile_class, quality, paths) = self.options.selected_options()



    class MetaDataFiller(urwid.Pile):
        """a class for selecting the MetaData to apply to tracks"""

        def __init__(self, metadata_choices, status,
                     extra_widgets=None):
            """metadata_choices[c][t]
            is a MetaData object for choice number "c" and track number "t"
            this widget allows the user to populate a set of MetaData objects
            which can be applied to tracks
            """

            #there must be at least one choice
            assert(len(metadata_choices) > 0)

            #all choices must have at least 1 track
            assert(min(map(len, metadata_choices)) > 0)

            #and all choices must have the same number of tracks
            assert(len(set(map(len, metadata_choices))) == 1)

            from audiotools.text import (LAB_SELECT_BEST_MATCH,
                                         LAB_TRACK_X_OF_Y,
                                         LAB_KEY_NEXT,
                                         LAB_KEY_PREVIOUS)

            self.metadata_choices = metadata_choices

            self.status = status

            #setup radio button for each possible match
            matches = []
            radios = [urwid.RadioButton(matches,
                                        (choice[0].album_name
                                         if (choice[0].album_name is not None)
                                         else u""),
                                        on_state_change=self.select_match,
                                        user_data=i)
                      for (i, choice) in enumerate(metadata_choices)]
            for radio in radios:
                radio._label.set_wrap_mode(urwid.CLIP)

            #put radio buttons in pretty container
            self.select_match = urwid.LineBox(urwid.ListBox(radios))

            if (hasattr(self.select_match, "set_title")):
                self.select_match.set_title(LAB_SELECT_BEST_MATCH)

            #setup a MetaDataEditor for each possible match
            self.edit_matches = [
                MetaDataEditor(
                    [(i,
                      LAB_TRACK_X_OF_Y % (i + 1, len(metadata_choices[0])),
                      track) for (i, track) in enumerate(choice)],
                    on_swivel_change=self.swiveled)
                for choice in metadata_choices]
            self.selected_match = self.edit_matches[0]

            #place selector at top only if there's more than one match
            if (len(metadata_choices) > 1):
                widgets = [("fixed",
                            len(metadata_choices) + 2,
                            self.select_match)]
            else:
                widgets = []

            widgets.append(("weight", 1,
                            self.edit_matches[0]))
            widgets.append(("fixed", 1,
                            urwid.Filler(urwid.Divider(u"\u2500"))))

            if (extra_widgets is not None):
                widgets.extend(extra_widgets)

            urwid.Pile.__init__(self, widgets)

        def select_match(self, radio, selected, match):
            if (selected):
                self.selected_match = self.edit_matches[match]
                self.body.widget_list[1] = self.selected_match

        def swiveled(self, radio_button, selected, swivel):
            if (selected):
                from .text import (LAB_KEY_NEXT,
                                   LAB_KEY_PREVIOUS)

                keys = []
                if (radio_button.previous_radio_button() is not None):
                    keys.extend([('key', u"F1"),
                                 LAB_KEY_PREVIOUS % (swivel.swivel_type)])
                if (radio_button.next_radio_button() is not None):
                    if (len(keys) > 0):
                        keys.append(u"   ")
                    keys.extend([('key', u"F2"),
                                 LAB_KEY_NEXT % (swivel.swivel_type)])

                if (len(keys) > 0):
                    self.status.set_text(keys)
                else:
                    self.status.set_text(u"")

        def populated_metadata(self):
            """yields a fully populated MetaData object per track
            to be called once Urwid's main loop has completed"""

            for (track_id, metadata) in self.selected_match.metadata():
                yield metadata


    class MetaDataEditor(urwid.Frame):
        def __init__(self, tracks,
                     on_text_change=None,
                     on_swivel_change=None):
            """tracks is a list of (id, label, MetaData) tuples
            in the order they are to be displayed
            where id is some hashable ID value
            label is a unicode string
            and MetaData is an audiotools.MetaData-compatible object or None

            on_text_change is a callback for when any text field is modified

            on_swivel_change is a callback for when
            tracks and fields are swapped
            """

            #a list of track IDs in the order they appear
            self.track_ids = []

            #a list of (track_id, label) tuples in the order they should appear
            track_labels = []

            #the order metadata fields should appear
            field_labels = [(attr, audiotools.MetaData.FIELD_NAMES[attr])
                            for attr in audiotools.MetaData.FIELD_ORDER]

            #a dict of track_id->TrackMetaData values
            self.metadata_edits = {}

            #determine the base metadata all others should be linked against
            base_metadata = {}
            for (track_id, track_label, metadata) in tracks:
                if (metadata is None):
                    metadata = audiotools.MetaData()
                self.track_ids.append(track_id)
                for (attr, value) in metadata.fields():
                        base_metadata.setdefault(attr, set([])).add(value)

            base_metadata = BaseMetaData(
                metadata=audiotools.MetaData(
                    **dict([(field, list(values)[0])
                            for (field, values) in base_metadata.items()
                            if (len(values) == 1)])),
                on_change=on_text_change)

            #populate the track_labels and metadata_edits lookup tables
            for (track_id, track_label, metadata) in tracks:
                if (metadata is None):
                    metadata = audiotools.MetaData()
                if (track_id not in self.metadata_edits):
                    track_labels.append((track_id, track_label))
                    self.metadata_edits[track_id] = TrackMetaData(
                        metadata=metadata,
                        base_metadata=base_metadata,
                        on_change=on_text_change)
                else:
                    #no_duplicates via open_files should filter this case
                    raise ValueError("same track ID cannot appear twice")

            swivel_radios = []

            track_radios_order = []
            track_radios = {}

            field_radios_order = []
            field_radios = {}

            #generate radio buttons for track labels
            for (track_id, track_label) in track_labels:
                radio = OrderedRadioButton(ordered_group=track_radios_order,
                                           group=swivel_radios,
                                           label=('label', track_label),
                                           state=False)

                swivel = Swivel(
                    swivel_type=u"track",
                    left_top_widget=urwid.Text(('label', 'fields')),
                    left_alignment='fixed',
                    left_width=4 + 14,
                    left_radios=field_radios,
                    left_ids=[field_id for (field_id, label) in field_labels],
                    right_top_widget=urwid.Text(('label', track_label),
                                                wrap=urwid.CLIP),
                    right_alignment='weight',
                    right_width=1,
                    right_widgets=[getattr(self.metadata_edits[track_id],
                                           field_id)
                                   for (field_id, label) in field_labels])

                radio._label.set_wrap_mode(urwid.CLIP)

                urwid.connect_signal(radio, 'change', self.activate_swivel,
                                     swivel)

                if (on_swivel_change is not None):
                    urwid.connect_signal(radio, 'change', on_swivel_change,
                                         swivel)

                track_radios[track_id] = radio

            #generate radio buttons for metadata labels
            for (field_id, field_label) in field_labels:
                radio = OrderedRadioButton(ordered_group=field_radios_order,
                                           group=swivel_radios,
                                           label=('label', field_label),
                                           state=False)

                swivel = Swivel(
                    swivel_type=u"field",
                    left_top_widget=urwid.Text(('label', u'files')),
                    left_alignment='weight',
                    left_width=1,
                    left_radios=track_radios,
                    left_ids=[track_id for (track_id, track)
                              in track_labels],
                    right_top_widget=urwid.Text(('label', field_label)),
                    right_alignment='weight',
                    right_width=2,
                    right_widgets=[getattr(self.metadata_edits[track_id],
                                           field_id)
                                   for (track_id, track) in track_labels])

                radio._label.set_align_mode('right')

                urwid.connect_signal(radio, 'change', self.activate_swivel,
                                     swivel)

                if (on_swivel_change is not None):
                    urwid.connect_signal(radio, 'change', on_swivel_change,
                                         swivel)

                field_radios[field_id] = radio

            urwid.Frame.__init__(
                self,
                header=urwid.Columns(
                    [("fixed", 1, urwid.Text(u"")),
                     ("weight", 1, urwid.Text(u""))]),
                body=urwid.ListBox([]))

            if (len(self.metadata_edits) != 1):
                #if more than one track, select track_name radio button
                field_radios["track_name"].set_state(True)
            else:
                #if only one track, select that track's radio button
                track_radios[track_labels[0][0]].set_state(True)

        def activate_swivel(self, radio_button, selected, swivel):
            if (selected):
                self.selected_radio = radio_button

                #add new entries according to swivel's values
                self.set_body(
                    # urwid.Filler(
                        urwid.ListBox([
                                urwid.Columns([(swivel.left_alignment,
                                                swivel.left_width,
                                                left_widget),
                                               (swivel.right_alignment,
                                                swivel.right_width,
                                                right_widget)])
                                for (left_widget,
                                     right_widget) in swivel.rows()]))
                        # valign='top'))

                #update header with swivel's values
                self.set_header(
                    urwid.Pile([urwid.Columns(
                                [(swivel.left_alignment,
                                  swivel.left_width,
                                  swivel.left_top_widget),
                                 (swivel.right_alignment,
                                  swivel.right_width,
                                  LinkedWidgetHeader(
                                            swivel.right_top_widget))]),
                                urwid.Columns(
                                [(swivel.left_alignment,
                                  swivel.left_width,
                                  urwid.Divider(u"\u2500")),
                                 (swivel.right_alignment,
                                  swivel.right_width,
                                  LinkedWidgetDivider())])]))
            else:
                pass

        def select_previous_item(self):
            previous_radio = self.selected_radio.previous_radio_button()
            if (previous_radio is not None):
                previous_radio.set_state(True)

        def select_next_item(self):
            next_radio = self.selected_radio.next_radio_button()
            if (next_radio is not None):
                next_radio.set_state(True)

        def metadata(self):
            """yields a (track_id, MetaData) tuple
            per edited metadata track"""

            for track_id in self.track_ids:
                yield (track_id,
                       self.metadata_edits[track_id].edited_metadata())


    class OrderedRadioButton(urwid.RadioButton):
        def __init__(self, ordered_group, group, label,
                     state='first True', on_state_change=None, user_data=None):
            urwid.RadioButton.__init__(self,
                                       group,
                                       label,
                                       state,
                                       on_state_change,
                                       user_data)
            ordered_group.append(self)
            self.ordered_group = ordered_group

        def previous_radio_button(self):
            for (current_radio,
                 previous_radio) in zip(self.ordered_group,
                                        [None] + self.ordered_group):
                if (current_radio is self):
                    return previous_radio
            else:
                return None

        def next_radio_button(self):
            for (current_radio,
                 next_radio) in zip(self.ordered_group,
                                    self.ordered_group[1:] + [None]):
                if (current_radio is self):
                    return next_radio
            else:
                return None


    class LinkedWidgetHeader(urwid.Columns):
        def __init__(self, widget):
            urwid.Columns.__init__(self,
                                   [("fixed", 3, urwid.Text(u" \u2502 ")),
                                    ("weight", 1, widget),
                                    ("fixed", 4, urwid.Text(u""))])


    class LinkedWidgetDivider(urwid.Columns):
        def __init__(self):
            urwid.Columns.__init__(
                self,
                [("fixed", 3, urwid.Text(u"\u2500\u2534\u2500")),
                 ("weight", 1, urwid.Divider(u"\u2500")),
                 ("fixed", 4, urwid.Text(u"\u2500" * 4))])


    class LinkedWidgets(urwid.Columns):
        def __init__(self, checkbox_group, linked_widget, unlinked_widget,
                     initially_linked):
            """linked_widget is shown when the linking checkbox is checked
            otherwise unlinked_widget is shown"""

            self.linked_widget = linked_widget
            self.unlinked_widget = unlinked_widget
            self.checkbox_group = checkbox_group

            self.checkbox = urwid.CheckBox(u"",
                                           state=initially_linked,
                                           on_state_change=self.swap_link)
            self.checkbox_group.append(self.checkbox)

            urwid.Columns.__init__(
                self,
                [("fixed", 3, urwid.Text(u" : ")),
                 ("weight", 1,
                  linked_widget if initially_linked else unlinked_widget),
                 ("fixed", 4, self.checkbox)])

        def swap_link(self, checkbox, linked):
            if (linked):
                #if nothing else linked in this checkbox group,
                #set linked text to whatever the last unlinked text as
                if (set([cb.get_state() for cb in self.checkbox_group
                         if (cb is not checkbox)]) == set([False])):
                    self.linked_widget.set_edit_text(
                        self.unlinked_widget.get_edit_text())
                self.widget_list[1] = self.linked_widget
                self.set_focus(2)
            else:
                #set unlinked text to whatever the last linked text was
                self.unlinked_widget.set_edit_text(
                    self.linked_widget.get_edit_text())
                self.widget_list[1] = self.unlinked_widget
                self.set_focus(2)

        def value(self):
            if (self.checkbox.get_state()):
                widget = self.linked_widget
            else:
                widget = self.unlinked_widget

            if (hasattr(widget, "value") and callable(widget.value)):
                return widget.value()
            elif (hasattr(widget, "get_edit_text") and
                  callable(widget.get_edit_text)):
                return widget.get_edit_text()
            else:
                return None

    class BaseMetaData:
        def __init__(self, metadata, on_change=None):
            """metadata is a MetaData object
            on_change is a callback for when the text field is modified"""

            self.metadata = metadata
            self.checkbox_groups = {}
            for field in metadata.FIELDS:
                if (field not in metadata.INTEGER_FIELDS):
                    value = getattr(metadata, field)
                    widget = DownEdit(edit_text=value if value is not None
                                      else u"")
                else:
                    value = getattr(metadata, field)
                    widget = DownIntEdit(default=value if value is not None
                                         else 0)

                if (on_change is not None):
                    urwid.connect_signal(widget, 'change', on_change)
                setattr(self, field, widget)
                self.checkbox_groups[field] = []


    class TrackMetaData:
        NEVER_LINK = frozenset(["track_name", "track_number", "ISRC"])

        def __init__(self, metadata, base_metadata, on_change=None):
            """metadata is a MetaData object
            base_metadata is a BaseMetaData object to link against
            on_change is a callback for when the text field is modified"""

            for field in metadata.FIELDS:
                if (field not in metadata.INTEGER_FIELDS):
                    value = getattr(metadata, field)
                    widget = DownEdit(edit_text=value if value is not None
                                      else u"")
                else:
                    value = getattr(metadata, field)
                    widget = DownIntEdit(default=value if value is not None
                                         else 0)

                if (on_change is not None):
                    urwid.connect_signal(widget, 'change', on_change)

                linked_widget = LinkedWidgets(
                    checkbox_group=base_metadata.checkbox_groups[field],
                    linked_widget=getattr(base_metadata, field),
                    unlinked_widget=widget,
                    initially_linked=((field not in self.NEVER_LINK) and
                                      (getattr(metadata, field) ==
                                       getattr(base_metadata.metadata, field))))

                setattr(self, field, linked_widget)

        def edited_metadata(self):
            """returns a MetaData object of the track's
            current value based on its widgets"""

            return audiotools.MetaData(**dict(
                    [(attr, value) for (attr, value) in
                     [(attr, getattr(self, attr).value())
                      for attr in audiotools.MetaData.FIELDS]
                     if ((len(value) > 0) if
                         (attr not in audiotools.MetaData.INTEGER_FIELDS) else
                         (value > 0))]))


    class Swivel:
        def __init__(self, swivel_type,
                     left_top_widget,
                     left_alignment,
                     left_width,
                     left_radios,
                     left_ids,
                     right_top_widget,
                     right_alignment,
                     right_width,
                     right_widgets):

            assert(len(left_ids) == len(right_widgets))

            self.swivel_type = swivel_type
            self.left_top_widget = left_top_widget
            self.left_alignment = left_alignment
            self.left_width = left_width
            self.left_radios = left_radios
            self.left_ids = left_ids
            self.right_top_widget = right_top_widget
            self.right_alignment = right_alignment
            self.right_width = right_width
            self.right_widgets = right_widgets

        def rows(self):
            for (left_id,
                 right_widget) in zip(self.left_ids, self.right_widgets):
                yield (self.left_radios[left_id], right_widget)


    def tab_complete(path):
        """given a partially-completed path string
        returns a path string completed as far as possible
        """

        import os.path

        (base, remainder) = os.path.split(path)
        if (os.path.isdir(base)):
            try:
                candidate_dirs = [d for d in os.listdir(base)
                                  if (d.startswith(remainder) and
                                      os.path.isdir(os.path.join(base, d)))]
                if (len(candidate_dirs) == 0):
                    #no possible matches to tab complete
                    return path
                elif (len(candidate_dirs) == 1):
                    #one possible match to tab complete
                    return os.path.join(base, candidate_dirs[0]) + os.sep
                else:
                    #multiple possible matches to tab complete
                    #so complete as much as possible
                    return os.path.join(base,
                                        os.path.commonprefix(candidate_dirs))
            except OSError:
                #unable to read base dir to complete the rest
                return path
        else:
            #base doesn't exist,
            #so we don't know how to complete the rest
            return path


    def pop_directory(path):
        """given a path string,
        returns a new path string with one directory removed if possible"""

        import os.path

        base = os.path.split(path.rstrip(os.sep))[0]
        if (not base.endswith(os.sep)):
            return base + os.sep
        else:
            return base


    class SelectButtons(urwid.Pile):
        def __init__(self, widget_list, focus_item=None, cancelled=None):
            """cancelled is a callback which is called
            when the esc key is pressed
            it takes no arguments"""

            urwid.Pile.__init__(self, widget_list, focus_item)
            self.cancelled = cancelled

        def keypress(self, size, key):
            key = urwid.Pile.keypress(self, size, key)
            if ((key == "esc") and (self.cancelled is not None)):
                self.cancelled()
                return
            else:
                return key


    class SelectOneDialog(urwid.WidgetWrap):
        signals = ['close']
        def __init__(self, select_one, items, selected_value):
            self.select_one = select_one
            self.items = items

            selected_button = 0
            buttons = []
            for (i, (label, value)) in enumerate(items):
                buttons.append(urwid.Button(label=label,
                                            on_press=self.select_button,
                                            user_data=(label, value)))
                if (value == selected_value):
                    selected_button = i
            pile = SelectButtons(buttons,
                                 selected_button,
                                 lambda: self._emit("close"))
            fill = urwid.Filler(pile)
            self.__super.__init__(urwid.AttrWrap(fill, 'popbg'))

        def select_button(self, button, label_value):
            (label, value) = label_value
            self.select_one.make_selection(label, value)
            self._emit("close")


    class SelectOne(urwid.PopUpLauncher):
        def __init__(self, items, selected_value=None, on_change=None):
            """items is a list of (unicode, value) tuples
            where value can be any sort of object

            selected_value is a selected object

            on_change is a callback which takes a new selected object
            which is called as on_change(new_value)"""

            self.__select_button__ = urwid.Button(u"")
            self.__super.__init__(self.__select_button__)
            urwid.connect_signal(self.original_widget, 'click',
                lambda button: self.open_pop_up())

            assert(len(items) > 0)

            self.__items__ = items
            self.__selected_value__ = None  #set by make_selection, below
            self.__on_change__ = on_change

            if (selected_value is not None):
                try:
                    (label, value) = [pair for pair in items
                                      if pair[1] is selected_value][0]
                except IndexError:
                    (label, value) = items[0]
            else:
                (label, value) = items[0]
            self.make_selection(label, value)

        def create_pop_up(self):
            pop_up = SelectOneDialog(self,
                                     self.__items__,
                                     self.__selected_value__)
            urwid.connect_signal(pop_up, 'close',
                lambda button: self.close_pop_up())
            return pop_up

        def get_pop_up_parameters(self):
            return {'left':0,
                    'top':1,
                    'overlay_width':max([4 + len(i[0]) for i in
                                         self.__items__]),
                    'overlay_height':len(self.__items__)}

        def make_selection(self, label, value):
            self.__select_button__.set_label(label)
            self.__selected_value__ = value
            if (self.__on_change__ is not None):
                self.__on_change__(value)

        def selection(self):
            return self.__selected_value__

        def set_items(self, items, selected_value):
            self.__items__ = items
            self.make_selection([label for (label, value) in items if
                                 value is selected_value][0],
                                selected_value)


    class SelectDirectory(urwid.Columns):
        def __init__(self, initial_directory, on_change=None, user_data=None):
            self.edit = EditDirectory(initial_directory)
            urwid.Columns.__init__(self,
                                   [('weight', 1, self.edit),
                                    ('fixed', 10, BrowseDirectory(self.edit))])
            if (on_change is not None):
                urwid.connect_signal(self.edit,
                                     'change',
                                     on_change,
                                     user_data)

        def set_directory(self, directory):
            #FIXME - allow this to be assigned externally
            raise NotImplementedError()

        def get_directory(self):
            return self.edit.get_directory()


    class EditDirectory(urwid.Edit):
        def __init__(self, initial_directory):
            """initial_directory is a plain string
            in the default filesystem encoding"""

            FS_ENCODING = audiotools.FS_ENCODING

            urwid.Edit.__init__(self,
                                edit_text=initial_directory.decode(FS_ENCODING),
                                wrap='clip',
                                allow_tab=False)

        def keypress(self, size, key):
            key = urwid.Edit.keypress(self, size, key)
            FS_ENCODING = audiotools.FS_ENCODING
            import os.path

            if (key == 'tab'):
                new_text = tab_complete(os.path.expanduser(
                        self.get_edit_text().encode(FS_ENCODING))).decode(
                    FS_ENCODING)
                self.set_edit_text(new_text)
                self.set_edit_pos(len(new_text))
            elif (key == 'ctrl w'):
                new_text = pop_directory(os.path.expanduser(
                        self.get_edit_text().encode(FS_ENCODING))).decode(
                    FS_ENCODING)
                self.set_edit_text(new_text)
                self.set_edit_pos(len(new_text))
            else:
                return key

        def set_directory(self, directory):
            """directory is a plain directory string to set"""

            FS_ENCODING = audiotools.FS_ENCODING

            new_text = directory.decode(FS_ENCODING)
            self.set_edit_text(new_text)
            self.set_edit_pos(len(new_text))

        def get_directory(self):
            """returns selected directory as a plain string"""

            FS_ENCODING = audiotools.FS_ENCODING
            return self.get_edit_text().encode(FS_ENCODING)


    class BrowseDirectory(urwid.PopUpLauncher):
        def __init__(self, edit_directory):
            """edit_directory is an EditDirectory object"""

            self.__super.__init__(
                urwid.Button(u"browse",
                             on_press=lambda button: self.open_pop_up()))
            self.edit_directory = edit_directory

        def create_pop_up(self):
            pop_up = BrowseDirectoryDialog(self.edit_directory)
            urwid.connect_signal(pop_up, "close",
                                 lambda button: self.close_pop_up())
            return pop_up

        def get_pop_up_parameters(self):
            #FIXME - make these values dynamic base on edit_directory's location
            return {'left':0,
                    'top':1,
                    'overlay_width':70,
                    'overlay_height':20}


    class BrowseDirectoryDialog(urwid.WidgetWrap):
        signals = ['close']
        def __init__(self, edit_directory):
            """edit_directory is an EditDirectory object"""

            browser = DirectoryBrowser(
                edit_directory.get_directory(),
                directory_selected=self.select_directory,
                cancelled=lambda: self._emit("close"))
            self.__super.__init__(urwid.AttrWrap(browser, 'popbg'))
            self.edit_directory = edit_directory

        def select_directory(self, selected_directory):
            self.edit_directory.set_directory(selected_directory)
            self._emit("close")


    class DirectoryBrowser(urwid.TreeListBox):
        def __init__(self, initial_directory,
                     directory_selected=None,
                     cancelled=None):
            import os
            import os.path

            def path_iter(path):
                if (path == os.sep):
                    yield path
                else:
                    path = path.rstrip(os.sep)
                    if (len(path) > 0):
                        (head, tail) = os.path.split(path)
                        for part in path_iter(head):
                            yield part
                        yield tail
                    else:
                        return

            topnode = DirectoryNode(os.sep)

            for path_part in path_iter(
                os.path.abspath(os.path.expanduser(initial_directory))):
                try:
                    if (path_part == "/"):
                        node = topnode
                    else:
                        node = node.get_child_node(path_part)
                    widget = node.get_widget()
                    widget.expanded = True
                    widget.update_expanded_icon()
                except urwid.treetools.TreeWidgetError:
                    break

            urwid.TreeListBox.__init__(self, urwid.TreeWalker(topnode))
            self.set_focus(node)
            self.directory_selected = directory_selected
            self.cancelled = cancelled

        def selected_directory(self):
            import os
            import os.path

            def focused_nodes():
                (widget, node) = self.get_focus()
                while (not node.is_root()):
                    yield node.get_key()
                    node = node.get_parent()
                else:
                    yield os.sep

            return os.path.join(*reversed(list(focused_nodes()))) + os.sep

        def unhandled_input(self, size, input):
            input = urwid.TreeListBox.unhandled_input(self, size, input)
            if (input == 'enter'):
                if (self.directory_selected is not None):
                    self.directory_selected(self.selected_directory())
                else:
                    return input
            elif (input == 'esc'):
                if (self.cancelled is not None):
                    self.cancelled()
                else:
                    return input
            else:
                return input


    class DirectoryWidget(urwid.TreeWidget):
        indent_cols = 1

        def __init__(self, node):
            self.__super.__init__(node)
            self.expanded = False
            self.update_expanded_icon()

        def keypress(self, size, key):
            key = urwid.TreeWidget.keypress(self, size, key)
            if (key == " "):
                self.expanded = not self.expanded
                self.update_expanded_icon()
            else:
                return key

        def get_display_text(self):
            node = self.get_node()
            if node.get_depth() == 0:
                return "/"
            else:
                return node.get_key()


    class ErrorWidget(urwid.TreeWidget):
        indent_cols = 1

        def get_display_text(self):
            return ('error', u"(error/permission denied)")


    class ErrorNode(urwid.TreeNode):
        def load_widget(self):
            return ErrorWidget(self)


    class DirectoryNode(urwid.ParentNode):
        def __init__(self, path, parent=None):
            import os
            import os.path

            if (path == os.sep):
                urwid.ParentNode.__init__(self,
                                          value=path,
                                          key=None,
                                          parent=parent,
                                          depth=0)
            else:
                urwid.ParentNode.__init__(self,
                                          value=path,
                                          key=os.path.basename(path),
                                          parent=parent,
                                          depth=path.count(os.sep))

        def load_parent(self):
            import os.path

            (parentname, myname) = os.path.split(self.get_value())
            parent = DirectoryNode(parentname)
            parent.set_child_node(self.get_key(), self)
            return parent

        def load_child_keys(self):
            import os.path

            dirs = []
            try:
                path = self.get_value()
                for a in os.listdir(path):
                    if os.path.isdir(os.path.join(path,a)):
                        dirs.append(a)
            except OSError, e:
                depth = self.get_depth() + 1
                self._children[None] = ErrorNode(self, parent=self, key=None,
                                                 depth=depth)
                return [None]

            return dirs

        def load_child_node(self, key):
            """Return a DirectoryNode"""

            import os.path

            index = self.get_child_index(key)
            path = os.path.join(self.get_value(), key)
            return DirectoryNode(path, parent=self)

        def load_widget(self):
            return DirectoryWidget(self)


    class OutputOptions(urwid.Pile):
        def __init__(self, output_dir, format_string,
                     audio_class, quality, file_paths, metadatas,
                     extra_widgets=None):
            """
            | field         | value      | meaning                             |
            |---------------+------------+-------------------------------------|
            | output_dir    | string     | default output directory            |
            | format_string | string     | format string to use for files      |
            | audio_class   | AudioFile  | audio class of output files         |
            | quality       | string     | quality level of output             |
            | file_paths    | [string]   | list of strings for input paths     |
            | metadatas     | [MetaData] | MetaData objects for files, or None |

            note that the length of file_paths must equal length of metadatas
            """

            assert(len(file_paths) == len(metadatas))

            self.file_paths = file_paths
            self.metadatas = metadatas
            self.selected_class = audio_class
            self.selected_quality = quality

            self.output_format = urwid.Edit(
                edit_text=audiotools.FILENAME_FORMAT.decode('utf-8'))
            urwid.connect_signal(self.output_format,
                                 'change',
                                 self.format_changed)

            self.output_directory = SelectDirectory(output_dir,
                                                    self.directory_changed)

            self.output_tracks_frame = urwid.Frame(
                body=urwid.Filler(urwid.Text(u"")))

            self.output_tracks = [urwid.Text(u"") for path in file_paths]

            self.output_tracks_list = urwid.ListBox(self.output_tracks)

            self.invalid_output_format = urwid.Filler(
                urwid.Text(u"invalid output format string",
                           align="center"))

            self.output_quality = SelectOne(
                [(u"N/A", "")])

            self.output_type = SelectOne(
                sorted([(t.NAME, t) for t in
                        audiotools.AVAILABLE_TYPES
                        if t.has_binaries(audiotools.BIN)],
                       lambda x,y: cmp(x[0], y[0])),
                audio_class,
                self.select_type)

            self.select_type(audio_class, quality)

            widgets = []
            widgets.append(("fixed", 1,
                            urwid.Filler(urwid.Columns(
                            [('fixed', 10, urwid.Text(u"Dir : ",
                                                      align="right")),
                             ('weight', 1, self.output_directory)]))))
            widgets.append(("fixed", 1,
                            urwid.Filler(urwid.Columns(
                            [('fixed', 10, urwid.Text(u"Format : ",
                                                      align="right")),
                             ('weight', 1, self.output_format)]))))
            widgets.append(("fixed", 1,
                            urwid.Filler(urwid.Columns(
                            [('fixed', 10, urwid.Text(u"Type : ",
                                                      align="right")),
                             ('weight', 1, self.output_type)]))))
            widgets.append(("fixed", 1,
                            urwid.Filler(urwid.Columns(
                            [('fixed', 10, urwid.Text(u"Quality : ",
                                                      align="right")),
                             ('weight', 1, self.output_quality)]))))
            widgets.append(("weight", 1,
                            urwid.LineBox(self.output_tracks_frame,
                                          title=u"Output Files")))

            if (extra_widgets is not None):
                widgets.extend(extra_widgets)

            urwid.Pile.__init__(self, widgets)

            self.update_tracks()

        def select_type(self, audio_class, default_quality=None):
            self.selected_class = audio_class

            if (len(audio_class.COMPRESSION_MODES) < 2):
                #one audio quality for selected type
                try:
                    quality = audio_class.COMPRESSION_MODES[0]
                except IndexError:
                    #this shouldn't happen, but just in case
                    quality = ""
                self.output_quality.set_items([(u"N/A", quality)], quality)
            else:
                #two or more audio qualities for selected type
                qualities = audio_class.COMPRESSION_MODES
                if (default_quality is not None):
                    default = [q for q in qualities if
                               q == default_quality][0]
                else:
                    default = [q for q in qualities if
                               q == audio_class.DEFAULT_COMPRESSION][0]
                self.output_quality.set_items(
                    [(q.decode('ascii') if q not in
                      audio_class.COMPRESSION_DESCRIPTIONS else
                      u"%s - %s" % (q.decode('ascii'),
                                    audio_class.COMPRESSION_DESCRIPTIONS[q]),
                      q)
                     for q in qualities],
                    default)

            self.update_tracks()

        def directory_changed(self, widget, new_value):
            FS_ENCODING = audiotools.FS_ENCODING
            self.update_tracks(output_directory=new_value.encode(FS_ENCODING))

        def format_changed(self, widget, new_value):
            self.update_tracks(filename_format=new_value)

        def update_tracks(self, output_directory=None, filename_format=None):
            FS_ENCODING = audiotools.FS_ENCODING
            import os.path

            #get the output directory
            if (output_directory is None):
                output_directory = self.output_directory.get_directory()

            #get selected audio format
            audio_class = self.selected_class

            #get current filename format
            if (filename_format is None):
                filename_format = \
                    self.output_format.get_edit_text().encode('utf-8')
            try:
                #generate list of filename strings
                #from paths, metadatas and format
                filenames = [audio_class.track_name(file_path,
                                                    metadata,
                                                    filename_format)
                             for (file_path, metadata) in zip(self.file_paths,
                                                              self.metadatas)]

                #prepend selected directory to filename strings
                self.output_paths = [os.path.join(output_directory, filename)
                                     for filename in filenames]

                #check for duplicates in paths
                path_counts = {}
                for path in self.output_paths:
                    if (path in path_counts):
                        path_counts[path] += 1
                    else:
                        path_counts[path] = 1

                #and populate output files list
                for (path, track) in zip(self.output_paths,
                                         self.output_tracks):
                    if (path_counts[path] == 1):
                        track.set_text(path.decode(FS_ENCODING))
                    else:
                        track.set_text(("duplicate", path.decode(FS_ENCODING)))
                if (self.output_tracks_frame.get_body() is not
                    self.output_tracks_list):
                    self.output_tracks_frame.set_body(
                        self.output_tracks_list)
            except (audiotools.UnsupportedTracknameField,
                    audiotools.InvalidFilenameFormat):
                #if there's an error calling track_name,
                #populate files list with an error message
                if (self.output_tracks_frame.get_body() is not
                    self.invalid_output_format):
                    self.output_tracks_frame.set_body(
                        self.invalid_output_format)

        def selected_options(self):
            """returns (AudioFile class, quality string, [output path strings])
            based on selected options"""

            return (self.selected_class,
                    self.output_quality.selection(),
                    self.output_paths)

        def set_metadatas(self, metadatas):
            """metadatas is a list of MetaData objects
            (some of which may be None)"""

            if (len(metadatas) != len(self.metadatas)):
                raise ValueError("new metadatas must have same count as old")

            self.metadatas = metadatas
            self.update_tracks()



except ImportError:
    AVAILABLE = False


def select_metadata(metadata_choices, msg):
    """queries the user for the best matching metadata to use"""

    assert(len(metadata_choices) > 0)
    if (len(metadata_choices) == 1):
        return metadata_choices[0]
    else:
        choice = None
        while (choice not in range(0, len(metadata_choices))):
            from audiotools.text import (LAB_SELECT_BEST_MATCH)
            for (i, choice) in enumerate(metadata_choices):
                msg.output(u"%d) %s" % (i + 1, choice[0].album_name))
            try:
                choice = int(raw_input(u"%s (1-%d) : " %
                                       (LAB_SELECT_BEST_MATCH,
                                        len(metadata_choices)))) - 1
            except ValueError:
                choice = None

        return metadata_choices[choice]


#FIXME - add an option handler
#which returns (class, path, quality, metadata) tuples
#based on options, or raises exception on invalid options


def not_available_message(msg):
    """prints a message about lack of Urwid availability
    to a Messenger object"""

    from audiotools.text import (ERR_URWID_REQUIRED,
                                 ERR_GET_URWID1,
                                 ERR_GET_URWID2)
    msg.error(ERR_URWID_REQUIRED)
    msg.output(ERR_GET_URWID1)
    msg.output(ERR_GET_URWID2)
