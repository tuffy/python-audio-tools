#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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


from audiotools import MetaData, VERSION, re


class VorbisComment(MetaData):
    ATTRIBUTE_MAP = {'track_name':u'TITLE',
                     'track_number':u'TRACKNUMBER',
                     'track_total':u'TRACKTOTAL',
                     'album_name':u'ALBUM',
                     'artist_name':u'ARTIST',
                     'performer_name':u'PERFORMER',
                     'composer_name':u'COMPOSER',
                     'conductor_name':u'CONDUCTOR',
                     'media':u'SOURCE MEDIUM',
                     'ISRC':u'ISRC',
                     'catalog':u'CATALOG',
                     'copyright':u'COPYRIGHT',
                     'publisher':u'PUBLISHER',
                     'year':u'DATE',
                     'album_number':u'DISCNUMBER',
                     'album_total':u'DISCTOTAL',
                     'comment':u'COMMENT'}

    ALIASES = {}

    for aliases in [frozenset([u'TRACKTOTAL', u'TOTALTRACKS'])]:
        for alias in aliases:
            ALIASES[alias] = aliases

    SLASHED_FIELD = re.compile(r'(\d+)\s*/\s*(\d+)')

    SLASHED_FIELDS = {'track_number':(u'TRACKNUMBER', 0),
                      'track_total':(u'TRACKNUMBER', 1),
                      'album_number':(u'DISCNUMBER', 0),
                      'album_total':(u'DISCNUMBER', 1)}

    def __init__(self, comment_strings, vendor_string):
        """comment_strings is a list of unicode strings

        vendor_string is a unicode string"""

        self.__dict__["comment_strings"] = comment_strings
        self.__dict__["vendor_string"] = vendor_string

    def keys(self):
        return list(set([comment.split(u"=", 1)[0]
                         for comment in self.comment_strings
                         if (u"=" in comment)]))

    def values(self):
        return [comment.split(u"=", 1)[1]
                for comment in self.comment_strings
                if (u"=" in comment)]

    def items(self):
        return [tuple(comment.split(u"=", 1))
                for comment in self.comment_strings
                if (u"=" in comment)]

    def __getitem__(self, key):
        matching_keys = self.ALIASES.get(key.upper(), frozenset([key.upper()]))

        return [item_value for (item_key, item_value) in self.items()
                if (item_key.upper() in matching_keys)]

    def __setitem__(self, key, values):
        new_values = values[:]
        new_comment_strings = []
        matching_keys = self.ALIASES.get(key.upper(), frozenset([key.upper()]))

        for comment in self.comment_strings:
            if (u"=" in comment):
                (c_key, c_value) = comment.split(u"=", 1)
                if (c_key.upper() in matching_keys):
                    try:
                        #replace current value with newly set value
                        new_comment_strings.append(
                            u"%s=%s" % (c_key, new_values.pop(0)))
                    except IndexError:
                        #no more newly set values, so remove current value
                        continue
                else:
                    #passthrough unmatching values
                    new_comment_strings.append(comment)
            else:
                #passthrough values with no "=" sign
                new_comment_strings.append(comment)

        #append any leftover values
        for new_value in new_values:
            new_comment_strings.append(u"%s=%s" % (key.upper(), new_value))

        self.__dict__["comment_strings"] = new_comment_strings

    def __repr__(self):
        return "VorbisComment(%s, %s)" % \
            (repr(self.comment_strings), repr(self.vendor_string))

    def raw_info(self):
        from os import linesep
        from . import display_unicode

        #align the text strings on the "=" sign, if any

        if (len(self.comment_strings) > 0):
            max_indent = max([len(display_unicode(comment.split(u"=", 1)[0]))
                              for comment in self.comment_strings
                              if u"=" in comment])

            comment_strings = []
            for comment in self.comment_strings:
                if (u"=" in comment):
                    comment_strings.append(
                        u" " * (max_indent -
                                len(
                                display_unicode(comment.split(u"=", 1)[0]))) +
                        comment)
                else:
                    comment_strings.append(comment)
        else:
            comment_strings = 0

        return linesep.decode('ascii').join(
            [u"Vorbis Comment:  %s" % (self.vendor_string)] +
            comment_strings)


    def __getattr__(self, attr):
        #returns the first matching key for the given attribute
        #in our list of comment strings

        if (attr in self.SLASHED_FIELDS):
            #handle rare u'TRACKNUMBER=1/2' cases
            #which must always be numerical fields

            (slashed_field, slash_side) = self.SLASHED_FIELDS[attr]

            try:
                return int([match.group(slash_side + 1)
                            for match in
                            [self.SLASHED_FIELD.search(field)
                             for field in self[slashed_field]]
                            if (match is not None)][0])
            except IndexError:
                pass

        if (attr in self.__INTEGER_FIELDS__):
            #all integer fields are present in attribute map
            try:
                return int(self[self.ATTRIBUTE_MAP[attr]][0])
            except (IndexError, ValueError):
                return 0
        elif (attr in self.ATTRIBUTE_MAP):
            try:
                return self[self.ATTRIBUTE_MAP[attr]][0]
            except IndexError:
                return u""
        elif (attr in self.__FIELDS__):
            return u""
        else:
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError(attr)

    def __setattr__(self, attr, value):
        #updates the first matching key for the given attribute
        #in our list of comment strings

        if (attr in self.SLASHED_FIELDS):
            #setting numerical fields to 0
            #is equivilent to deleting them
            #in our high level implementation
            if (value == 0):
                self.__delattr__(attr)

            #handle rare u'TRACKNUMBER=1/2' cases
            #which must always be numerical fields
            (slashed_field, slash_side) = self.SLASHED_FIELDS[attr]

            slashed_matches = [match for match in
                               [self.SLASHED_FIELD.search(field)
                                for field in self[slashed_field]]
                               if (match is not None)]

            if (len(slashed_matches) > 0):
                if (slash_side == 0):
                    #retain the number on the right side
                    self[slashed_field] = (
                        [u"%d/%s" % (int(value),
                                     slashed_matches[0].group(2))] +
                        [m.group(0) for m in slashed_matches][1:])
                else:
                    #retain the number on the left side
                    self[slashed_field] = (
                        [u"%s/%d" % (slashed_matches[0].group(1),
                                     int(value))] +
                        [m.group(0) for m in slashed_matches][1:])

            else:
                current_values = self[self.ATTRIBUTE_MAP[attr]]
                self[self.ATTRIBUTE_MAP[attr]] = ([unicode(value)] +
                                                  current_values[1:])

        #plain text fields are easier
        elif (attr in self.ATTRIBUTE_MAP):
            #try to leave subsequent fields as-is
            current_values = self[self.ATTRIBUTE_MAP[attr]]
            self[self.ATTRIBUTE_MAP[attr]] = [value] + current_values[1:]
        else:
            self.__dict__[attr] = value

    def __delattr__(self, attr):
        #deletes all matching keys for the given attribute
        #in our list of comment strings

        if (attr in self.SLASHED_FIELDS):
            #handle rare u'TRACKNUMBER=1/2' cases
            #which must always be numerical fields
            (slashed_field, slash_side) = self.SLASHED_FIELDS[attr]

            slashed_matches = [match for match in
                               [self.SLASHED_FIELD.search(field)
                                for field in self[slashed_field]]
                               if (match is not None)]

            if (len(slashed_matches) > 0):
                if (slash_side == 0):
                    #retain the number on the right side
                    self[slashed_field] = \
                        [u"0/%s" % (m.group(2)) for m in slashed_matches
                         if (int(m.group(2)) != 0)]
                else:
                    #retain the number on the left side
                    self[slashed_field] = \
                        [m.group(1) for m in slashed_matches
                         if (int(m.group(1)) != 0)]
                    #FIXME - also wipe non-slashed field?

            else:
                self[self.ATTRIBUTE_MAP[attr]] = []

        elif (attr in self.ATTRIBUTE_MAP):
            #unlike __setattr_, which tries to preserve multiple instances
            #of fields, __delattr__ wipes them all
            #so that orphaned fields don't show up after deletion
            self[self.ATTRIBUTE_MAP[attr]] = []
        else:
            try:
                del(self.__dict__[attr])
            except KeyError:
                raise AttributeError(attr)

    def __eq__(self, metadata):
        raise NotImplementedError()

    @classmethod
    def converted(cls, metadata):
        """Converts metadata from another class to VorbisComment"""

        if ((metadata is None) or (isinstance(metadata, VorbisComment))):
            return metadata
        elif (metadata.__class__.__name__ == 'FlacMetaData'):
            if (metadata.vorbis_comment is not None):
                return cls(metadata.vorbis_comment.comment_strings,
                           metadata.vorbis_comment.vendor_string)
            else:
                return cls([], u"Python Audio Tools %s" % (VERSION))
        elif (metadata.__class__.__name__ == 'Flac_VORBISCOMMENT'):
            return cls(metadata.comment_strings,
                       metadata.vendor_string)
        else:
            comment_strings = []

            for (attr, keys) in cls.ATTRIBUTE_MAP.items():
                if (attr not in cls.__INTEGER_FIELDS__):
                    if (len(getattr(metadata, attr)) > 0):
                        comment_strings.append(
                            "%s=%s" % (cls.ATTRIBUTE_MAP[attr],
                                       getattr(metadata, attr)))
                else:
                    if (getattr(metadata, attr) > 0):
                        comment_strings.append(
                            "%s=%s" % (cls.ATTRIBUTE_MAP[attr],
                                       getattr(metadata, attr)))

            return cls(comment_strings, u"Python Audio Tools %s" % (VERSION))


    @classmethod
    def supports_images(cls):
        """returns False"""

        #There's actually a (proposed?) standard to add embedded covers
        #to Vorbis Comments by base64 encoding them.
        #This strikes me as messy and convoluted.
        #In addition, I'd have to perform a special case of
        #image extraction and re-insertion whenever converting
        #to FlacMetaData.  The whole thought gives me a headache.

        return False

    def images(self):
        """Returns a list of embedded Image objects."""

        return []

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        if (metadata is None):
            return
        else:
            from operator import or_

            metadata = self.__class__.converted(metadata)

            #first, port over the known fields
            for field in self.ATTRIBUTE_MAP.keys():
                if (field not in self.__INTEGER_FIELDS__):
                    if ((len(getattr(self, field)) == 0) and
                        (len(getattr(metadata, field)) > 0)):
                        setattr(self, field, getattr(metadata, field))
                else:
                    if ((getattr(self, field) == 0) and
                        (getattr(metadata, field) > 0)):
                        setattr(self, field, getattr(metadata, field))

            #then, port over any unknown fields
            known_keys = reduce(or_,
                                [self.ALIASES.get(field, frozenset([field]))
                                 for field in self.ATTRIBUTE_MAP.values()])
            for key in metadata.keys():
                if (key.upper() not in known_keys):
                    self[key] = metadata[key]

    def clean(self, fixes_performed):
        """Returns a new MetaData object that's been cleaned of problems."""

        reverse_attr_map = {}
        for (attr, key) in self.ATTRIBUTE_MAP.items():
            reverse_attr_map[key] = attr
            if (key in self.ALIASES):
                for alias in self.ALIASES[key]:
                    reverse_attr_map[alias] = attr

        cleaned_fields = []

        for comment_string in self.comment_strings:
            if (u"=" in comment_string):
                (key, value) = comment_string.split(u"=", 1)
                key = key.upper()
                if (key in reverse_attr_map):
                    attr = reverse_attr_map[key]
                    #handle all text fields by stripping whitespace
                    fix1 = value.rstrip()
                    if (fix1 != value):
                        fixes_performed.append(
                            _(u"removed trailing whitespace from %(field)s") %
                            {"field":key})

                    fix2 = fix1.lstrip()
                    if (fix2 != fix1):
                        fixes_performed.append(
                            _(u"removed leading whitespace from %(field)s") %
                            {"field":key})

                    #integer fields also strip leading zeroes
                    if ((attr in self.SLASHED_FIELDS) and
                        (self.SLASHED_FIELD.search(fix2) is not None)):
                        match = self.SLASHED_FIELD.search(value)
                        fix3 = "%d/%d" % (int(match.group(1)),
                                          int(match.group(2)))
                        if (fix3 != fix2):
                            fixes_performed.append(
                                _(u"removed whitespace/zeroes from %(field)s" %
                                  {"field":key}))
                    elif (attr in self.__INTEGER_FIELDS__):
                        fix3 = fix2.lstrip(u"0")
                        if (fix3 != fix2):
                            fixes_performed.append(
                                _(u"removed leading zeroes from %(field)s") %
                                {"field":key})
                    else:
                        fix3 = fix2

                    cleaned_fields.append(u"%s=%s" % (key, fix3))
                else:
                    cleaned_fields.append(comment_string)
            else:
                cleaned_fields.append(comment_string)

        return self.__class__(cleaned_fields, self.vendor_string)
