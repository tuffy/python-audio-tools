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


    class MetaDataFiller(urwid.Frame):
        """a class for selecting the MetaData to apply to tracks"""

        def __init__(self, metadata_choices):
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
                                         LAB_APPLY,
                                         LAB_CANCEL,
                                         LAB_KEY_NEXT,
                                         LAB_KEY_PREVIOUS)

            self.metadata_choices = metadata_choices

            self.status = urwid.Text(u"")

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

            widgets.append(
                ("fixed", 1,
                 urwid.Filler(
                        urwid.GridFlow([urwid.Button(LAB_APPLY,
                                                     on_press=self.finish,
                                                     user_data=True),
                                        urwid.Button(LAB_CANCEL,
                                                     on_press=self.finish,
                                                     user_data=False)],
                                       10, 5, 1, 'center'))))

            self.body = urwid.Pile(widgets)

            self.canceled = True

            urwid.Frame.__init__(
                self,
                body=self.body,
                footer=self.status,
                focus_part="body")

        def select_match(self, radio, selected, match):
            if (selected):
                self.selected_match = self.edit_matches[match]
                self.body.widget_list[1] = self.selected_match

        def swiveled(self, radio_button, selected, swivel):
            if (selected):
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

        def handle_text(self, i):
            if (i == 'esc'):
                self.canceled = True
                raise urwid.ExitMainLoop()
            elif (i == 'f1'):
                self.selected_match.select_previous_item()
            elif (i == 'f2'):
                self.selected_match.select_next_item()

        def finish(self, button, apply_changes):
            self.canceled = not apply_changes
            raise urwid.ExitMainLoop()

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
                    left_top_widget=urwid.Text(('label', 'files')),
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


def not_available_message(msg):
    """prints a message about lack of Urwid availability
    to a Messenger object"""

    from audiotools.text import (ERR_URWID_REQUIRED,
                                 ERR_GET_URWID1,
                                 ERR_GET_URWID2)
    msg.error(ERR_URWID_REQUIRED)
    msg.output(ERR_GET_URWID1)
    msg.output(ERR_GET_URWID2)
