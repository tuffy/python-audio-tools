.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.CHAPTER "Python Reference"

.BEGIN_PROGRAMMING
.SECTION "Module Attributes"

.ATTRIBUTE "AVAILABLE_TYPES"
A tuple of AudioFile-compatible classes defined by this module.

.ATTRIBUTE "BIN"
A system binaries lookup class.
This acts as a dict, taking the string of an executable and
returns a string containing the path to use to execute that
executable.
Since the system \fCaudiotools.cfg\fR config file and a 
user's config file may specify executables in nonstandard locations,
this class will handle the task of checking for them appropriately.

.ATTRIBUTE "BUFFER_SIZE"
An integer representing the amount of data to transfer between
PCM handlers at a time.

.ATTRIBUTE "DEFAULT_CDROM"
A string containing the default CD-ROM device to use
for ripping and burning audio.

.ATTRIBUTE "FILENAME_FORMAT"
A string formatted with Python "%"-based substitution
parameters for use when creating new audio tracks.

.ATTRIBUTE "FREEDB_PORT"
An integer of the default FreeDB port number to use.

.ATTRIBUTE "FREEDB_SERVER"
A string of the default FreeDB server name to use.

.ATTRIBUTE "FS_ENCODING"
The encoding to use for newly created track names written
on the filesystem.

.ATTRIBUTE "IO_ENCODING"
The encoding to use when printing information to the screen.

.ATTRIBUTE "MAX_JOBS"
The default maximum number of processes to run at once.

.ATTRIBUTE "TYPE_MAP"
A dict of suffix strings->AudioFile-compatible classes
containing only those classes whose required executables
are present on the system.

.ATTRIBUTE "VERSION"
A string identifying the module's version.

.bp

.SECTION "Module Functions"

.FUNCTION open filename
Takes a filename and returns an AudioFile-compatible object
corresponding to the type of audio file it is.
If the file is not something supported, open raises an
UnsupportedFile exception.

.FUNCTION open_files "filename_list, [sorted]"
Takes a list of filenames and returns a list of
AudioFile-compatible objects.
Anything not supported is filtered out.
The default behavior is to return the list sorted
by track number.
If sorted is False, the list is returned as-is.

.FUNCTION parse_xmcd_file filename
Takes a filename, opens it, parses the XMCD data and returns
an AlbumMetaData object.

.FUNCTION build_xmcd_file audio_files
Takes a list of AudioFile-compatible objects and returns XMCD file
data as a string.

.FUNCTION get_xmcd "disc_id, output, freedb_server, freedb_server_port"
Runs the entire XMCD-fetching sequence for the given disc_id
on the given FreeDB server and port (using the web-based interface)
and delivering the XMCD file to the given output file handle.
If there are no matches, a blank XMCD file template will be sent.
If there is one match, that XMCD file will be sent.
If there are multiple matches, this function will prompt
for which of them to select via stderr and stdin.
.PP
This function is obviously not suited for querying in a GUI or
anything other than a command-line.
However, it is a small, well-commented routine that one can use
to build other FreeDB querying functions from.

.FUNCTION pcm_cmp "pcmreader1, pcmreader2"
Takes two PCMReader-compatible objects and compares their output.
Returns True if the PCM data is identical.
Returns False if not.

.FUNCTION stripped_pcm_cmp "pcmreader1, pcmreader2"
Takes two PCMReader-compatible objects and compares their output,
stripping any NULL samples from the beginning and end of each.
Returns True if that PCM data is identical.
Returns False if not.

.FUNCTION transfer_data "from_function, to_function"
from_function is expected to take an integer number of bytes
and return a string that large, or an empty string when finished.
to_function is expected to take a string.
These correspond to read() and write() methods, respectively.
This function transfers strings from from_function to to_function
until empty.

.bp

.SECTION AudioFile

.CLASS AudioFile "filename"
filename should be the path to a valid audio file on the system
of the same type as this class.

.FUNCTION bits_per_sample
Returns the number of bits per PCM sample.  16 for CD audio.

.FUNCTION channels
Returns the number of distinct audio channels.  2 for CD audio.

.FUNCTION sample_rate
Returns the number of samples per second.  44100 for CD audio.

.FUNCTION total_frames
Returns the total number of audio frames in the file.
Each frame is a channel-independent block of individual samples.
For example, 1 second of 44100Hz audio has 44100 frames, 
regardless of the number of channels it has.

.FUNCTION cd_frames
Returns the length of the file in CD frames.
Each CD frame is 1/75th of a second.
Most formats do not need to define this method as it
can be derived from the sample_rate and total_frames methods.

.FUNCTION lossless
Returns True if this audio file is stored losslessly.
Returns False if not.

.FUNCTION get_metadata
Returns a Metadata-compatible object containing the track's
metadata, such as track name, track number, artist name and so forth.
This may return None if the track has no metadata or its
format does not support metadata.

.FUNCTION set_metadata metadata
Takes a Metadata-compatible object and sets this track's metadata
to those values.
If metadata is None, this method does nothing.
If the audio format does not support metadata, this method also
does nothing.

.FUNCTION track_number
Returns this track's position in the album, starting from 1.
The metadata's track number is checked first.
If none is present or the metadata has no track number,
try to guess the track number from the audio file's name.
If we can't make any guess, returns 0.

.FUNCTION to_pcm
Returns a PCMReader-compatible object containing a stream of
this audio file's PCM data.

.CLASSMETHOD from_pcm "filename, pcmreader, [compression]"
Builds and returns an AudioFile-compatible object with
the given filename from the given pcmreader and, optionally,
at the given compression setting.

.bp

.CLASSMETHOD track_name "track_number, track_metadata"
Given a track number and MetaData-compatible object,
returns a default filename for this track.

.CLASSMETHOD can_add_replay_gain
Returns True if all the necessary binaries are present to add
ReplayGain metadata, and the format supports such metadata.

.CLASSMETHOD add_replay_gain filenames
Given a list of filenames of AudioFiles with of the same class
as this AudioFile class, calculate and add ReplayGain metadata
to those files.

.FUNCTION replay_gain
Returns a ReplayGain object of the track's ReplayGain values,
if present.
Returns None if no values or present or ReplayGain is not supported.

.CLASSMETHOD has_binaries "system_binaries"
Takes a __system_binaries__ class, typically this module's
BIN attribute.
Checks the system executable paths (and any paths
overridden with __system_binaries__) for all of the executables
necessary to use this class.
Returns True if all the binaries are present.
Returns False if one or more is missing.

.CLASSMETHOD is_type "file"
Takes a seekable file pointer which is rewound to the start of the file.
Returns True if that header data indicates the file is of
this class.
Returns False if not.
This is a simple magic numbers implementation
so that we do not have to rely on filename suffixes to
identify audio types.

.bp

.SECTION Metadata
.PP
This is a human-readable collection of information about a single
track on an album.
It is designed as a lowest-common-demonimator for conversion between
audio formats with vastly different ways of storing track metadata.
So while it is recommended that an AudioFile's get_metadata and
set_metadata methods support more information than these fields,
it is required that they support at least these (assuming the
AudioFile supports any metadata at all).

.CLASS MetaData "track_name=u\[aq]\[aq], track_number=0, album_name=u\[aq]\[aq], artist_name=u\[aq]\[aq], performer_name=u\[aq]\[aq], copyright=u\[aq]\[aq], year=u\[aq]\[aq], images=[]"
track_number is stored as an integer.
The images field, if present, should be a list of Image-compatible objects.
The rest are stored as Unicode strings.


.ATTRIBUTE "track_name"
The name of this track.

.ATTRIBUTE "track_number"
The number of this track on the album as an integer between 1 and 99.

.ATTRIBUTE "album_name"
The name of the album this track belongs to.

.ATTRIBUTE "artist_name"
The name of this track's original artist.

.ATTRIBUTE "performer_name"
The name of this track's performer.

.ATTRIBUTE "copyright"
The copyright information for this track.

.ATTRIBUTE "year"
The release year for this track's album.

.CLASSMETHOD converted "metadata"
This method takes a MetaData-compatible object and returns a
new object of the same class.
For instance, the `converted' method of the VorbisComment class will 
return VorbisComment instances, or None if `metadata' is None.
The purpose of this is to remove the burden of metadata conversion
from the AudioFile classes.
Continuing our example, without `converted', VorbisAudio will have
different ways of handling a `set_metadata' call depending on
whether the MetaData we're setting is already an instance of VorbisComment 
or not (e.g. from FlacAudio).
By converting MetaData with this method, the VorbisAudio class 
only needs to know how to handle VorbisComment instances.

.bp

.CLASSMETHOD supports_images
Returns True if this particular subclass of MetaData supports
embedded images.
Returns False if not.
Subclasses which do not support images will return empty lists
when querying for images and raise exceptions if one attempts to
add or delete images from them.

.FUNCTION images
Returns a list of our stored Images.

.FUNCTION front_covers
Returns a list of our Images which are front covers.

.FUNCTION back_covers
Returns a list of our Images which are back covers.

.FUNCTION leaflet_pages
Returns a list of our Images which are leaflet pages.

.FUNCTION media
Returns a list of our Images of the album media.

.FUNCTION other_images
Returns a list of our Images which aren't in the aforementioned categories.

.FUNCTION add_image image
Takes an Image-compatible object and adds it to our internal list.

.FUNCTION delete_image image
Takes an object, originally from our internal list, and deletes it
from that list.

.bp

.CLASS Image "data, mime_type, width, height, color_depth, color_count, description, type"
.PP
A container for image data.
This is often the base class for metadata-specific embedded images.
.ATTRIBUTE data
A string containing the binary data that comprises this image.

.ATTRIBUTE mime_type
A Unicode string storing the MIME type of this image, such as `image/jpeg'
or `image/png'.

.ATTRIBUTE width
How wide this image is as an integer number of pixels.

.ATTRIBUTE height
How tall this image is as an integer number of pixels.

.ATTRIBUTE color_depth
The number of color this image contains as an integer number of
bits-per-pixel.

.ATTRIBUTE color_count
For palette-based images (such as GIF), 
the total number of colors the image contains.
For images with no palette, this value is 0.

.ATTRIBUTE description
A description of the image as a Unicode string.

.ATTRIBUTE type
What portion of an album this image is of, as an integer.
.TS
tab(:);
c | l.
0:Front Cover
1:Back Cover
2:Leaflet Page
3:Media
4:Other
.TE

.FUNCTION type_string
Returns what portion of an album this image is of, as a string.

.FUNCTION suffix
Returns a string of this image's file suffix, based on its MIME type.
`image/jpeg' returns a suffix of `jpg', for example.

.CLASSMETHOD new "image_data, description, type"
Given a string of image data, a Unicode description string and
integer type, returns an Image object with the remaining fields
filled-in based upon that image data.
This allows a user to add a JPEG to an audio track, for example,
by having the rest of the image information retrieved automatically
based on its contents rather than having to specify those metrics.

.bp

.CLASS ReplayGain "track_gain, track_peak, album_gain, album_peak"
A simple container class for ReplayGain metadata.
All values are floats.

.ATTRIBUTE "track_gain"
This track's ReplayGain value, in dB.

.ATTRIBUTE "track_peak"
This track's peak value.
This is used to prevent clipping.

.ATTRIBUTE "album_gain"
The entire album's ReplayGain value, in dB.

.ATTRIBUTE "album_peak"
The entire album's peak value.

.bp

.SECTION PCMReader

.CLASS PCMReader "file, sample_rate, channels, bits_per_sample, [process]"
A PCM generator class.  It is designed to function much like 
a file reader object, but with additional metadata about the PCM data
being generated.

.FUNCTION read bytes
Returns a number of "bytes" of data from the PCM stream, as a string.
We're not guaranteed to return exactly that amount of bytes, depending
on the implementation of a given PCMReader.
The stream is finished when the number of bytes is 0.

.FUNCTION close
Closes the PCMReader.
If a process is associated with the PCMReader, that process is
finished upon calling close.

.ATTRIBUTE file
A file-like object with read and close methods.

.ATTRIBUTE sample_rate
The PCM stream's number of samples-per-second.
44100 for CD audio.

.ATTRIBUTE channels
The PCM stream's number of channels.
2 for CD audio.

.ATTRIBUTE bits_per_sample
The PCM stream's number of bits per sample.
16 for CD audio.

.ATTRIBUTE process
An optional subprocess-compatible object.
If not None, its wait method will be called when the PCMReader
is closed.

.SECTION PCMConverter

.CLASS PCMConverter "pcmreader, sample_rate, channels, bits_per_sample"
This is a PCMReader-compatible class which takes a PCMReader
and converts its PCM stream to a new format with the given attributes
using resampling, dithering and channel modification, if necessary.
For example, it is not possible to create a CD from a 
PCMReader with a sample rate of 96000Hz, 6 channels and 24 bits-per-sample
because CD audio must have a sample rate of 44100Hz, 2 channels and
16 bits-per-sample.
But by wrapping PCMConverter around that PCMReader, like:
.LP
\fCPCMConverter(pcmreader,44100,2,16)\fR
.LP
PCMConveter's read method will translate the stream to a CD-quality one.
.bp

.SECTION CDDA

.CLASS CDDA "device_name, [speed]"
This class represents an audio CD at the given device and, optionally,
at the given speed.
device_name is a string containing a CD-ROM device
(e.g. \fC"/dev/cdrom"\fR).
speed is an integer rate of speed at which to access that device.

.FUNCTION __len__
Returns the number of tracks on the CD

.FUNCTION __getitem__ "track_number"
Returns a CDTrackReader object for the given track number.
Raises an IndexError if one tries to retrieve a track
beyond the total number available, or a track number below 1.

.FUNCTION __iter__
Generates an iterator over all of the tracks on this CD,
as CDTrackReader objects.


.CLASS CDTrackReader "cdda, track_number"
This is a PCMReader-compatible object containing the PCM data
for the given track number on the given CDDA object.
CDTrackReader should be retrieved from a CDDA object rather than
instantiated directly.

.FUNCTION length
Returns the length of this track in CD frames.

.FUNCTION offset
Returns the total offset of this track from the beginning on the CD,
in CD frames.

.FUNCTION read bytes
Returns a sector-aligned number of bytes from the given track.
This method returns as many sectors as possible to fulfill the
requested number of bytes, or at least 1 sector if the number of
bytes is too small.
It returns an empty string when the sectors have been exhausted.

.FUNCTION close
Closes this track for reading.

.ATTRIBUTE rip_log
A CDTrackLog object containing the log data for this track.

.bp

.CLASS CDTrackLog
This is a container for log data generated by CDTrackReader during
sector extraction.
It is created and set as a global cdio callback automatically by 
CDTrackReader.
Because of this, only one CDTrackLog can be receiving log data
from CD extraction at a time.
This prohibits multiple CDTrackReaders from operating in the same
Python interpreter at the same time (if one wishes to rip data from
2 CDs at once, for instance).
Short of a major libcdio design change, there is little that can be
done to eliminate this restriction.

.FUNCTION __str__
Returns the log information as a string, formatted to be similar
to that generated by the cdda2wav program.

.bp

.SECTION XMCD
.PP
CD audio discs do not typically come with information about the album
name, artist name, track names and so forth; they only contain audio
data split into tracks.
Therefore, that information must come from an external source.
FreeDB is an open source for audio data with a wide coverage of albums
and easy protocols to work with.
It outputs XMCD files.
Therefore, XMCD files are what Python Audio Tools use for external metadata
not contained in the tracks themselves.
If we cannot or do not wish to use FreeDB's XMCD files, ones can
be created from AudioFiles.
.PP
From a programmer's perspective, the goal is to get an
AlbumMetaData object.
Since all our AudioFile objects should have a valid track number
(pulled from the filename, if necessary), AlbumMetaData can tell us
what to name them and the appropriate MetaData to add to them.

.CLASS AlbumMetaData
A track number->MetaData dictionary.

.FUNCTION __getitem__ track_number
Returns a MetaData-compatible object for the given integer track_number.
Throws a KeyError if the track_number is not in AlbumMetaData.
track_numbers start from 1.


.CLASS DiscID "[tracks]"
One must submit disc track information to FreeDB in order to receive
an XMCD file.
DiscID is a container object for that information.
It can be created either from the CD audio disc itself, 
or from tracks ripped from that disc.
If present, the "tracks" argument should be a list of track lengths,
in CD frames.

.FUNCTION add track
Takes the length of a track in CD frames and adds it to this DiscID.

.FUNCTION offsets
Returns a list of CD track offsets based on the DiscID's track lengths.

.FUNCTION idsuffix
Returns a string containing the CD's number of tracks, track offsets
and total length in seconds.

.FUNCTION __str__
Returns a string containing the 32-bit FreeDB disc ID calculated
from the track lengths.

.FUNCTION toxmcd
Returns an empty XMCD file as a string, suitable for populating by
the user.

.bp

.CLASS FreeDB "servername, port"
This is a connection to the FreeDB server at the given servername and port.
It uses FreeDB's native protocol rather than the web-based one.
Prints status information to stderr while it operates.

.FUNCTION connect
Performs the socket connection to the FreeDB server.

.FUNCTION close
Closes the socket connection to the FreeDB server.

.FUNCTION write line
Writes a command line to the FreeDB server.

.FUNCTION read
Reads a response line from the FreeDB server and returns
the response code and response data as a tuple.

.FUNCTION query disc_id
Takes a DiscID object.
Queries the FreeDB server for any or all matches and returns them
as a list of category/id tuples.

.FUNCTION read_data "category, id, output"
Takes the category and id fields, as returned by query(),
retrieves the XMCD data of that disc from the FreeDB server
and sends it to output, which must have a write() method.


.CLASS FreeDBWeb "servername, port"
This is a web-based connection to a FreeDB server.
It is a subclass of FreeDB with all the same methods and can
be used interchangeably.

.END_PROGRAMMING
