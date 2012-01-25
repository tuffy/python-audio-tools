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


except ImportError:
    AVAILABLE = False

    def not_available_message(msg):
        msg.error(u"urwid is required for interactive mode")
        msg.output(u"Please download and install urwid " +
                   u"from http://excess.org/urwid/")
        msg.output(u"or your system's package manager.")
