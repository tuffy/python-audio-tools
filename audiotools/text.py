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

"""a text strings module"""


#ReplayGain
RG_ADDING_REPLAYGAIN = \
    u"Adding ReplayGain"

RG_APPLYING_REPLAYGAIN = \
    u"Applying ReplayGain"

RG_ADDING_REPLAYGAIN_WAIT = \
    u"Adding ReplayGain metadata.  This may take some time."

RG_APPLYING_REPLAYGAIN_WAIT = \
    u"Applying ReplayGain.  This may take some time."

RG_REPLAYGAIN_ADDED = \
    u"ReplayGain added"

RG_REPLAYGAIN_APPLIED = \
    u"ReplayGain applied"


#Labels
LAB_PICTURE = \
    u"Picture"

LAB_T_OPTIONS = \
    u"Please use the -t option to specify %s"


#Compression settings
COMP_FLAC_0 = \
    u"least amount of compresson, fastest compression speed"
COMP_FLAC_8 = \
    u"most amount of compression, slowest compression speed"


#Errors
ERR_UNSUPPORTED_CHANNEL_MASK = \
    u"Unable to write \"%(target_filename)s\" " + \
    u"with channel assignment \"%(assignment)s\""

ERR_UNSUPPORTED_BITS_PER_SAMPLE = \
    u"Unable to write \"%(target_filename)s\" " + \
    u"with %(bps)d bits per sample"

ERR_UNSUPPORTED_CHANNEL_COUNT = \
    u"Unable to write \"%(target_filename)s\" " + \
    u"with %(channels)d channel input"

ERR_DUPLICATE_FILE = \
    u"File \"%s\" included more than once"

ERR_OPEN_IOERROR = \
    u"Unable to open \"%s\""

ERR_UNSUPPORTED_AUDIO_TYPE = \
    u"Unsupported audio type \"%s\""

ERR_AMBIGUOUS_AUDIO_TYPE = \
    u"Ambiguous suffix type \"%s\""

ERR_NO_PCMREADERS = \
    u"You must have at least 1 PCMReader"

ERR_PICTURES_UNSUPPORTED = \
    u"This MetaData type does not support images"

ERR_UNKNOWN_FIELD = \
    u"Unknown field \"%s\" in file format"

ERR_FOREIGN_METADATA = \
    u"metadata not from audio file"

ERR_AIFF_NOT_AIFF = \
    u"Not an AIFF file"

ERR_AIFF_INVALID_AIFF = \
    u"Invalid AIFF file"

ERR_AIFF_INVALID_CHUNK_ID = \
    u"Invalid AIFF chunk ID"

ERR_AIFF_INVALID_CHUNK = \
    u"Invalid AIFF chunk"

ERR_AIFF_MULTIPLE_COMM_CHUKNS = \
    u"multiple COMM chunks found"

ERR_AIFF_PREMATURE_SSND_CHUNK = \
    u"SSND chunk found before fmt"

ERR_AIFF_MULTIPLE_SSND_CHUNKS = \
    u"multiple SSND chunks found"

ERR_AIFF_TRUNCATED_CHUNK = \
    u"truncated %s chunk found"

ERR_AIFF_NO_COMM_CHUNK = \
    u"COMM chunk not found"

ERR_AIFF_NO_SSND_CHUNK = \
    u"SSND chunk not found"

ERR_APE_INVALID_HEADER = \
    u"Invalid Monkey's Audio header"

ERR_AU_INVALID_HEADER = \
    u"Invalid Sun AU header"

ERR_AU_UNSUPPORTED_FORMAT = \
    u"Unsupported Sun AU format"

ERR_CUE_INVALID_TOKEN = \
    u"Invalid token at char %d"

ERR_CUE_ERROR = \
    u"%(error)s at line %(line)d"

ERR_CUE_INVALID_TRACK_NUMBER = \
    u"Invalid track number"

ERR_CUE_INVALID_TRACK_TYPE = \
    u"Invalid track type"

ERR_CUE_MISSING_VALUE = \
    u"Missing value"

ERR_CUE_EXCESS_DATA = \
    u"Excess data"

ERR_CUE_MISSING_FILENAME = \
    u"Missing filename"

ERR_CUE_MISSING_FILETYPE = \
    u"Missing file type"

ERR_CUE_INVALID_TAG = \
    u"Invalid tag %(tag)s at line %(line)d"

ERR_CUE_INVALID_DATA = \
    u"Invalid data"

ERR_CUE_INVALID_FLAG = \
    u"Invalid flag"

ERR_CUE_INVALID_TIMESTAMP = \
    u"Invalid timestamp"

ERR_CUE_INVALID_INDEX_NUMBER = \
    u"Invalid index number"

ERR_CUE_MISSING_TAG = \
    u"Missing tag at line %d"

ERR_CUE_IOERROR = \
    u"Unable to read cuesheet"

ERR_CUE_INVALID_FORMAT = \
    u"Cuesheet not formatted for disc images"

ERR_DVDA_IOERROR_AUDIO_TS = \
    u"unable to open AUDIO_TS.IFO"

ERR_DVDA_INVALID_AUDIO_TS = \
    u"invalid AUDIO_TS.IFO"

ERR_DVDA_IOERROR_ATS = \
    u"unable to open ATS_%2.2d_0.IFO"

ERR_DVDA_INVALID_ATS = \
    u"invalid ATS_%2.2d_0.IFO"

ERR_DVDA_INVALID_SECTOR_POINTER = \
    u"invalid sector pointer"

ERR_DVDA_NO_TRACK_SECTOR = \
    u"unable to find track sector in AOB files"

ERR_DVDA_INVALID_AOB_SYNC = \
    u"invalid AOB sync bytes"

ERR_DVDA_INVALID_AOB_MARKER = \
    u"invalid AOB marker bits"

ERR_DVDA_INVALID_AOB_START = \
    u"invalid AOB packet start code"

ERR_FLAC_RESERVED_BLOCK = \
    u"reserved metadata block type %d"

ERR_FLAC_INVALID_BLOCK = \
    u"invalid metadata block type"

ERR_FLAC_INVALID_FILE = \
    u"Invalid FLAC file"

ERR_OGG_INVALID_MAGIC_NUMBER = \
    u"invalid Ogg magic number"

ERR_OGG_INVALID_VERSION = \
    u"invalid Ogg version"

ERR_OGGFLAC_INVALID_PACKET_BYTE = \
    u"invalid packet byte"

ERR_OGGFLAC_INVALID_OGG_SIGNATURE = \
    u"invalid Ogg signature"

ERR_OGGFLAC_INVALID_MAJOR_VERSION = \
    u"invalid major version"

ERR_OGGFLAC_INVALID_MINOR_VERSION = \
    u"invalid minor version"

ERR_OGGFLAC_VALID_FLAC_SIGNATURE = \
    u"invalid FLAC signature"

#Cleaning messages

CLEAN_REMOVE_DUPLICATE_TAG = \
    u"removed duplicate tag %(field)s"

CLEAN_REMOVE_TRAILING_WHITESPACE = \
    u"removed trailing whitespace from %(field)s"

CLEAN_REMOVE_LEADING_WHITESPACE = \
    u"removed leading whitespace from %(field)s"

CLEAN_REMOVE_EMPTY_TAG = \
    u"removed empty field %(field)s"

CLEAN_FIX_TAG_FORMATTING = \
    u"fixed formatting for %(field)s"

CLEAN_FIX_IMAGE_FIELDS = \
    u"fixed embedded image metadata fields"

CLEAN_AIFF_MULTIPLE_COMM_CHUNKS = \
    u"removed duplicate COMM chunk"

CLEAN_AIFF_REORDERED_SSND_CHUNK = \
    u"moved COMM chunk after SSND chunk"

CLEAN_AIFF_MULTIPLE_SSND_CHUNKS = \
    u"removed duplicate SSND chunk"

CLEAN_FLAC_REORDERED_STREAMINFO = \
    u"moved STREAMINFO to first block"

CLEAN_FLAC_MULITPLE_STREAMINFO = \
    u"removing redundant STREAMINFO block"

CLEAN_FLAC_MULTIPLE_VORBISCOMMENT = \
    u"removing redundant VORBIS_COMMENT block"

CLEAN_FLAC_MULTIPLE_SEEKTABLE = \
    u"removing redundant SEEKTABLE block"

CLEAN_FLAC_MULTIPLE_CUESHEET = \
    u"removing redundant CUESHEET block"

CLEAN_FLAC_UNDEFINED_BLOCK = \
    u"removing undefined block"

CLEAN_FLAC_REMOVE_SEEKPOINTS = \
    u"removed empty seekpoints from seektable"

CLEAN_FLAC_REORDER_SEEKPOINTS = \
    u"reordered seektable to be in ascending order"

CLEAN_FLAC_REMOVE_ID3V2 = \
    u"removed ID3v2 tag"

CLEAN_FLAC_REMOVE_ID3V1 = \
    u"removed ID3v1 tag"

CLEAN_FLAC_POPULATE_MD5 = \
    u"populated empty MD5SUM"

CLEAN_FLAC_ADD_CHANNELMASK = \
    u"added WAVEFORMATEXTENSIBLE_CHANNEL_MASK"

CLEAN_FLAC_FIX_SEEKTABLE = \
    u"fixed invalid SEEKTABLE"

#Channel names
MASK_FRONT_LEFT = \
    u"front left"
MASK_FRONT_RIGHT = \
    u"front right"
MASK_FRONT_CENTER = \
    u"front center"
MASK_LFE = \
    u"low frequency"
MASK_BACK_LEFT = \
    u"back left"
MASK_BACK_RIGHT = \
    u"back right"
MASK_FRONT_RIGHT_OF_CENTER = \
    u"front right of center"
MASK_FRONT_LEFT_OF_CENTER = \
    u"front left of center"
MASK_BACK_CENTER = \
    u"back center"
MASK_SIDE_LEFT = \
    u"side left"
MASK_SIDE_RIGHT = \
    u"side right"
MASK_TOP_CENTER = \
    u"top center"
MASK_TOP_FRONT_LEFT = \
    u"top front left"
MASK_TOP_FRONT_CENTER = \
    u"top front center"
MASK_TOP_FRONT_RIGHT = \
    u"top front right"
MASK_TOP_BACK_LEFT = \
    u"top back left"
MASK_TOP_BACK_CENTER = \
    u"top back center"
MASK_TOP_BACK_RIGHT = \
    u"top back right"
