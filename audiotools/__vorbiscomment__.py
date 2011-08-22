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


from audiotools import MetaData, Con, VERSION, re


class VorbisComment(MetaData, dict):
    """A complete Vorbis Comment tag."""

    VORBIS_COMMENT = Con.Struct(
        "vorbis_comment",
        Con.PascalString("vendor_string",
                         length_field=Con.ULInt32("length")),
        Con.PrefixedArray(
            length_field=Con.ULInt32("length"),
            subcon=Con.PascalString("value",
                                    length_field=Con.ULInt32("length"))),
        Con.Const(Con.Byte("framing"), 1))

    ATTRIBUTE_MAP = {'track_name': 'TITLE',
                     'track_number': 'TRACKNUMBER',
                     'track_total': 'TRACKTOTAL',
                     'album_name': 'ALBUM',
                     'artist_name': 'ARTIST',
                     'performer_name': 'PERFORMER',
                     'composer_name': 'COMPOSER',
                     'conductor_name': 'CONDUCTOR',
                     'media': 'SOURCE MEDIUM',
                     'ISRC': 'ISRC',
                     'catalog': 'CATALOG',
                     'copyright': 'COPYRIGHT',
                     'publisher': 'PUBLISHER',
                     'year': 'DATE',
                     'album_number': 'DISCNUMBER',
                     'album_total': 'DISCTOTAL',
                     'comment': 'COMMENT'}

    ITEM_MAP = dict(map(reversed, ATTRIBUTE_MAP.items()))

    def __init__(self, vorbis_data, vendor_string=u""):
        """Initialized with a key->[value1,value2] dict.

        keys are generally upper case.
        values are unicode string.
        vendor_string is an optional unicode string."""

        dict.__init__(self, [(key.upper(), values)
                            for (key, values) in vorbis_data.items()])
        self.vendor_string = vendor_string

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.upper(), value)

    def __getattr__(self, key):
        if (key == 'track_number'):
            match = re.match(r'^\d+$',
                             self.get('TRACKNUMBER', [u''])[0])
            if (match):
                return int(match.group(0))
            else:
                match = re.match('^(\d+)/\d+$',
                                 self.get('TRACKNUMBER', [u''])[0])
                if (match):
                    return int(match.group(1))
                else:
                    return 0
        elif (key == 'track_total'):
            match = re.match(r'^\d+$',
                             self.get('TRACKTOTAL', [u''])[0])
            if (match):
                return int(match.group(0))
            else:
                match = re.match('^\d+/(\d+)$',
                                 self.get('TRACKNUMBER', [u''])[0])
                if (match):
                    return int(match.group(1))
                else:
                    return 0
        elif (key == 'album_number'):
            match = re.match(r'^\d+$',
                             self.get('DISCNUMBER', [u''])[0])
            if (match):
                return int(match.group(0))
            else:
                match = re.match('^(\d+)/\d+$',
                                 self.get('DISCNUMBER', [u''])[0])
                if (match):
                    return int(match.group(1))
                else:
                    return 0
        elif (key == 'album_total'):
            match = re.match(r'^\d+$',
                             self.get('DISCTOTAL', [u''])[0])
            if (match):
                return int(match.group(0))
            else:
                match = re.match('^\d+/(\d+)$',
                                 self.get('DISCNUMBER', [u''])[0])
                if (match):
                    return int(match.group(1))
                else:
                    return 0
        elif (key in self.ATTRIBUTE_MAP):
            return self.get(self.ATTRIBUTE_MAP[key], [u''])[0]
        elif (key in MetaData.__FIELDS__):
            return u''
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __delattr__(self, key):
        if (key == 'track_number'):
            track_number = self.get('TRACKNUMBER', [u''])[0]
            if (re.match(r'^\d+$', track_number)):
                del(self['TRACKNUMBER'])
            elif (re.match('^\d+/(\d+)$', track_number)):
                self['TRACKNUMBER'] = u"0/%s" % (
                    re.match('^\d+/(\d+)$', track_number).group(1))
        elif (key == 'track_total'):
            track_number = self.get('TRACKNUMBER', [u''])[0]
            if (re.match('^(\d+)/\d+$', track_number)):
                self['TRACKNUMBER'] = u"%s" % (
                    re.match('^(\d+)/\d+$', track_number).group(1))
            if ('TRACKTOTAL' in self):
                del(self['TRACKTOTAL'])
        elif (key == 'album_number'):
            album_number = self.get('DISCNUMBER', [u''])[0]
            if (re.match(r'^\d+$', album_number)):
                del(self['DISCNUMBER'])
            elif (re.match('^\d+/(\d+)$', album_number)):
                self['DISCNUMBER'] = u"0/%s" % (
                    re.match('^\d+/(\d+)$', album_number).group(1))
        elif (key == 'album_total'):
            album_number = self.get('DISCNUMBER', [u''])[0]
            if (re.match('^(\d+)/\d+$', album_number)):
                self['DISCNUMBER'] = u"%s" % (
                    re.match('^(\d+)/\d+$', album_number).group(1))
            if ('DISCTOTAL' in self):
                del(self['DISCTOTAL'])
        elif (key in self.ATTRIBUTE_MAP):
            if (self.ATTRIBUTE_MAP[key] in self):
                del(self[self.ATTRIBUTE_MAP[key]])
        elif (key in MetaData.__FIELDS__):
            pass
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    @classmethod
    def supports_images(cls):
        """Returns False."""

        #There's actually a (proposed?) standard to add embedded covers
        #to Vorbis Comments by base64 encoding them.
        #This strikes me as messy and convoluted.
        #In addition, I'd have to perform a special case of
        #image extraction and re-insertion whenever converting
        #to FlacMetaData.  The whole thought gives me a headache.

        return False

    def images(self):
        """Returns an empty list of Image objects."""

        return list()

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        if (key in self.ATTRIBUTE_MAP):
            if (key not in MetaData.__INTEGER_FIELDS__):
                self[self.ATTRIBUTE_MAP[key]] = [value]
            else:
                self[self.ATTRIBUTE_MAP[key]] = [unicode(value)]
        else:
            self.__dict__[key] = value

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to a VorbisComment object."""

        if ((metadata is None) or (isinstance(metadata, VorbisComment))):
            return metadata
        elif (metadata.__class__.__name__ == 'FlacMetaData'):
            return cls(vorbis_data=dict(metadata.vorbis_comment.items()),
                       vendor_string=metadata.vorbis_comment.vendor_string)
        else:
            values = {}
            for key in cls.ATTRIBUTE_MAP.keys():
                if (key in cls.__INTEGER_FIELDS__):
                    if (getattr(metadata, key) != 0):
                        values[cls.ATTRIBUTE_MAP[key]] = \
                            [unicode(getattr(metadata, key))]
                elif (getattr(metadata, key) != u""):
                    values[cls.ATTRIBUTE_MAP[key]] = \
                        [unicode(getattr(metadata, key))]

            return VorbisComment(values)

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        metadata = self.__class__.converted(metadata)
        if (metadata is None):
            return

        for (key, values) in metadata.items():
            if ((len(values) > 0) and
                (len(self.get(key, [])) == 0)):
                self[key] = values

    def __comment_name__(self):
        return u'Vorbis'

    #takes two (key,value) vorbiscomment pairs
    #returns cmp on the weighted set of them
    #(title first, then artist, album, tracknumber, ... , replaygain)
    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {"TITLE": 1,
                   "ALBUM": 2,
                   "TRACKNUMBER": 3,
                   "TRACKTOTAL": 4,
                   "DISCNUMBER": 5,
                   "DISCTOTAL": 6,
                   "ARTIST": 7,
                   "PERFORMER": 8,
                   "COMPOSER": 9,
                   "CONDUCTOR": 10,
                   "CATALOG": 11,
                   "PUBLISHER": 12,
                   "ISRC": 13,
                   "SOURCE MEDIUM": 14,
                   #"YEAR": 15,
                   "DATE": 16,
                   "COPYRIGHT": 17,
                   "REPLAYGAIN_ALBUM_GAIN": 19,
                   "REPLAYGAIN_ALBUM_PEAK": 19,
                   "REPLAYGAIN_TRACK_GAIN": 19,
                   "REPLAYGAIN_TRACK_PEAK": 19,
                   "REPLAYGAIN_REFERENCE_LOUDNESS": 20}
        return cmp((KEY_MAP.get(pair1[0].upper(), 18),
                    pair1[0].upper(),
                    pair1[1]),
                   (KEY_MAP.get(pair2[0].upper(), 18),
                    pair2[0].upper(),
                    pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key, values) in self.items():
            for value in values:
                pairs.append((key, value))

        pairs.sort(VorbisComment.__by_pair__)
        return pairs

    def build(self):
        """Returns this VorbisComment as a binary string."""

        comment = Con.Container(vendor_string=self.vendor_string,
                                framing=1,
                                value=[])

        for (key, values) in self.items():
            for value in values:
                if ((value != u"") and not
                    ((key in ("TRACKNUMBER", "TRACKTOTAL",
                              "DISCNUMBER", "DISCTOTAL")) and
                     (value == u"0"))):
                    comment.value.append("%s=%s" % (key,
                                                    value.encode('utf-8')))
        return self.VORBIS_COMMENT.build(comment)

    def clean(self, fixes_applied):
        """Returns a new VorbisComment object that's been cleaned of problems.

        Any fixes performed are appended to fixes_performed as Unicode."""

        fixed = {}

        for (key, values) in self.items():
            for value in values:
                #remove leading or trailing whitespace
                fix1 = value.rstrip()
                if (fix1 != value):
                    fixes_applied.append(
                        _(u"removed trailing whitespace from %(field)s") %
                        {"field":key.decode('ascii')})

                fix2 = fix1.lstrip()
                if (fix2 != fix1):
                    fixes_applied.append(
                        _(u"removed leading whitespace from %(field)s") %
                        {"field":key.decode('ascii')})

                #remove leading zeroes from numerical fields
                if (key in ("TRACKNUMBER", "TRACKTOTAL",
                            "DISCNUMBER", "DISCTOTAL")):
                    fix3 = fix2.lstrip(u"0")
                    if (fix3 != fix2):
                        fixes_applied.append(
                            _(u"removed leading zeroes from %(field)s") %
                            {"field":key.decode('ascii')})
                else:
                    fix3 = fix2

                #remove empty fields
                if (len(fix3) == 0):
                    fixes_applied.append(
                        _("removed empty field %(field)s") %
                        {"field":key.decode('ascii')})
                else:
                    fixed.setdefault(key, []).append(fix3)

        #FIXME - check vendor string for fixes?

        return self.__class__(fixed, self.vendor_string)


class VorbisComment2(MetaData):
    ATTRIBUTE_MAP = {'track_name':[u'TITLE'],
                     'track_number':[u'TRACKNUMBER'],
                     'track_total':[u'TRACKTOTAL',u'TOTALTRACKS'],
                     'album_name':[u'ALBUM'],
                     'artist_name':[u'ARTIST'],
                     'performer_name':[u'PERFORMER'],
                     'composer_name':[u'COMPOSER'],
                     'conductor_name':[u'CONDUCTOR'],
                     'media':[u'SOURCE MEDIUM'],
                     'ISRC':[u'ISRC'],
                     'catalog':[u'CATALOG'],
                     'copyright':[u'COPYRIGHT'],
                     'publisher':[u'PUBLISHER'],
                     'year':[u'DATE'],
                     'date':[],
                     'album_number':[u'DISCNUMBER'],
                     'album_total':[u'DISCTOTAL'],
                     'comment':[u'COMMENT']}

    UNSLASHED_FIELD = re.compile(r'(\d+)')
    SLASHED_FIELD = re.compile(r'(\d+)\s*/\s*(\d+)')

    SLASHED_FIELDS = {'track_number':(0, [u'TRACKNUMBER']),
                      'track_total':(1, [u'TRACKNUMBER']),
                      'album_number':(0, [u'DISCNUMBER']),
                      'album_total':(1, [u'DISCTOTAL'])}

    def __init__(self, comment_strings, vendor_string):
        """comment_strings is a list of unicode strings

        vendor_string is a unicode string"""

        self.__dict__["comment_strings"] = comment_strings
        self.__dict__["vendor_string"] = vendor_string

    def __repr__(self):
        return "VorbisComment2(%s, %s)" % \
            (repr(self.comment_strings), repr(self.vendor_string))

    def __getattr__(self, attr):
        #returns the first matching key for the given attribute
        #in our list of comment strings

        if (attr in self.SLASHED_FIELDS):
            #handle rare u'TRACKNUMBER=1/2' cases
            #which must always be numerical fields
            matching_slashed_fields = frozenset(self.SLASHED_FIELDS[attr][1])
            matching_unslashed_fields = frozenset(self.ATTRIBUTE_MAP[attr])

            for (key, value) in [comment.split(u"=", 1)
                                 for comment in self.comment_strings
                                 if (u"=" in comment)]:
                key = key.upper()

                #first, attempt to search for a slashed value, like:
                #u'TRACKNUMBER=1/2'
                #and return the appropriate side of the value as an int
                if (key in matching_slashed_fields):
                    slashed_value = self.SLASHED_FIELD.search(value)
                    if (slashed_value is not None):
                        return int(slashed_value.group(
                                self.SLASHED_FIELDS[attr][0] + 1))

                #then, attempt to search for an unslashed value, like:
                #u'TRACKNUMBER=1'
                #and return the int result
                if (key in matching_unslashed_fields):
                    unslashed_value = self.UNSLASHED_FIELD.search(value)
                    if (unslashed_value is not None):
                        return int(unslashed_value.group(1))

                #otherwise, continue through the list of fields
            else:
                return 0
        elif (attr in self.ATTRIBUTE_MAP):
            matching_fields = frozenset(self.ATTRIBUTE_MAP[attr])
            for (key, value) in [comment.split(u"=", 1)
                                 for comment in self.comment_strings
                                 if (u"=" in comment)]:
                if (key.upper() in matching_fields):
                    return value
            else:
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
            #handle rare u'TRACKNUMBER=1/2' cases
            #which must always be numerical fields
            matching_slashed_fields = frozenset(self.SLASHED_FIELDS[attr][1])
            matching_unslashed_fields = frozenset(self.ATTRIBUTE_MAP[attr])

            updated_comment_strings = []
            matched = False

            for comment_string in self.__dict__["comment_strings"]:
                if ((not matched) and (u"=" in comment_string)):
                    (key, cur_value) = comment_string.split(u"=", 1)
                    key = key.upper()

                    #first, attempt to search for a slashed value, like:
                    #u'TRACKNUMBER=1/2'
                    #and update the appropriate side of the value
                    #while preserving the other side
                    if ((key in matching_slashed_fields) and
                        (self.SLASHED_FIELD.search(cur_value) is not None)):
                        slashed_value = self.SLASHED_FIELD.search(cur_value)
                        if (self.SLASHED_FIELDS[attr][0] == 0):
                            #update left side, preserve right side
                            updated_comment_strings.append(
                                "%s=%s/%s" % (key,
                                              value,
                                              slashed_value.group(2)))
                        else:
                            #update right side, preserve left side
                            updated_comment_strings.append(
                                "%s=%s/%s" % (key,
                                              slashed_value.group(1),
                                              value))
                        matched = True

                    #then, attempt to search for an unslashed value, like:
                    #u'TRACKNUMBER=1'
                    #and update the value outright
                    elif ((key in matching_unslashed_fields) and
                          (self.UNSLASHED_FIELD.search(cur_value) is not None)):
                        updated_comment_strings.append(
                            u"%s=%d" % (self.ATTRIBUTE_MAP[attr][0], value))
                        matched = True

                    #otherwise, continue porting the list of fields
                    else:
                        updated_comment_strings.append(comment_string)
                else:
                    updated_comment_strings.append(comment_string)
            else:
                #no matching fields, so append a new one as unslashed
                if (not matched):
                    updated_comment_strings.append(
                        u"%s=%d" %  (self.ATTRIBUTE_MAP[attr][0], value))

            self.__dict__["comment_strings"] = updated_comment_strings

        #plain text fields are easier,
        #but still require checking a set of aliased key names
        elif (attr in self.ATTRIBUTE_MAP):
            matching_fields = frozenset(self.ATTRIBUTE_MAP[attr])
            updated_comment_strings = []
            matched = False

            for comment_string in self.__dict__["comment_strings"]:
                if ((not matched) and (u"=" in comment_string)):
                    key = comment_string.split(u"=", 1)[0].upper()
                    if (key in matching_fields):
                        #update the first matching field
                        updated_comment_strings.append(
                            u"%s=%s" % (key, value))
                        matched = True
                    else:
                        updated_comment_strings.append(comment_string)
                else:
                    updated_comment_strings.append(comment_string)
            else:
                #no matching fields, so append a new one
                if (not matched):
                    updated_comment_strings.append(
                        u"%s=%s" % (self.ATTRIBUTE_MAP[attr][0], value))

            self.__dict__["comment_strings"] = updated_comment_strings
        else:
            self.__dict__[attr] = value

    def __delattr__(self, attr):
        #deletes all matching keys for the given attribute
        #in our list of comment strings

        if (attr in self.SLASHED_FIELDS):
            #handle rate u'TRACKNUMBER=1/2' cases
            #which must always be numerical fields
            matching_slashed_fields = frozenset(self.SLASHED_FIELDS[attr][1])
            matching_unslashed_fields = frozenset(self.ATTRIBUTE_MAP[attr])

            updated_comment_strings = []

            for comment_string in self.__dict__["comment_strings"]:
                if (u"=" in comment_string):
                    (key, cur_value) = comment_string.split("=", 1)
                    key = key.upper()

                    #first attempt to search for a slashed value, like
                    #u'TRACKNUMBER=1/2'
                    #and delete the appropriate side of the value
                    #while preserving the other side
                    if ((key in matching_slashed_fields) and
                        (self.SLASHED_FIELD.search(cur_value) is not None)):
                        slashed_value = self.SLASHED_FIELD.search(cur_value)
                        if (self.SLASHED_FIELDS[attr][0] == 0):
                            #zero out left side, preserve right side
                            updated_comment_strings.append(
                                "%s=0/%s" % (key, slashed_value.group(2)))
                        else:
                            #preserve left side, remove right side
                            #so long as the left side is non-zero
                            try:
                                if (int(slashed_value.group(1)) != 0):
                                    updated_comment_strings.append(
                                        "%s=%s" % (key, slashed_value.group(1)))
                            except ValueError:
                                updated_comment_strings.append(
                                    "%s=%s" % (key, slashed_value.group(1)))

                    #then, attempt to search for an unslashed value, like
                    #u'TRACKNUMBER=1'
                    #and delete the value outright
                    elif (key in matching_unslashed_fields):
                        continue

                    #otherwise, continue to port unmatching values
                    else:
                        updated_comment_strings.append(comment_string)
                else:
                    updated_comment_strings.append(comment_string)

            self.__dict__["comment_strings"] = updated_comment_strings

        elif (attr in self.ATTRIBUTE_MAP):
            matching_fields = frozenset(self.ATTRIBUTE_MAP[attr])
            updated_comment_strings = []

            for comment_string in self.__dict__["comment_strings"]:
                if (u"=" in comment_string):
                    if (comment_string.split(u"=", 1)[0].upper()
                        not in matching_fields):
                        updated_comment_strings.append(comment_string)
                else:
                    updated_comment_strings.append(comment_string)

            self.__dict__["comment_strings"] = updated_comment_strings
        else:
            try:
                del(self.__dict__[attr])
            except KeyError:
                raise AttributeError(attr)

    def __comment_name__(self):
        return u"VorbisComment"

    def __eq__(self, metadata):
        raise NotImplementedError()

    @classmethod
    def converted(cls, metadata):
        """Converts metadata from another class to VorbisComment"""

        if ((metadata is None) or (isinstance(metadata, VorbisComment2))):
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
                            "%s=%s" % (cls.ATTRIBUTE_MAP[attr][0],
                                       getattr(metadata, attr)))
                else:
                    if (getattr(metadata, attr) > 0):
                        comment_strings.append(
                            "%s=%s" % (cls.ATTRIBUTE_MAP[attr][0],
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
            metadata = self.__class__.converted(metadata)

            #build a field -> frozenset dict
            #such as {u"TRACKTOTAL":frozenset([u"TRACKTOTAL",u"TOTALTRACKS"]),
            #         u"TOTALTRACKS":frozenset([u"TRACKTOTAL",u"TOTALTRACKS"])}
            #for ensuring we don't merge a duplicate field
            #simply because it has an aliased name
            field_aliases = {}
            for fields in self.ATTRIBUTE_MAP.values():
                field_set = frozenset(fields)
                for field in fields:
                    field_aliases[field] = field_set

            #FIXME - merge #/# fields properly

            #build a set of all in-use fields
            #using the aliasing dict
            #so that all the "track_total" variants are present, for example
            current_fields = set([])
            for comment_string in self.comment_strings:
                if (u"=" in comment_string):
                    key = comment_string.split(u"=", 1)[0]
                    current_fields |= field_aliases.get(key, set([key]))

            #finally, merge in all fields from the new metadata
            #that aren't in our set of in-use fields
            for comment_string in metadata.comment_strings:
                if ((u"=" in comment_string) and
                    (comment_string.split(u"=", 1)[0] not in current_fields)):
                    self.comment_strings.append(comment_string)

    def clean(self, fixes_performed):
        """Returns a new MetaData object that's been cleaned of problems."""

        raise NotImplementedError()
