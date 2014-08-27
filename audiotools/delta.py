#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2008-2014  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
from itertools import izip
import bz2
import sqlite3
from hashlib import sha1
import base64
import anydbm
import subprocess
import tempfile
import whichdb
from audiotools import BIN, transfer_data


class UndoDB(object):
    """a class for performing undo operations on files

    this stores an undo/redo patch for transforming a file
    back to its original value, or forward again to its modified form"""

    def __init__(self, filename):
        """filename is the location on disk for this undo database"""

        self.db = sqlite3.connect(filename)
        self.cursor = self.db.cursor()

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS patch (
  patch_id INTEGER PRIMARY KEY AUTOINCREMENT,
  patch_data BLOB NOT NULL
)""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS source_file (
  source_checksum CHAR(40) PRIMARY KEY,
  source_size INTEGER NOT NULL,
  target_size INTEGER NOT NULL,
  patch_id INTEGER,
  FOREIGN KEY (patch_id) REFERENCES patch (patch_id) ON DELETE CASCADE
)""")

    def close(self):
        """closes any open database handles"""

        self.cursor.close()
        self.db.close()

    @classmethod
    def build_patch(cls, s1, s2):
        """given two strings, returns a transformation patch

        this function presumes the two strings will be largely
        equal and similar in length.  It operates by performing an
        xOR operation across both and BZ2 compressing the result"""

        if (len(s1) < len(s2)):
            s1 += (chr(0) * (len(s2) - len(s1)))
        elif (len(s2) < len(s1)):
            s2 += (chr(0) * (len(s1) - len(s2)))

        patch = bz2.compress("".join([chr(ord(x) ^ ord(y)) for (x, y) in
                                      izip(s1, s2)]))
        return patch

    @classmethod
    def apply_patch(cls, s, patch, new_length):
        """given a string, patch and new length, restores string

        patch is the same BZ2 compressed output from build_patch()
        new_length is the size of the string originally,
        which must be stored externally from the patch itself"""

        if (len(s) > new_length):
            s = s[0:new_length]
        elif (len(s) < new_length):
            s += (chr(0) * (new_length - len(s)))

        return "".join([chr(ord(x) ^ ord(y)) for (x, y) in
                        izip(s, bz2.decompress(patch))])

    def __add__(self, file_data1, file_data2):
        # file_data1's target is file_data2 and
        # file_data2's target is file_data1

        self.cursor.execute(
            "INSERT INTO patch (patch_id, patch_data) VALUES (?, ?)",
            [None,
             base64.b64encode(UndoDB.build_patch(file_data1,
                                                 file_data2)).decode('ascii')])
        patch_id = self.cursor.lastrowid
        try:
            self.cursor.execute("""INSERT INTO source_file (
source_checksum, source_size, target_size, patch_id) values (?, ?, ?, ?)""",
                                [sha1(file_data1).hexdigest().decode('ascii'),
                                 len(file_data1),
                                 len(file_data2),
                                 patch_id])
            self.cursor.execute("""INSERT INTO source_file (
source_checksum, source_size, target_size, patch_id) values (?, ?, ?, ?)""",
                                [sha1(file_data2).hexdigest().decode('ascii'),
                                 len(file_data2),
                                 len(file_data1),
                                 patch_id])
            self.db.commit()
        except sqlite3.IntegrityError:
            self.db.rollback()

    def __undo__(self, file_data):
        self.cursor.execute("""SELECT target_size, patch_data FROM
source_file, patch WHERE ((source_checksum = ?) AND
                          (source_size = ?) AND
                          (source_file.patch_id = patch.patch_id))""",
                            [sha1(file_data).hexdigest().decode('ascii'),
                             len(file_data)])
        row = self.cursor.fetchone()
        if (row is not None):
            (target_size, patch) = row
            return UndoDB.apply_patch(
                file_data,
                base64.b64decode(patch.encode('ascii')),
                target_size)
        else:
            return None

    def add(self, old_file, new_file):
        """adds an undo entry for transforming new_file to old_file

        both are filename strings"""

        old_f = open(old_file, 'rb')
        new_f = open(new_file, 'rb')
        try:
            self.__add__(old_f.read(), new_f.read())
        finally:
            old_f.close()
            new_f.close()

    def undo(self, new_file):
        """updates new_file to its original state,
        if present in the undo database

        returns True if undo performed, False if not"""

        new_f = open(new_file, 'rb')
        try:
            old_data = self.__undo__(new_f.read())
        finally:
            new_f.close()
        if (old_data is not None):
            old_f = open(new_file, 'wb')
            old_f.write(old_data)
            old_f.close()
            return True
        else:
            return False


class OldUndoDB(object):
    """a class for performing legacy undo operations on files

    this implementation is based on xdelta and requires it to be
    installed to function
    """

    def __init__(self, filename):
        """filename is the location on disk for this undo database"""

        self.db = anydbm.open(filename, 'c')

    def close(self):
        """closes any open database handles"""

        self.db.close()

    @classmethod
    def checksum(cls, filename):
        """returns the SHA1 checksum of the filename's contents"""

        f = open(filename, "rb")
        c = sha1("")
        try:
            transfer_data(f.read, c.update)
            return c.hexdigest()
        finally:
            f.close()

    def add(self, old_file, new_file):
        """adds an undo entry for transforming new_file to old_file

        both are filename strings"""

        from io import BytesIO

        # perform xdelta between old and new track to temporary file
        delta_f = tempfile.NamedTemporaryFile(suffix=".delta")

        try:
            if (subprocess.call([BIN["xdelta"],
                                 "delta",
                                 new_file, old_file, delta_f.name]) != 2):
                # store the xdelta in our internal db
                f = open(delta_f.name, 'rb')
                data = BytesIO()
                transfer_data(f.read, data.write)
                f.close()

                self.db[OldUndoDB.checksum(new_file)] = data.getvalue()
            else:
                raise IOError("error performing xdelta operation")
        finally:
            delta_f.close()

    def undo(self, new_file):
        """updates new_file to its original state,
        if present in the undo database"""

        undo_checksum = OldUndoDB.checksum(new_file)
        if (undo_checksum in self.db.keys()):
            # copy the xdelta to a temporary file
            xdelta_f = tempfile.NamedTemporaryFile(suffix=".delta")
            xdelta_f.write(self.db[undo_checksum])
            xdelta_f.flush()

            # patch the existing track to a temporary track
            old_track = tempfile.NamedTemporaryFile()
            try:
                if (subprocess.call([BIN["xdelta"],
                                     "patch",
                                     xdelta_f.name,
                                     new_file,
                                     old_track.name]) == 0):
                    # copy the temporary track over the existing file
                    f1 = open(old_track.name, 'rb')
                    f2 = open(new_file, 'wb')
                    transfer_data(f1.read, f2.write)
                    f1.close()
                    f2.close()
                    return True
                else:
                    raise IOError("error performing xdelta operation")
            finally:
                old_track.close()
                xdelta_f.close()
        else:
            return False


def open_db(filename):
    """given a filename string, returns UndoDB or OldUndoDB

    if the file doesn't exist, this uses UndoDB by default
    otherwise, detect OldUndoDB if xdelta is installed"""

    if (BIN.can_execute(BIN["xdelta"])):
        db = whichdb.whichdb(filename)
        if ((db is not None) and (db != '')):
            return OldUndoDB(filename)
        else:
            return UndoDB(filename)
    else:
        return UndoDB(filename)
