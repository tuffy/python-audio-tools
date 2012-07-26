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

#Utility usage
USAGE_CD2TRACK = \
    u"%prog [options] [track #] [track #] ..."

USAGE_CDINFO = \
    u"%prog [options]"

USAGE_CDPLAY = \
    u"%prog [track 1] [track 2] ..."

USAGE_TRACKPLAY = \
    u"%prog [track 1] [track 2] ..."

USAGE_COVERDUMP = \
    u"%prog [-d directory] <track>"

USAGE_COVERVIEW = \
    u"%prog [OPTIONS] [track]"

USAGE_DVDA2TRACK = \
    u"%prog [options] [track #] [track #] ..."

USAGE_DVDAINFO = \
    u"%prog [options]"

USAGE_TRACK2CD = \
    u"%prog [options] <track 1> [track 2] ..."

USAGE_TRACK2TRACK = \
    u"%prog [options] <track 1> [track 2] ..."

USAGE_TRACKCAT = \
    u"%prog [options] [-o output] <track 1> [track 2] ..."

USAGE_TRACKCMP = \
    u"%prog <file 1> <file 2>"

USAGE_TRACKCMP_CDIMAGE = \
    u"<CD image> <track 1> <track 2> ..."

USAGE_TRACKCMP_FILES = \
    u"<track 1> <track 2>"

USAGE_TRACKSPLIT = \
    u"%prog [options] [-d directory] <track>"

USAGE_TRACKINFO = \
    u"%prog [options] <track 1> [track 2] ..."

USAGE_TRACKLENGTH = \
    u"%prog <track 1> [track 2] ..."

#Utility Options
OPT_VERBOSE = \
    u"the verbosity level to execute at"
OPT_TYPE = \
    u"the type of audio track to create"
OPT_QUALITY = \
    u"the quality to store audio tracks at"
OPT_DIR = \
    u"the directory to store new audio tracks"
OPT_DIR_IMAGES = \
    u"the directory to store extracted images"
OPT_FORMAT = \
    u"the format string for new filenames"
OPT_NO_MUSICBRAINZ = \
    u"do not query MusicBrainz for metadata"
OPT_NO_FREEDB = \
    u"do not query FreeDB for metadata"
OPT_INTERACTIVE_METADATA = \
    u"edit metadata in interactive mode"
OPT_INTERACTIVE_PLAY = \
    u"play in interactive mode"
OPT_OUTPUT_PLAY = \
    u"the method to play audio (choose from: %s)"
OPT_OUTPUT_TRACK2TRACK = \
    u"output filename to use, overriding default and -d"
OPT_OUTPUT_TRACKCAT = \
    u"the output file"
OPT_DEFAULT = \
    u"when multiple choices are available, " + \
    u"select the first one automatically"
OPT_ALBUM_NUMBER = \
    u"the album number of this disc, if it is one of a series of albums"
OPT_ALBUM_TOTAL = \
    u"the total albums of this disc\'s set, if it is one of a series of albums"
OPT_REPLAY_GAIN = \
    u"add ReplayGain metadata to newly created tracks"
OPT_NO_REPLAY_GAIN = \
    u"do not add ReplayGain metadata in newly created tracks"
OPT_PLAYBACK_TRACK_GAIN = \
    u"apply track ReplayGain during playback, if present"
OPT_PLAYBACK_ALBUM_GAIN = \
    u"apply album ReplayGain during playback, if present"
OPT_SHUFFLE = \
    u"shuffle tracks"
OPT_PREFIX = \
    u"add a prefix to the output image"
OPT_NO_GTK = \
    u"don't use PyGTK for GUI"
OPT_NO_TKINTER = \
    u"don't use Tkinter for GUI"
OPT_AUDIO_TS = \
    u"location of AUDIO_TS directory"
OPT_DVDA_TITLE = \
    u"DVD-Audio title number to extract tracks from"
OPT_TRACK_START = \
    u"the starting track number of the title being extracted"
OPT_TRACK_TOTAL = \
    u"the total number of tracks, if the extracted title is only a subset"
OPT_SPEED = \
    u"the speed to burn the CD at"
OPT_CUESHEET_TRACK2CD = \
    u"the cuesheet to use for writing tracks"
OPT_JOINT = \
    u"the maximum number of processes to run at a time"
OPT_THUMBNAIL = \
    u"convert embedded images to smaller thumbnails during conversion"
OPT_CUESHEET_TRACKCAT = \
    u"a cuesheet to embed in the output file"
OPT_CUESHEET_TRACKSPLIT = \
    u"the cuesheet to use for splitting track"
OPT_NO_SUMMARY = \
    u"suppress summary output"

OPT_CAT_EXTRACTION = u"Extraction Options"
OPT_CAT_CD_LOOKUP = u"CD Lookup Options"
OPT_CAT_DVDA_LOOKUP = u"DVD-A Lookup Options"
OPT_CAT_METADATA = u"Metadata Options"
OPT_CAT_CONVERSION = u"Conversion Options"
OPT_CAT_ENCODING = u"Encoding Options"

#MetaData Fields
METADATA_TRACK_NAME = u"Track Name"
METADATA_TRACK_NUMBER = u"Track Number"
METADATA_TRACK_TOTAL = u"Track Total"
METADATA_ALBUM_NAME = u"Album Name"
METADATA_ARTIST_NAME = u"Artist Name"
METADATA_PERFORMER_NAME = u"Performer Name"
METADATA_COMPOSER_NAME = u"Composer Name"
METADATA_CONDUCTOR_NAME = u"Conductor Name"
METADATA_MEDIA = u"Media"
METADATA_ISRC = u"ISRC"
METADATA_CATALOG = u"Catalog Number"
METADATA_COPYRIGHT = u"Copyright"
METADATA_PUBLISHER = u"Publisher"
METADATA_YEAR = u"Release Year"
METADATA_DATE = u"Recording Date"
METADATA_ALBUM_NUMBER = u"Album Number"
METADATA_ALBUM_TOTAL = u"Album Total"
METADATA_COMMENT = u"Comment"


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
LAB_ENCODE = \
    u"%(source)s -> %(destination)s"

LAB_PICTURE = \
    u"Picture"

LAB_T_OPTIONS = \
    u"Please use the -t option to specify %s"

LAB_AVAILABLE_COMPRESSION_TYPES = \
    u"Available compression types for %s:"

LAB_CD2TRACK_PROGRESS = \
    u"track %(track_number)2.2d -> %(filename)s"

LAB_CD2TRACK_LOG = \
    u"Rip log : "

LAB_TOTAL_TRACKS = \
    u"Total Tracks"

LAB_TOTAL_LENGTH = \
    u"Total Length"

LAB_TRACK_LENGTH = \
    u"%d:%2.2d"

LAB_TRACK_LENGTH_FRAMES = \
    u"%2d:%2.2d (%d frames)"

LAB_FREEDB_ID = \
    u"FreeDB disc ID"

LAB_MUSICBRAINZ_ID = \
    u"MusicBrainz disc ID"

LAB_CDINFO_LENGTH = \
    u"Length"

LAB_CDINFO_FRAMES = \
    u"Frames"

LAB_CDINFO_OFFSET = \
    u"Offset"

LAB_PLAY_BUTTON = \
    u"Play"

LAB_PAUSE_BUTTON = \
    u"Pause"

LAB_NEXT_BUTTON = \
    u"Next"

LAB_PREVIOUS_BUTTON = \
    u"Prev"

LAB_PLAY_STATUS = \
    u"%(count)d tracks, %(min)d:%(sec)2.2d minutes"

LAB_PLAY_STATUS_1 = \
    u"%(count)d track, %(min)d:%(sec)2.2d minutes"

LAB_PLAY_TRACK = \
    u"Track"

LAB_CLOSE = \
    u"Close"

LAB_TRACK = \
    u"track"

LAB_X_OF_Y = \
    u"%d / %d"

LAB_CHOOSE_FILE = \
    u"Choose an audio file"

LAB_COVERVIEW_ABOUT = \
    u"A viewer for displaying images embedded in audio files."

LAB_AUDIOTOOLS_URL = \
    u"http://audiotools.sourceforge.net"

LAB_BYTE_SIZE = \
    u"%d bytes"

LAB_DIMENSIONS = \
    u"%d \u00D7 %d"

LAB_BITS_PER_PIXEL = \
    u"%d bits"

LAB_DVDA_TRACK = \
    u"title %(title_number)d - track %(track_number)2.2d"

LAB_DVDA_TITLE = \
    u"Title %d"

LAB_DVDA_TRACKS = \
    u" (%d tracks)"

LAB_DVDA_TITLE_INFO = \
    u"%(minutes)2.2d:%(seconds)2.2d " + \
    u"%(channels)dch %(rate)dHz %(bits)d-bit " + \
    u"%(type)s"

LAB_DVDAINFO_TITLE = \
    u"Title"

LAB_DVDAINFO_TRACK = \
    u"Track"

LAB_DVDAINFO_LENGTH = \
    u"Length"

LAB_DVDAINFO_FILENAME = \
    u"Filename"

LAB_DVDAINFO_STARTSECTOR = \
    u"Start Sector"

LAB_DVDAINFO_ENDSECTOR = \
    u"End Sector"

LAB_DVDAINFO_TICKS = \
    u"PTS Ticks"

LAB_CONVERTING_FILE = \
    u"Converting audio file"

LAB_TRACKCMP_CMP = \
    u"%(file1)s <> %(file2)s"

LAB_TRACKCMP_OK = \
    u"OK"

LAB_TRACKCMP_MISMATCH = \
    u"differ at PCM frame %(frame_number)d"

LAB_TRACKCMP_TYPE_MISMATCH = \
    u"must be either files or directories"

LAB_TRACKCMP_ERROR = \
    u"error"

LAB_TRACKCMP_MISSING = \
    u"missing"

LAB_TRACKCMP_RESULTS = \
    u"Results:"

LAB_TRACKCMP_HEADER_SUCCESS = \
    u"success"

LAB_TRACKCMP_HEADER_FAILURE = \
    u"failure"

LAB_TRACKCMP_HEADER_TOTAL = \
    u"total"

LAB_TRACKINFO_BITRATE = \
    u"%(bitrate)4.4s kbps: %(filename)s"

LAB_TRACKINFO_PERCENTAGE = \
    u"%(percentage)3.3s%%: %(filename)s"

LAB_TRACKINFO_ATTRIBS = \
    u"%(minutes)2.2d:%(seconds)2.2d " + \
    u"%(channels)dch %(rate)dHz %(bits)d-bit: %(filename)s"

LAB_TRACKINFO_REPLAYGAIN = \
    u"ReplayGain:"

LAB_TRACKINFO_TRACK_GAIN = \
    u"Track Gain : "

LAB_TRACKINFO_TRACK_PEAK = \
    u"Track Peak : "

LAB_TRACKINFO_ALBUM_GAIN = \
    u"Album Gain : "

LAB_TRACKINFO_ALBUM_PEAK = \
    u"Album Peak : "

LAB_TRACKINFO_CUESHEET = \
    u"Cuesheet:"

LAB_TRACKINFO_CUESHEET_TRACK = \
    u"track"

LAB_TRACKINFO_CUESHEET_LENGTH = \
    u"length"

LAB_TRACKINFO_CUESHEET_ISRC = \
    u"ISRC"

LAB_TRACKINFO_CHANNELS = \
    u"Assigned Channels:"

LAB_TRACKINFO_CHANNEL = \
    u"channel %(channel_number)d - %(channel_name)s"

LAB_TRACKINFO_UNDEFINED = \
    u"undefined"

LAB_TRACKLENGTH = \
    u"%(hours)d:%(minutes)2.2d:%(seconds)2.2d"

#Compression settings
COMP_FLAC_0 = \
    u"least amount of compresson, fastest compression speed"
COMP_FLAC_8 = \
    u"most amount of compression, slowest compression speed"

COMP_NERO_LOW = \
    u"lowest quality, corresponds to neroAacEnc -q 0.4"

COMP_NERO_HIGH = \
    u"highest quality, corresponds to neroAacEnc -q 1"

COMP_LAME_0 = \
    u"high quality, larger files, corresponds to lame's -V0"

COMP_LAME_6 = \
    u"lower quality, smaller files, corresponds to lame's -V6"

COMP_LAME_MEDIUM = \
    u"corresponds to lame's --preset medium"

COMP_LAME_STANDARD = \
    u"corresponds to lame's --preset standard"

COMP_LAME_EXTREME = \
    u"corresponds to lame's --preset extreme"

COMP_LAME_INSANE = \
    u"corresponds to lame's --preset insane"

COMP_TWOLAME_64 = \
    u"total bitrate of 64kbps"

COMP_TWOLAME_384 = \
    u"total bitrate of 384kbps"

COMP_VORBIS_0 = \
    u"very low quality, corresponds to oggenc -q 0"

COMP_VORBIS_10 = \
    u"very high quality, corresponds to oggenc -q 10"

COMP_WAVPACK_VERYFAST = \
    u"fastest encode/decode, worst compression"

COMP_WAVPACK_VERYHIGH = \
    u"slowest encode/decode, best compression"

#Errors
ERR_1_FILE_REQUIRED = \
    u"You must specify exactly 1 supported audio file"

ERR_FILES_REQUIRED = \
    u"You must specify at least 1 supported audio file"

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

ERR_OUTPUT_IS_INPUT = \
    u"\"%s\" cannot be both input and output file"

ERR_OPEN_IOERROR = \
    u"Unable to open \"%s\""

ERR_ENCODING_ERROR = \
    u"Unable to write \"%s\""

ERR_UNSUPPORTED_AUDIO_TYPE = \
    u"Unsupported audio type \"%s\""

ERR_UNSUPPORTED_FILE = \
    u"Unsupported File '%s'"

ERR_INVALID_FILE = \
    u"Invalid File '%s'"

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

ERR_OGG_CHECKSUM_MISMATCH = \
    u"Ogg page checksum mismatch"

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

ERR_IMAGE_UNKNOWN_TYPE = \
    u"unknown image type"

ERR_IMAGE_INVALID_JPEG_MARKER = \
    u"Invalid JPEG segment marker"

ERR_IMAGE_INVALID_PNG = \
    u"Invalid PNG"

ERR_IMAGE_INVALID_PLTE = \
    u"Invalid PLTE chunk length"

ERR_IMAGE_INVALID_BMP = \
    u"Invalid BMP"

ERR_IMAGE_INVALID_TIFF = \
    u"Invalid TIFF"

ERR_M4A_IOERROR = \
    u"I/O error opening M4A file"

ERR_M4A_MISSING_MDIA = \
    u"Required mdia atom not found"

ERR_M4A_MISSING_STSD = \
    u"Required stsd atom not found"

ERR_M4A_INVALID_MP4A = \
    u"Invalid mp4a atom"

ERR_M4A_MISSING_MDHD = \
    u"Required mdhd atom not found"

ERR_M4A_UNSUPPORTED_MDHD = \
    u"Unsupported mdhd version"

ERR_M4A_INVALID_MDHD = \
    u"Invalid mdhd atom"

ERR_M4A_INVALID_LEAF_ATOMS = \
    u"leaf atoms must be a list"

ERR_ALAC_IOERROR = \
    u"I/O error opening ALAC file"

ERR_ALAC_INVALID_ALAC = \
    u"Invalid alac atom"

ERR_MP3_FRAME_NOT_FOUND = \
    u"MP3 frame not found"

ERR_MP3_INVALID_SAMPLE_RATE = \
    u"Invalid sample rate"

ERR_MP3_INVALID_BIT_RATE = \
    u"Invalid bit rate"

ERR_TOC_NO_HEADER = \
    u"No CD_DA TOC header found"

ERR_VORBIS_INVALID_TYPE = \
    u"invalid Vorbis type"

ERR_VORBIS_INVALID_HEADER = \
    u"invalid Vorbis header"

ERR_VORBIS_INVALID_VERSION = \
    u"invalid Vorbis version"

ERR_VORBIS_INVALID_FRAMING_BIT = \
    u"invalid framing bit"

ERR_WAV_NOT_WAVE = \
    u"Not a RIFF WAVE file"

ERR_WAV_INVALID_WAVE = \
    u"Invalid RIFF WAVE file"

ERR_WAV_NO_DATA_CHUNK = \
    u"data chunk not found"

ERR_WAV_INVALID_CHUNK = \
    u"Invalid RIFF WAVE chunk ID"

ERR_WAV_MULTIPLE_FMT = \
    u"multiple fmt chunks found"

ERR_WAV_PREMATURE_DATA = \
    u"data chunk found before fmt"

ERR_WAV_MULTIPLE_DATA = \
    u"multiple data chunks found"

ERR_WAV_TRUNCATED_CHUNK = \
    u"truncated %s chunk found"

ERR_WAV_NO_FMT_CHUNK = \
    u"fmt chunk not found"

ERR_WAVPACK_INVALID_HEADER = \
    u"WavPack header ID invalid"

ERR_WAVPACK_UNSUPPORTED_FMT = \
    u"unsupported FMT compression"

ERR_WAVPACK_INVALID_FMT = \
    u"invalid FMT chunk"

ERR_WAVPACK_NO_FMT = \
    u"FMT chunk not found in WavPack"

ERR_NO_COMPRESSION_MODES = \
    u"Audio type %s has no compression modes"

ERR_UNSUPPORTED_COMPRESSION_MODE = \
    u"\"%(quality)s\" is not a supported compression mode " + \
    u"for type \"%(type)s\""

ERR_INVALID_CDDA = \
    u". Is that an audio cd ?"

ERR_NO_CDDA = \
    u"No CD in drive"

ERR_NO_EMPTY_CDDA = \
    u"No audio tracks found on CD"

ERR_NO_OUTPUT_FILE = \
    u"You must specify an output file"

ERR_DUPLICATE_OUTPUT_FILE = \
    u"Output file \"%s\" occurs more than once"

ERR_URWID_REQUIRED = \
    u"urwid is required for interactive mode"

ERR_GET_URWID1 = \
    u"Please download and install urwid from http://excess.org/urwid/"

ERR_GET_URWID2 = \
    u"or your system's package manager."

ERR_TERMIOS_ERROR = \
    u"Unable to get tty settings"

ERR_TERMIOS_SUGGESTION = \
    u"If piping arguments via xargs(1), try using its -o option"

ERR_NO_GUI = \
    u"Neither PyGTK nor Tkinter is available"

ERR_NO_AUDIO_TS = \
    u"You must specify the DVD-Audio's AUDIO_TS directory with -A"

ERR_INVALID_TITLE_NUMBER = \
    u"title number must be greater than 0"

ERR_INVALID_JOINT = \
    u"You must run at least 1 process at a time"

ERR_NO_CDRDAO = \
    u"Unable to find \"cdrdao\" executable"

ERR_GET_CDRDAO = \
    u"Please install \"cdrdao\" to burn CDs"

ERR_NO_CDRECORD = \
    u"Unable to find \"cdrecord\" executable"

ERR_GET_CDRECORD = \
    u"Please install \"cdrecord\" to burn CDs"

ERR_SAMPLE_RATE_MISMATCH = \
    u"All audio files must have the same sample rate"

ERR_CHANNEL_COUNT_MISMATCH = \
    u"All audio files must have the same channel count"

ERR_CHANNEL_MASK_MISMATCH = \
    u"All audio files must have the same channel assignment"

ERR_BPS_MISMATCH = \
    u"All audio files must have the same bits per sample"

ERR_TRACK2CD_INVALIDFILE = \
    u"Not all files are valid.  Unable to write CD"

ERR_TRACK2TRACK_O_AND_D = \
    u"-o and -d options are not compatible"

ERR_TRACK2TRACK_O_AND_D_SUGGESTION = \
    u"Please specify either -o or -d but not both"

ERR_TRACK2TRACK_O_AND_FORMAT = \
    u"--format has no effect when used with -o"

ERR_TRACK2TRACK_O_AND_MULTIPLE = \
    u"You may specify only 1 input file for use with -o"

ERR_NO_THUMBNAILS = \
    u"Unable to generate thumbnails"

ERR_THUMBNAIL_SUGGESTION1 = \
    u"Please install the Python Imaging Library"

ERR_THUMBNAIL_SUGGESTION2 = \
    u"available at http://www.pythonware.com/products/pil/"

ERR_THUMBNAIL_SUGGESTION3 = \
    u"to enable image resizing"

ERR_INVALID_THUMBNAIL_FORMAT = \
    u"Unsupported thumbnail format \"%s\""

ERR_AVAILABLE_THUMBNAIL_FORMATS = \
    u"Available formats are: %s"

ERR_TRACKCMP_TYPE_MISMATCH = \
    u"Both files to be compared must be audio files"

ERR_TRACKSPLIT_NO_CUESHEET = \
    u"You must specify a cuesheet to split audio file"

ERR_TRACKSPLIT_OVERLONG_CUESHEET = \
    u"Cuesheet too long for track being split"

#Cleaning messages

CLEAN_REMOVE_DUPLICATE_TAG = \
    u"removed duplicate tag %(field)s"

CLEAN_REMOVE_TRAILING_WHITESPACE = \
    u"removed trailing whitespace from %(field)s"

CLEAN_REMOVE_LEADING_WHITESPACE = \
    u"removed leading whitespace from %(field)s"

CLEAN_REMOVE_LEADING_WHITESPACE_ZEROES = \
    u"removed leading whitespace/zeroes from %(field)s"

CLEAN_REMOVE_LEADING_ZEROES = \
    u"removed leading zeroes from %(field)s"

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

CLEAN_WAV_MULTIPLE_FMT_CHUNKS = \
    u"removed duplicate fmt chunk"

CLEAN_WAV_REORDERED_DATA_CHUNK = \
    u"moved data chunk after fmt chunk"

CLEAN_WAV_MULTIPLE_DATA_CHUNKS = \
    u"removed multiple data chunk"

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
