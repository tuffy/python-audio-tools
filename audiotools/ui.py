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

        def __init__(self, caption='', edit_text='', multiline=False,
                     align='left', wrap='space', allow_tab=False,
                     edit_pos=None, layout=None, key_map={}):
            urwid.Edit.__init__(self, caption=caption,
                                edit_text=edit_text,
                                multiline=multiline,
                                align=align,
                                wrap=wrap,
                                allow_tab=allow_tab,
                                edit_pos=edit_pos,
                                layout=layout)
            self.__key_map__ = {"enter": "down"}

        def keypress(self, size, key):
            return urwid.Edit.keypress(self, size,
                                       self.__key_map__.get(key, key))

    class DownIntEdit(urwid.IntEdit):
        """a subclass of urwid.IntEdit which performs a down-arrow keypress
        when the enter key is pressed,
        typically for moving to the next element in a form"""

        def __init__(self, caption='', default=None):
            urwid.IntEdit.__init__(self, caption=caption, default=default)
            self.__key_map__ = {"enter": "down"}

        def keypress(self, size, key):
            return urwid.Edit.keypress(self, size,
                                       self.__key_map__.get(key, key))

    class FocusFrame(urwid.Frame):
        """a special Frame widget which performs callbacks on focus changes"""

        def __init__(self, body, header=None, footer=None, focus_part='body'):
            urwid.Frame.__init__(self, body, header, footer, focus_part)
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

    class Track(urwid.LineBox):
        FIELDS = [(u"Track Name", "track_name"),
                  (u"Track Number", "track_number"),
                  (u"Album", "album_name"),
                  (u"Artist", "artist_name"),
                  (u"Performer", "performer_name"),
                  (u"Composer", "composer_name"),
                  (u"Conductor", "conductor_name"),
                  (u"ISRC", "ISRC"),
                  (u"Copyright", "copyright"),
                  (u"Recording Date", "date"),
                  (u"Comment", "comment")]

        def __init__(self, metadata):
            """takes a MetaData object and constructs a Track widget
            for modifying track-specific metadata"""

            self.metadata = metadata

            #setup contained editing widgets
            self.track_name = DownEdit(edit_text=metadata.track_name)
            if (metadata.track_total != 0):
                self.track_number = urwid.Text("%d of %d" %
                                               (metadata.track_number,
                                                metadata.track_total))
            else:
                self.track_number = urwid.Text("%d" % (metadata.track_number))
            for field in ["album_name",
                          "artist_name",
                          "performer_name",
                          "composer_name",
                          "conductor_name",
                          "ISRC",
                          "copyright",
                          "date",
                          "comment"]:
                setattr(self, field,
                        DownEdit(edit_text=getattr(metadata, field)))

            field_width = max([len(f) for (f, a) in Track.FIELDS]) + 2

            #initialize ourself
            urwid.LineBox.__init__(
                self,
                urwid.ListBox([urwid.Columns([
                                ("fixed", field_width,
                                 urwid.Text(field + u": ",
                                            align="right")),
                                ("weight", 1, getattr(self, attr))])
                               for (field, attr) in Track.FIELDS]))

            #setup widget title, if supported by Urwid
            if (hasattr(self, "set_title") and callable(self.set_title)):
                self.set_title(u"track fields")

        def field_count(self):
            return len(self.FIELDS)

        def get_metadata(self):
            """returns a populated MetaData object"""

            from . import MetaData

            #anything not present is populated by Album widget
            return MetaData(
                track_name=self.track_name.get_edit_text(),
                track_number=self.metadata.track_number,
                track_total=self.metadata.track_total,
                album_name=self.album_name.get_edit_text(),
                artist_name=self.artist_name.get_edit_text(),
                performer_name=self.performer_name.get_edit_text(),
                composer_name=self.composer_name.get_edit_text(),
                conductor_name=self.conductor_name.get_edit_text(),
                ISRC=self.ISRC.get_edit_text(),
                copyright=self.copyright.get_edit_text(),
                date=self.date.get_edit_text(),
                comment=self.comment.get_edit_text())

    class Album(urwid.LineBox):
        FIELDS = [(u"Album Name", "album_name"),
                  (u"Album Number", "album_number"),
                  (u"Artist", "artist_name"),
                  (u"Performer", "performer_name"),
                  (u"Composer", "composer_name"),
                  (u"Conductor", "conductor_name"),
                  (u"Media", "media"),
                  (u"Catalog #", "catalog"),
                  (u"Copyright", "copyright"),
                  (u"Publisher", "publisher"),
                  (u"Release Year", "year"),
                  (u"Recording Date", "date"),
                  (u"Comment", "comment")]

        LINKED_FIELDS = ["artist_name",
                         "performer_name",
                         "composer_name",
                         "conductor_name",
                         "copyright",
                         "date",
                         "comment"]

        def __init__(self, tracks):
            """takes a list of Track objects and constructs an Album widget
            for modifying album-specific metadata
            (which may propagate to tracks)"""

            from . import most_numerous

            self.tracks = tracks

            def update_name(widget, new_value):
                widget._attrib = [("albumname", len(new_value))]

            #setup album name, which should be consistent between tracks
            album_name = set([t.metadata.album_name for t in tracks]).pop()
            self.album_name = DownEdit(edit_text=album_name)
            update_name(self.album_name, album_name)
            urwid.connect_signal(self.album_name,
                                 'change',
                                 update_name)
            for t in tracks:
                t.album_name = self.album_name

            #self.number is the album_number field, which should be consistent
            self.number = set([t.metadata.album_number for t in tracks]).pop()

            #self.total is the album_total field, which should be consistent
            self.total = set([t.metadata.album_total for t in tracks]).pop()

            #setup album number field,
            if ((self.number != 0) or (self.total != 0)):
                if (self.total != 0):
                    self.album_number = urwid.Text(u"%d of %d" %
                                                   (self.number, self.total))
                else:
                    self.album_number = urwid.Text(u"%d" % (self.number))
            else:
                self.album_number = urwid.Text(u"")

            #build editable fields for album-specific metadata
            for field in ["artist_name",
                          "performer_name",
                          "composer_name",
                          "conductor_name",
                          "media",
                          "catalog",
                          "copyright",
                          "publisher",
                          "year",
                          "date",
                          "comment"]:
                setattr(self, field,
                        DownEdit(edit_text=most_numerous(
                            [getattr(t.metadata, field) for t in tracks],
                            empty_list=u"",
                            all_differ=u"various")))

            def field_changed(widget, new_value, attr):
                for track in self.tracks:
                    if (getattr(track, attr).edit_text == widget.edit_text):
                        getattr(track, attr).set_edit_text(new_value)

            #link fields common to both albums and tracks
            for attr in Album.LINKED_FIELDS:
                urwid.connect_signal(getattr(self, attr), 'change',
                                     field_changed, attr)

            field_width = max([len(f) for (f, a) in Album.FIELDS]) + 2

            #initialize ourself
            if ((self.number != 0) or (self.total != 0)):
                urwid.LineBox.__init__(
                    self,
                    urwid.ListBox(
                        [urwid.Columns([
                                    ("fixed", field_width,
                                     urwid.Text(field + u": ",
                                                align="right")),
                                    ("weight", 1, getattr(self, attr))])
                         for (field, attr) in Album.FIELDS]))
            else:
                #omit "Album Number" row if number and total are both missing
                #(a very common case)
                urwid.LineBox.__init__(
                    self,
                    urwid.ListBox(
                        [urwid.Columns([
                                    ("fixed", field_width,
                                     urwid.Text(field + u": ",
                                                align="right")),
                                    ("weight", 1, getattr(self, attr))])
                         for (field, attr) in Album.FIELDS
                         if (attr != "album_number")]))

            #setup widget title, if supported by Urwid
            if (hasattr(self, "set_title") and callable(self.set_title)):
                self.set_title(u"album fields")

        def field_count(self):
            if ((self.number != 0) or (self.total != 0)):
                return len(self.FIELDS)
            else:
                return len(self.FIELDS) - 1

        def get_metadata(self):
            """yields a populated MetaData object per track"""

            for track in self.tracks:
                metadata = track.get_metadata()
                metadata.album_number = self.number
                metadata.album_total = self.total
                metadata.media = self.media.get_edit_text()
                metadata.catalog = self.catalog.get_edit_text()
                metadata.publisher = self.publisher.get_edit_text()
                metadata.year = self.year.get_edit_text()

                yield metadata

    class AlbumList(urwid.Pile):
        def __init__(self, albums, select_item):
            """takes a list of Album objects
            and a select_item() callback for when an album or track is selected
            and returns a tree-like widget for editing an album or tracks"""

            from . import iter_last

            self.albums = albums
            self.radios = []      # all our radio button-like checkboxes
            rows = []

            def unselect_others(checkbox, state_change):
                for radio in self.radios:
                    if (radio is not checkbox):
                        radio.set_state(False, do_callback=False)

            for album in albums:
                #the checkbox for selecting an album
                checkbox = urwid.CheckBox(u"",
                                          on_state_change=select_item,
                                          user_data=album)
                urwid.connect_signal(checkbox, "change", unselect_others)
                self.radios.append(checkbox)

                #setup album row depending on if it has an album number or not
                if (album.number != 0):
                    album_digits = len(str(album.number))
                    rows.append(
                        urwid.Columns(
                            [("fixed", 4, checkbox),
                             ("fixed", album_digits + 1,
                              urwid.Text(u"%%%d.d " % (album_digits) % \
                                             (album.number))),
                             ("fixed", 2, urwid.Text(u": ")),
                             ("weight", 1, album.album_name)]))
                else:
                    rows.append(
                        urwid.Columns([("fixed", 4, checkbox),
                                       ("fixed", 2, urwid.Text(u": ")),
                                       ("weight", 1, album.album_name)]))

                #the largest number of digits in a track_number field
                track_digits = max([len(str(t.metadata.track_number))
                                    for t in album.tracks])

                #setup track rows
                for (last, track) in iter_last(iter(album.tracks)):
                    #the checkbox for selecting a track
                    checkbox = urwid.CheckBox(u"",
                                              on_state_change=select_item,
                                              user_data=track)
                    urwid.connect_signal(checkbox, "change", unselect_others)
                    self.radios.append(checkbox)

                    #prefixed differently depending on its position
                    if (last):
                        prefix = u" \u2514\u2500"
                    else:
                        prefix = u" \u251c\u2500"

                    #setup track row
                    rows.append(
                        urwid.Columns(
                            [("fixed", len(prefix), urwid.Text(prefix)),
                             ("fixed", 4, checkbox),
                             ("fixed", track_digits + 1,
                              urwid.Text(u"%%%d.d " % (track_digits) % \
                                             (track.metadata.track_number))),
                             ("fixed", 2, urwid.Text(u": ")),
                             ("weight", 1, track.track_name)]))

            urwid.Pile.__init__(self, rows)

        def get_metadata(self):
            """for each album, yields a generator of MetaData objects, like:

            for album in albumlist:
                for metadata in album:
                    <process MetaData object>
            """

            for album in self.albums:
                yield album.get_metadata()

    def get_focus(widget):
        #something to smooth out the differences between Urwid versions

        if (hasattr(widget, "get_focus") and callable(widget.get_focus)):
            return widget.get_focus()
        else:
            return widget.focus_part

    #the MetaDataFiller UI states are:
    #|          | selecting match | fields closed     | fields open           |
    #|----------+-----------------+-------------------+-----------------------|
    #| controls | N/A             | APPLY_LIST        | APPLY_LIST_W_FIELDS   |
    #| list     | SELECTING_MATCH | EDITING_LIST_ONLY | EDITING_LIST_W_FIELDS |
    #| fields   | N/A             | N/A               | EDITING_FIELDS        |
    #|----------+-----------------+-------------------+-----------------------|

    class MetaDataFiller(urwid.Frame):
        """a class for selecting the MetaData to apply to tracks"""

        (SELECTING_MATCH,
         APPLY_LIST_W_FIELDS,
         APPLY_LIST,
         EDITING_LIST_W_FIELDS,
         EDITING_LIST_ONLY,
         EDITING_FIELDS,
         UNKNOWN_STATE) = range(7)

        def __init__(self, metadata_choices):
            """metadata_choices[c][t]
            is a MetaData object for choice number "c" and track number "t"
            this widget allows the user to populate a set of MetaData objects
            which can be applied to tracks
            """

            assert(len(metadata_choices) > 0)

            self.metadata_choices = metadata_choices

            #a list of AlbumList objects, one for each possible choice
            self.album_lists = [AlbumList(
                    [Album(map(Track,
                               metadata_choice))],
                    self.select_album_or_track)
                                for metadata_choice in metadata_choices]

            self.selected_album_list = self.album_lists[0]

            self.select_header = urwid.LineBox(
                urwid.Text(u"select best match", align='center'))

            widgets = []
            for (choice, album) in zip(metadata_choices, self.album_lists):
                widgets.append(urwid.Button(choice[0].album_name,
                                            on_press=self.select_best_match,
                                            user_data=album))
                widgets.append(urwid.Divider())
            self.select_album = urwid.ListBox(widgets)

            #a simple widget for going back or applying selected album
            if (len(metadata_choices) == 1):
                #no back button for selecting choice if only 1 choice
                self.back_apply = urwid.LineBox(
                    urwid.GridFlow([
                            urwid.Button("Apply",
                                         on_press=self.apply_selection)],
                                   10, 5, 1, 'center'))
            else:
                self.back_apply = urwid.LineBox(
                    urwid.GridFlow([
                            urwid.Button("Back",
                                         on_press=self.back_to_select),
                            urwid.Button("Apply",
                                         on_press=self.apply_selection)],
                                   10, 5, 1, 'center'))
                self.back_apply.base_widget.set_focus(1)

            self.collapsed = urwid.Divider(div_char=u'\u2500')

            #header will be either an album selection box
            #or a set of controls

            #body will be either the album preview area
            #or a place to edit an album's track list

            #footer will either be a collapsed line
            #or a place to edit album/track field data
            if (len(metadata_choices) == 1):
                #automatically shift to selected choice
                #if only one available
                self.work_area = FocusFrame(
                    header=self.back_apply,
                    body=urwid.Filler(self.album_lists[0], valign='top'),
                    footer=self.collapsed,
                    focus_part="header")
            else:
                #otherwise, offer a choice of albums to select
                self.work_area = FocusFrame(
                    header=self.select_header,
                    body=self.select_album,
                    footer=self.collapsed,
                    focus_part="body")
            self.work_area.set_focus_callback(self.update_focus)

            self.status = urwid.Text(u"", align='left')

            urwid.Frame.__init__(
                self,
                body=self.work_area,
                footer=self.status,
                focus_part="body")

            if (len(metadata_choices) == 1):
                self.set_state_message(self.APPLY_LIST)
            else:
                self.set_state_message(self.SELECTING_MATCH)

        def preview_album(self, radio_button, new_state, user_data):
            if (new_state):
                self.work_area.set_body(user_data)

        def select_best_match(self, button, album_list):
            self.selected_album_list = album_list

            #update control box with <back>, <select> buttons
            self.work_area.set_header(self.back_apply)

            #update preview area with editable area
            self.work_area.set_body(
                urwid.Filler(album_list, valign='top'))

            self.work_area.set_footer(self.collapsed)
            self.work_area.set_focus('header')
            self.set_state_message(self.get_state())

        def select_album_or_track(self, checkbox, state_change,
                                  user_data=None):
            if ((state_change == True) and (user_data is not None)):
                #select item
                self.work_area.set_footer(
                    urwid.BoxAdapter(user_data, user_data.field_count()))
                self.work_area.set_focus('footer')
            elif (state_change == False):
                #unselect item
                self.work_area.set_footer(self.collapsed)
                self.work_area.set_focus('body')

        def back_to_select(self, button):
            for album in self.album_lists:
                for radio in album.radios:
                    radio.set_state(False, do_callback=False)

            self.work_area.set_header(self.select_header)
            self.work_area.set_body(self.select_album)
            self.work_area.set_footer(self.collapsed)
            self.work_area.set_focus('body')
            self.set_state_message(self.get_state())

        def apply_selection(self, button):
            raise urwid.ExitMainLoop()

        def get_state(self):
            if (self.work_area.get_body() is self.select_album):
                #selecting match
                return self.SELECTING_MATCH
            elif (self.work_area.get_header() is self.back_apply):
                if (self.work_area.get_footer() is self.collapsed):
                    #match selected, fields closed
                    if (get_focus(self.work_area) == 'header'):
                        return self.APPLY_LIST
                    elif (get_focus(self.work_area) == 'body'):
                        return self.EDITING_LIST_ONLY
                    else:
                        return self.UNKNOWN_STATE
                else:
                    #match selected, fields open
                    if (get_focus(self.work_area) == 'header'):
                        return self.APPLY_LIST_W_FIELDS
                    elif (get_focus(self.work_area) == 'body'):
                        return self.EDITING_LIST_W_FIELDS
                    else:
                        return self.EDITING_FIELDS
            else:
                return self.UNKNOWN_STATE

        def handle_text(self, i):
            state = self.get_state()
            if (state == self.SELECTING_MATCH):
                pass
            elif (state == self.APPLY_LIST_W_FIELDS):
                if (i == 'tab'):
                    self.work_area.set_focus('body')
            elif (state == self.APPLY_LIST):
                if (i == 'tab'):
                    self.work_area.set_focus('body')
            elif (state == self.EDITING_LIST_W_FIELDS):
                if (i == 'tab'):
                    self.work_area.set_focus('footer')
                elif (i == 'esc'):
                    for checkbox in self.selected_album_list.radios:
                        checkbox.set_state(False, do_callback=False)
                    self.work_area.set_footer(self.collapsed)
                    self.work_area.set_focus('body')
            elif (state == self.EDITING_LIST_ONLY):
                if ((i == 'tab') or (i == 'esc')):
                    self.work_area.set_focus('header')
            elif (state == self.EDITING_FIELDS):
                if (i == 'tab'):
                    self.work_area.set_focus('body')
                elif (i == 'esc'):
                    for checkbox in self.selected_album_list.radios:
                        checkbox.set_state(False, do_callback=False)
                    self.work_area.set_footer(self.collapsed)
                    self.work_area.set_focus('body')

        def set_keys(self, keys):
            """keys is a [(key, action), ...] list
            where 'key' and 'action' are both strings"""

            from . import iter_last

            if (len(keys) > 0):
                text = []
                for (last, (key, action)) in iter_last(iter(keys)):
                    text.append(('key', key))
                    text.append(u" - " + action)
                    if (not last):
                        text.append(u"  ")

                self.status.set_text(text)
            else:
                self.status.set_text(u"")

        def update_focus(self, widget, focus_part):
            self.set_state_message(self.get_state())

        def set_state_message(self, state):
            if (state != self.UNKNOWN_STATE):
                self.set_keys([
                        #SELECTING_MATCH
                        [],

                        #APPLY_LIST_W_FIELDS
                        [(u"tab", u"go to track list")],

                        #APPLY_LIST
                        [(u"tab", u"go to track list")],

                        #EDITING_LIST_W_FIELDS
                        [(u"esc", u"close fields"),
                         (u"tab", u"return to fields")],

                        #EDITING_LIST_ONLY
                        [(u"esc/tab", u"return to control buttons")],

                        #EDITING_FIELDS
                        [(u"esc", u"close fields"),
                         (u"tab", u"return to track list")]
                        ][state])
            else:
                self.status.set_text(u"")

        def populated_metadata(self):
            """yields a fully populated MetaData object per track
            to be called once Urwid's main loop has completed"""

            return self.selected_album_list.albums[0].get_metadata()

    class MetaDataEditor(urwid.Frame):
        def __init__(self, tracks, on_text_change=None):
            """tracks is a list of (id, label, MetaData) tuples
            in the order they are to be displayed
            where id is some hashable ID value
            label is a unicode string
            and MetaData is an audiotools.MetaData-compatible object or None"""

            #a list of track IDs in the order they appear
            self.track_ids = []

            #a list of (track_id, label) tuples in the order they should appear
            track_labels = []

            #the order metadata fields should appear
            field_labels = [("track_name", u"Track Name"),
                            ("artist_name", u"Artist Name"),
                            ("album_name", u"Album Name"),
                            ("track_number", u"Track Number"),
                            ("track_total", u"Track Total"),
                            ("album_number", u"Album Number"),
                            ("album_total", u"Album Total"),
                            ("performer_name", u"Performer Name"),
                            ("composer_name", u"Composer Name"),
                            ("conductor_name", u"Conductor Name"),
                            ("catalog", u"Catalog Number"),
                            ("ISRC", u"ISRC"),
                            ("publisher", u"Publisher"),
                            ("media", u"Media"),
                            ("year", u"Release Year"),
                            ("date", u"Recording Date"),
                            ("copyright", u"Copyright"),
                            ("comment", u"Comment")]

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
                                           state=False,
                                           on_state_change=self.activate_swivel,
                                           user_data=Swivel(
                        left_top_widget=urwid.Text(('label', 'fields')),
                        left_alignment='fixed',
                        left_width=4 + 14,
                        left_radios=field_radios,
                        left_ids=[field_id for (field_id, label)
                                  in field_labels],
                        right_top_widget=urwid.Text(('label', track_label)),
                        right_alignment='weight',
                        right_width=1,
                        right_widgets=[getattr(self.metadata_edits[track_id],
                                               field_id)
                                       for (field_id, label) in field_labels]))
                radio._label.set_wrap_mode(urwid.CLIP)
                track_radios[track_id] = radio

            #generate radio buttons for metadata labels
            for (field_id, field_label) in field_labels:
                radio = OrderedRadioButton(ordered_group=field_radios_order,
                                           group=swivel_radios,
                                           label=('label', field_label),
                                           state=False,
                                           on_state_change=self.activate_swivel,
                                           user_data=Swivel(
                        left_top_widget=urwid.Text(('label', 'filenames')),
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
                                       for (track_id, track) in track_labels]))
                radio._label.set_align_mode('right')
                field_radios[field_id] = radio

            self.edit_box = urwid.Pile([])

            urwid.Frame.__init__(
                self,
                header=urwid.Columns(
                    [("fixed", 1, urwid.Text(u"")),
                     ("weight", 1, urwid.Text(u""))]),
                body=urwid.Filler(self.edit_box, valign='top'))

            if (len(self.metadata_edits) != 1):
                #if more than one track, select track_name radio button
                field_radios["track_name"].set_state(True)
            else:
                #if only one track, select that track's radio button
                track_radios[track_labels[0][0]].set_state(True)

        def activate_swivel(self, radio_button, selected, swivel):
            if (selected):
                self.selected_radio = radio_button
                while (len(self.edit_box.widget_list)):
                    del(self.edit_box.widget_list[-1])
                for (left_widget, right_widget) in swivel.rows():
                    self.edit_box.widget_list.append(
                        urwid.Columns([
                                (swivel.left_alignment,
                                 swivel.left_width,
                                 left_widget),
                                (swivel.right_alignment,
                                 swivel.right_width,
                                 right_widget)]))
                self.edit_box.set_focus(0)
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
        def __init__(self, checkbox_group, linked_widget, unlinked_widget):
            """linked_widget is shown when the linking checkbox is checked
            otherwise unlinked_widget is shown"""

            self.linked_widget = linked_widget
            self.unlinked_widget = unlinked_widget
            self.checkbox_group = checkbox_group

            if (linked_widget.get_text() != unlinked_widget.get_text()):
                self.checkbox = urwid.CheckBox(u"",
                                               on_state_change=self.swap_link)
                self.checkbox_group.append(self.checkbox)
                urwid.Columns.__init__(
                    self,
                    [("fixed", 3, urwid.Text(u" : ")),
                     ("weight", 1, unlinked_widget),
                     ("fixed", 4, self.checkbox)])
            else:
                self.checkbox = urwid.CheckBox(u"",
                                               state=True,
                                               on_state_change=self.swap_link)
                self.checkbox_group.append(self.checkbox)
                urwid.Columns.__init__(
                    self,
                    [("fixed", 3, urwid.Text(u" : ")),
                     ("weight", 1, linked_widget),
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
            self.checkbox_groups = {}
            for field in metadata.FIELDS:
                if (field not in metadata.INTEGER_FIELDS):
                    widget = DownEdit(edit_text=getattr(metadata, field))
                else:
                    widget = DownIntEdit(default=getattr(metadata, field))

                if (on_change is not None):
                    urwid.connect_signal(widget, 'change', on_change)
                setattr(self, field, widget)
                self.checkbox_groups[field] = []


    class TrackMetaData:
        def __init__(self, metadata, base_metadata, on_change=None):
            for field in metadata.FIELDS:
                if (field not in metadata.INTEGER_FIELDS):
                    widget = DownEdit(edit_text=getattr(metadata, field))
                else:
                    widget = DownIntEdit(default=getattr(metadata, field))

                if (on_change is not None):
                    urwid.connect_signal(widget, 'change', on_change)
                setattr(self, field,
                        LinkedWidgets(
                        base_metadata.checkbox_groups[field],
                        getattr(base_metadata, field), widget))

        def edited_metadata(self):
            return audiotools.MetaData(**dict(
                    [(attr, getattr(self, attr).value())
                     for attr in audiotools.MetaData.FIELDS]))


    class Swivel:
        def __init__(self, left_top_widget,
                     left_alignment,
                     left_width,
                     left_radios,
                     left_ids,
                     right_top_widget,
                     right_alignment,
                     right_width,
                     right_widgets):
            assert(len(left_ids) == len(right_widgets))
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
            for (i, choice) in enumerate(metadata_choices):
                msg.output(u"%d) %s" % (i + 1, choice[0].album_name))
            try:
                choice = int(raw_input("please select best match (1-%d) : " %
                                       (len(metadata_choices)))) - 1
            except ValueError:
                choice = None

        return metadata_choices[choice]


def not_available_message(msg):
    """prints a message about lack of Urwid availability
    to a Messenger object"""

    msg.error(u"urwid is required for interactive mode")
    msg.output(u"Please download and install urwid " +
               u"from http://excess.org/urwid/")
    msg.output(u"or your system's package manager.")
