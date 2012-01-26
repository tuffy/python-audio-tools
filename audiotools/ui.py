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

"""A module for reusable GUI widgets"""

import audiotools

try:
    import urwid
    AVAILABLE = True


    class FocusFrame(urwid.Frame):
        """a special Frame widget which handles focus changes"""

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
            self.track_name = urwid.Edit(edit_text=metadata.track_name)
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
                        urwid.Edit(edit_text=getattr(metadata, field)))

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

            #anything not present is populated by Album widget
            return audiotools.MetaData(
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

            self.tracks = tracks

            def update_name(widget, new_value):
                widget._attrib = [("albumname", len(new_value))]

            #setup album name, which should be consistent between tracks
            album_name = set([t.metadata.album_name for t in tracks]).pop()
            self.album_name = urwid.Edit(edit_text=album_name)
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
                        urwid.Edit(edit_text=
                                   audiotools.most_numerous(
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

            self.albums = albums
            self.radios = []      #all our radio button-like checkboxes
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
                for (last, track) in audiotools.iter_last(iter(album.tracks)):
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
                        urwid.Columns([
                                ("fixed", len(prefix), urwid.Text(prefix)),
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


    class AlbumPreview(urwid.ListBox):
        def __init__(self, metadatas):
            rows = []
            for (last, metadata) in audiotools.iter_last(iter(metadatas)):
                if (last):
                    prefix = u" \u2514\u2500"
                else:
                    prefix = u" \u251c\u2500"
                rows.append(
                    urwid.Columns(
                        [("fixed", len(prefix),
                          urwid.Text(prefix)),
                         ("fixed", 6,
                          urwid.Text(" %2.d : " % (metadata.track_number))),
                         ("weight", 1,
                          urwid.Text(metadata.track_name))]))

            urwid.ListBox.__init__(self, rows)

    #the MetaDataFiller UI states are:
    #|          | selecting match | fields closed     | fields open           |
    #|----------+-----------------+-------------------+-----------------------|
    #| controls | SELECTING_MATCH | APPLY_LIST        | APPLY_LIST_W_FIELDS   |
    #| list     | SELECTING_LIST  | EDITING_LIST_ONLY | EDITING_LIST_W_FIELDS |
    #| fields   | N/A             | N/A               | EDITING_FIELDS        |
    #|----------+-----------------+-------------------+-----------------------|

    class MetaDataFiller(urwid.Frame):
        """a class for selecting the MetaData to apply to tracks"""

        (SELECTING_MATCH,
         SELECTING_LIST,
         APPLY_LIST_W_FIELDS,
         APPLY_LIST,
         EDITING_LIST_W_FIELDS,
         EDITING_LIST_ONLY,
         EDITING_FIELDS,
         UNKNOWN_STATE) = range(8)

        def __init__(self, metadata_choices):
            """metadata_choices[c][t]
            is a MetaData object for choice number "c" and track number "t"
            this widget allows the user to populate a set of MetaData objects
            which can be applied to tracks
            """

            assert(len(metadata_choices) > 0)

            self.metadata_choices = metadata_choices

            #a list of AlbumPreview objects, one for each possible choice
            self.album_previews = map(AlbumPreview, metadata_choices)

            #a list of AlbumList objects, one for each possible choice
            self.album_lists = [audiotools.ui.AlbumList(
                    [audiotools.ui.Album(map(audiotools.ui.Track,
                                             metadata_choice))],
                    self.select_album_or_track)
                                for metadata_choice in metadata_choices]

            #a list of radio buttons for each album choice
            self.albums = []

            #a simple widget for selecting one album choice from many
            self.select_button = urwid.Button("Select",
                                              on_press=self.select_best_match)
            self.select_album = urwid.LineBox(
                urwid.BoxAdapter(
                    urwid.ListBox([
                            urwid.RadioButton(
                                self.albums,
                                set([m.album_name for m in c]).pop(),
                                on_state_change=self.preview_album,
                                user_data=p)
                            for (c,p) in zip(metadata_choices,
                                             self.album_previews)] +
                                  [urwid.GridFlow([self.select_button],
                                                  10, 5, 1, 'center')]),
                    len(self.album_previews) + 1))
            if (hasattr(self.select_album, "set_title") and
                callable(self.select_album.set_title)):
                self.select_album.set_title(u"select best match")

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
                self.work_area = audiotools.ui.FocusFrame(
                    header=self.back_apply,
                    body=urwid.Filler(self.album_lists[0], valign='top'),
                    footer=self.collapsed,
                    focus_part="header")
            else:
                self.work_area = audiotools.ui.FocusFrame(
                    header=self.select_album,
                    body=self.album_previews[0],
                    footer=self.collapsed,
                    focus_part="header")
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

        def select_best_match(self, button):
            selected_index = [a.state for a in self.albums].index(True)

            #update control box with <back>, <select> buttons
            self.work_area.set_header(self.back_apply)

            #update preview area with editable area
            self.work_area.set_body(
                urwid.Filler(self.album_lists[selected_index], valign='top'))

            self.work_area.set_footer(self.collapsed)
            self.set_state_message(self.get_state())

        def select_album_or_track(self, checkbox, state_change, user_data=None):
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
            selected_index = [a.state for a in self.albums].index(True)

            for album in self.album_lists:
                for radio in album.radios:
                    radio.set_state(False, do_callback=False)

            self.work_area.set_header(self.select_album)
            self.work_area.set_body(self.album_previews[selected_index])
            self.work_area.set_footer(self.collapsed)
            self.set_state_message(self.get_state())

        def apply_selection(self, button):
            raise urwid.ExitMainLoop()

        def get_state(self):
            if (self.work_area.get_header() is self.select_album):
                #selecting match
                if (get_focus(self.work_area) == 'header'):
                    return self.SELECTING_MATCH
                elif (get_focus(self.work_area) == 'body'):
                    return self.SELECTING_LIST
                else:
                    return self.UNKNOWN_STATE
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
                control = self.select_album.base_widget
                if (i == 'tab'):
                    if (control.get_focus()[1] == len(self.metadata_choices)):
                        #focus on radio buttons
                        selection = [a.state for a in self.albums].index(True)
                        control.set_focus(selection, 'below')
                    else:
                        #focus on select button
                        control.set_focus(len(self.metadata_choices), 'above')
                elif (i == 'esc'):
                    control.set_focus(len(self.metadata_choices), 'above')
            elif (state == self.SELECTING_LIST):
                if ((i == 'tab') or (i == 'esc')):
                    self.work_area.set_focus('header')
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
                    selected_index = [a.state for a in self.albums].index(True)
                    for checkbox in self.album_lists[selected_index].radios:
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
                    selected_index = [a.state for a in self.albums].index(True)
                    for checkbox in self.album_lists[selected_index].radios:
                        checkbox.set_state(False, do_callback=False)
                    self.work_area.set_footer(self.collapsed)
                    self.work_area.set_focus('body')

        def set_keys(self, keys):
            """keys is a [(key, action), ...] list
            where 'key' and 'action' are both strings"""

            text = []
            for (last, (key, action)) in audiotools.iter_last(iter(keys)):
                text.append(('key', key))
                text.append(u" - " + action)
                if (not last):
                    text.append(u"  ")

            self.status.set_text(text)

        def update_focus(self, widget, focus_part):
            self.set_state_message(self.get_state())

        def set_state_message(self, state):
            if (state != self.UNKNOWN_STATE):
                self.set_keys([
                        #SELECTING_MATCH
                        [(u"esc", u"go to Select button"),
                         (u"tab", u"toggle between radios and Select")],

                        #SELECTING_LIST
                        [(u"esc/tab", u"return to control buttons")],

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

            selected_index = [a.state for a in self.albums].index(True)
            return self.album_lists[selected_index].albums[0].get_metadata()

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
    msg.error(u"urwid is required for interactive mode")
    msg.output(u"Please download and install urwid " +
               u"from http://excess.org/urwid/")
    msg.output(u"or your system's package manager.")
