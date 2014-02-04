#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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

import sys

if (sys.version_info < (2, 7, 0, 'final', 0)):
    print >> sys.stderr, "*** Python 2.7.0 or better required"
    sys.exit(1)

import os
import os.path
import re
import subprocess
from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext as _build_ext
from ConfigParser import (RawConfigParser, NoSectionError, NoOptionError)


configfile = RawConfigParser()
configfile.read(["setup.cfg"])


VERSION = re.search(r'VERSION\s*=\s"(.+?)"',
                    open(os.path.join(
                        os.path.dirname(sys.argv[0]),
                        "audiotools/__init__.py")).read()).group(1)


LIBRARY_URLS = {"libcdio_paranoia": "http://www.gnu.org/software/libcdio/",
                "libmpg123": "http://www.mpg123.org",
                "vorbisfile": "http://xiph.org",
                "opusfile": "http://www.opus-codec.org",
                "opus": "http://www.opus-codec.org",
                "mp3lame": "http://lame.sourceforge.net",
                "twolame": "http://twolame.sourceforge.net",
                "vorbisenc": "http://www.xiph.org",
                "alsa": "http://www.alsa-project.org",
                "libasound2": "http://www.alsa-project.org",
                "libpulse": "http://www.freedesktop.org"}


class SystemLibraries:
    def __init__(self, configfile):
        self.configfile = configfile

    def guaranteed_present(self, library):
        """given library name string
        returns True if library is guaranteed present,
        False if library is not present,
        None if one should probe for the library

        default is None"""

        try:
            if (self.configfile.get("Libraries", library) == "probe"):
                return None
            else:
                try:
                    return self.configfile.getboolean("Libraries", library)
                except ValueError:
                    return None
        except NoSectionError:
            return None
        except NoOptionError:
            return None

    def present(self, library):
        """returns True if the given library is present on the system,
        returns False if it cannot be found"""

        present = self.guaranteed_present(library)
        if (present is None):
            #probe for library using pkg-config, if available
            try:
                pkg_config = subprocess.Popen(
                    ["pkg-config", "--exists", library],
                    stdout=open(os.devnull, "wb"),
                    stderr=open(os.devnull, "wb"))
                return (pkg_config.wait() == 0)
            except OSError:
                #pkg-config not found, so assume library isn't found
                return False
        else:
            return present

    def extra_compile_args(self, library):
        """returns a list of compile argument strings for populating
        an extension's 'extra_compile_args' argument

        the list may be empty"""

        try:
            pkg_config = subprocess.Popen(
                ["pkg-config", "--cflags", library],
                stdout=subprocess.PIPE,
                stderr=open(os.devnull, "wb"))

            pkg_config_stdout = pkg_config.stdout.read().strip()

            if (pkg_config.wait() == 0):
                #libraries found
                return pkg_config_stdout.split()
            else:
                #library not found
                return []
        except OSError:
            #pkg-config not found
            return []

    def extra_link_args(self, library):
        """returns a list of link argument strings for populating
        an extension's 'extra_link_args' argument

        the list may be empty"""

        try:
            pkg_config = subprocess.Popen(
                ["pkg-config", "--libs", library],
                stdout=subprocess.PIPE,
                stderr=open(os.devnull, "wb"))

            pkg_config_stdout = pkg_config.stdout.read().strip()

            if (pkg_config.wait() == 0):
                #libraries found
                return pkg_config_stdout.split()
            else:
                #library not found
                return []
        except OSError:
            #pkg-config not found
            return []


system_libraries = SystemLibraries(configfile)


class output_table:
    def __init__(self):
        """a class for formatting rows for display"""

        self.__rows__ = []

    def row(self):
        """returns a output_table_row object which columns can be added to"""

        row = output_table_row()
        self.__rows__.append(row)
        return row

    def blank_row(self):
        """inserts a blank table row with no output"""

        self.__rows__.append(output_table_blank())

    def divider_row(self, dividers):
        """adds a row of unicode divider characters

        there should be one character in dividers per output column"""

        self.__rows__.append(output_table_divider(dividers))

    def format(self):
        """yields one formatted string per row"""

        if (len(self.__rows__) == 0):
            #no rows, so do nothing
            return

        if (len(set([len(r) for r in self.__rows__ if
                     not isinstance(r, output_table_blank)])) != 1):
            raise ValueError("all rows must have same number of columns")

        column_widths = [
            max([row.column_width(col) for row in self.__rows__])
            for col in xrange(len(self.__rows__[0]))]

        for row in self.__rows__:
            yield row.format(column_widths)


class output_table_row:
    def __init__(self):
        """a class for formatting columns for display"""

        self.__columns__ = []

    def __len__(self):
        return len(self.__columns__)

    def add_column(self, text, alignment="left"):
        """adds text which is a plain string and an optional alignment

        alignment may be 'left', 'center', 'right'"""

        if (alignment not in ("left", "center", "right")):
            raise ValueError("alignment must be 'left', 'center', or 'right'")

        self.__columns__.append((text, alignment))

    def column_width(self, column):
        return len(self.__columns__[column][0])

    def format(self, column_widths):
        """returns formatted row as a string"""

        def align_left(text, width):
            spaces = width - len(text)

            if (spaces > 0):
                return text + " " * spaces
            else:
                return text

        def align_right(text, width):
            spaces = width - len(text)

            if (spaces > 0):
                return " " * spaces + text
            else:
                return text

        def align_center(text, width):
            left_spaces = (width - len(text)) // 2
            right_spaces = width - (left_spaces + len(text))

            if ((left_spaces + right_spaces) > 0):
                return (" " * left_spaces +
                        text +
                        " " * right_spaces)
            else:
                return text

        #attribute to method mapping
        align_meth = {"left": align_left,
                      "right": align_right,
                      "center": align_center}

        assert(len(column_widths) == len(self.__columns__))

        return "".join([align_meth[alignment](text, width)
                        for ((text, alignment), width) in
                        zip(self.__columns__, column_widths)]).rstrip()


class output_table_divider:
    """a class for formatting a row of divider characters"""

    def __init__(self, dividers):
        self.__dividers__ = dividers[:]

    def __len__(self):
        return len(self.__dividers__)

    def column_width(self, column):
        return 0

    def format(self, column_widths):
        """returns formatted row as a string"""

        assert(len(column_widths) == len(self.__dividers__))

        return "".join([divider * width
                        for (divider, width) in
                        zip(self.__dividers__, column_widths)]).rstrip()


class output_table_blank:
    """a class for an empty table row"""

    def __init__(self):
        pass

    def column_width(self, column):
        return 0

    def format(self, column_widths):
        """returns formatted row as a string"""

        return ""


class build_ext(_build_ext):
    def build_extensions(self):
        _build_ext.build_extensions(self)

        print "=" * 60
        print "Python Audio Tools %s Setup" % (VERSION)
        print "=" * 60

        #lib_name -> ([used for, ...], is present)
        libraries = {}

        for extension in self.extensions:
            if ((hasattr(extension, "library_manifest") and
                 callable(extension.library_manifest))):
                for (library,
                     used_for,
                     is_present) in extension.library_manifest():
                    if (library in libraries):
                        libraries[library] = (
                            libraries[library][0] + [used_for],
                            libraries[library][1] and is_present)
                    else:
                        libraries[library] = ([used_for], is_present)

        table = output_table()

        header = table.row()
        header.add_column("library", "right")
        header.add_column(" ")
        header.add_column("present?")
        header.add_column(" ")
        header.add_column("used for")
        header.add_column(" ")
        header.add_column("download URL")

        table.divider_row(["-", " ", "-", " ", "-", " ", "-"])

        for library in sorted(libraries.keys()):
            row = table.row()
            row.add_column(library, "right")
            row.add_column(" ")
            row.add_column("yes" if libraries[library][1] else "no")
            row.add_column(" ")
            row.add_column(", ".join(libraries[library][0]))
            row.add_column(" ")
            if (not libraries[library][1]):
                row.add_column(LIBRARY_URLS[library])
            else:
                row.add_column("")

        for row in table.format():
            print row
        print


class audiotools_cdio(Extension):
    def __init__(self, system_libraries):
        """extra_link_args is a list of argument strings
        from pkg-config, or None if we're to use the standard
        libcdio libraries"""

        self.__library_manifest__ = []
        sources = []
        libraries = set()
        extra_link_args = []

        if (system_libraries.present("libcdio_paranoia")):
            if (system_libraries.guaranteed_present("libcdio_paranoia")):
                libraries.update(set(["libcdio",
                                      "libcdio_cdda",
                                      "libcdio_paranoia"]))
            else:
                extra_link_args.extend(
                    system_libraries.extra_link_args("libcdio_paranoia"))
            sources.append("src/cdiomodule.c")
            self.__library_manifest__.append(("libcdio",
                                              "CDDA data extraction",
                                              True))
        else:
            self.__library_manifest__.append(("libcdio",
                                              "CDDA data extraction",
                                              False))

        Extension.__init__(
            self,
            'audiotools.cdio',
            sources=sources,
            libraries=list(libraries),
            extra_link_args=extra_link_args)

    def library_manifest(self):
        for values in self.__library_manifest__:
            yield values

    def libraries_present(self):
        for (library, used_for, is_present) in self.library_manifest():
            if (not is_present):
                return False
        else:
            return True


class audiotools_pcm(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools.pcm',
                           sources=['src/pcm.c'])


class audiotools_pcmconverter(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools.pcmconverter',
                           sources=['src/pcmconverter.c',
                                    'src/pcmconv.c',
                                    'src/array.c',
                                    'src/bitstream.c',
                                    'src/buffer.c',
                                    'src/func_io.c',
                                    'src/samplerate/samplerate.c',
                                    'src/samplerate/src_sinc.c',
                                    'src/samplerate/src_zoh.c',
                                    'src/samplerate/src_linear.c'])


class audiotools_replaygain(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools.replaygain',
                           sources=['src/replaygain.c',
                                    'src/pcmconv.c',
                                    'src/array.c',
                                    'src/bitstream.c',
                                    'src/buffer.c',
                                    'src/func_io.c'])


class audiotools_decoders(Extension):
    def __init__(self, system_libraries):
        self.__library_manifest__ = []

        defines = [("VERSION", VERSION)]
        sources = ['src/array.c',
                   'src/pcmconv.c',
                   'src/common/md5.c',
                   'src/bitstream.c',
                   'src/buffer.c',
                   'src/func_io.c',
                   'src/huffman.c',
                   'src/decoders/flac.c',
                   'src/decoders/oggflac.c',
                   'src/common/flac_crc.c',
                   'src/ogg.c',
                   'src/ogg_crc.c',
                   'src/common/tta_crc.c',
                   'src/decoders/shn.c',
                   'src/decoders/alac.c',
                   'src/decoders/wavpack.c',
                   'src/decoders/tta.c',
                   'src/decoders/mlp.c',
                   'src/decoders/aobpcm.c',
                   'src/decoders/aob.c',
                   'src/decoders/sine.c',
                   'src/decoders/mod_cppm.c',
                   'src/decoders.c']
        libraries = set()
        extra_link_args = []
        extra_compile_args = []

        if (system_libraries.present("libmpg123")):
            if (system_libraries.guaranteed_present("libmpg123")):
                libraries.add("mpg123")
            else:
                extra_link_args.extend(
                    system_libraries.extra_link_args("libmpg123"))
            defines.append(("HAS_MP3", None))
            sources.append("src/decoders/mp3.c")
            self.__library_manifest__.append(("libmpg123",
                                              "MP3/MP2 decoding",
                                              True))
        else:
            self.__library_manifest__.append(("libmpg123",
                                              "MP3/MP2 decoding",
                                              False))

        if (system_libraries.present("vorbisfile")):
            if (system_libraries.guaranteed_present("vorbisfile")):
                libraries.update(set(["vorbisfile", "vorbis", "ogg"]))
            else:
                extra_link_args.extend(
                    system_libraries.extra_link_args("vorbisfile"))
            defines.append(("HAS_VORBIS", None))
            sources.append("src/decoders/vorbis.c")
            self.__library_manifest__.append(("vorbisfile",
                                              "Ogg Vorbis decoding",
                                              True))
        else:
            self.__library_manifest__.append(("vorbisfile",
                                              "Ogg Vorbis decoding",
                                              False))

        if (system_libraries.present("opusfile")):
            if (system_libraries.guaranteed_present("opusfile")):
                libraries.add("opusfile")
            else:
                extra_compile_args.extend(
                    system_libraries.extra_compile_args("opusfile"))
                extra_link_args.extend(
                    system_libraries.extra_link_args("opusfile"))
            defines.append(("HAS_OPUS", None))
            sources.append("src/decoders/opus.c")
            self.__library_manifest__.append(("opusfile",
                                              "Opus decoding",
                                              True))
        else:
            self.__library_manifest__.append(("opusfile",
                                              "Opus decoding",
                                              False))

        if (sys.platform == 'linux2'):
            defines.extend([('DVD_STRUCT_IN_LINUX_CDROM_H', None),
                            ('HAVE_LINUX_DVD_STRUCT', None),
                            ('HAS_UNPROT', None)])
            sources.extend(['src/decoders/cppm.c',
                            'src/decoders/ioctl.c',
                            'src/decoders/dvd_css.c'])

        Extension.__init__(self,
                           'audiotools.decoders',
                           sources=sources,
                           define_macros=defines,
                           libraries=list(libraries),
                           extra_compile_args=extra_compile_args,
                           extra_link_args=extra_link_args)

    def library_manifest(self):
        for values in self.__library_manifest__:
            yield values


class audiotools_encoders(Extension):
    def __init__(self, system_libraries):
        self.__library_manifest__ = []
        defines = [("VERSION", VERSION)]
        sources = ['src/array.c',
                   'src/pcmconv.c',
                   'src/bitstream.c',
                   'src/buffer.c',
                   'src/func_io.c',
                   'src/common/md5.c',
                   'src/encoders/flac.c',
                   'src/common/flac_crc.c',
                   'src/common/tta_crc.c',
                   'src/encoders/shn.c',
                   'src/encoders/alac.c',
                   'src/encoders/wavpack.c',
                   'src/encoders/tta.c',
                   'src/encoders.c']
        libraries = set()
        extra_link_args = []
        extra_compile_args = []

        if (system_libraries.present("mp3lame")):
            if (system_libraries.guaranteed_present("mp3lame")):
                libraries.add("mp3lame")
            else:
                #the LAME library doesn't seem to show in pkg-config
                #so this may not be used
                extra_link_args.extend(
                    system_libraries.extra_link_args("mp3lame"))

            defines.append(("HAS_MP3", None))
            sources.append("src/encoders/mp3.c")
            self.__library_manifest__.append(("mp3lame",
                                              "MP3 encoding",
                                              True))
        else:
            self.__library_manifest__.append(("mp3lame",
                                              "MP3 encoding",
                                              False))

        if (system_libraries.present("twolame")):
            if (system_libraries.guaranteed_present("twolame")):
                libraries.add("twolame")
            else:
                extra_link_args.extend(
                    system_libraries.extra_link_args("twolame"))

            defines.append(("HAS_MP2", None))
            sources.append("src/encoders/mp2.c")
            self.__library_manifest__.append(("twolame",
                                              "MP2 encoding",
                                              True))
        else:
            self.__library_manifest__.append(("twolame",
                                              "MP2 encoding",
                                              False))

        if (system_libraries.present("vorbisenc")):
            if (system_libraries.guaranteed_present("vorbisenc")):
                libraries.update(set(["vorbisenc", "vorbis", "ogg"]))
            else:
                extra_link_args.extend(
                    system_libraries.extra_link_args("vorbisenc"))

            defines.append(("HAS_VORBIS", None))
            sources.append("src/encoders/vorbis.c")
            self.__library_manifest__.append(("vorbisenc",
                                              "Ogg Vorbis encoding",
                                              True))
        else:
            self.__library_manifest__.append(("vorbisenc",
                                              "Ogg Vorbis encoding",
                                              False))

        if (system_libraries.present("opus")):
            if (system_libraries.guaranteed_present("opus")):
                libraries.add("opus")
            else:
                extra_compile_args.extend(
                    system_libraries.extra_compile_args("opus"))
                extra_link_args.extend(
                    system_libraries.extra_link_args("opus"))
            defines.append(("HAS_OPUS", None))
            sources.append("src/encoders/opus.c")
            self.__library_manifest__.append(("opus",
                                              "Opus encoding",
                                              True))
        else:
            self.__library_manifest__.append(("opus",
                                              "Opus encoding",
                                              False))

        Extension.__init__(self,
                           'audiotools.encoders',
                           sources=sources,
                           define_macros=defines,
                           libraries=list(libraries),
                           extra_compile_args=extra_compile_args,
                           extra_link_args=extra_link_args)

    def library_manifest(self):
        for values in self.__library_manifest__:
            yield values


class audiotools_bitstream(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools.bitstream',
                           sources=['src/mod_bitstream.c',
                                    'src/bitstream.c',
                                    'src/buffer.c',
                                    'src/func_io.c',
                                    'src/huffman.c'])


class audiotools_verify(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools.verify',
                           sources=['src/verify.c',
                                    'src/bitstream.c',
                                    'src/buffer.c',
                                    'src/func_io.c'])


class audiotools_ogg(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools._ogg',
                           sources=['src/ogg.c',
                                    'src/ogg_crc.c',
                                    'src/mod_ogg.c',
                                    'src/bitstream.c',
                                    'src/func_io.c',
                                    'src/buffer.c'])


class audiotools_accuraterip(Extension):
    def __init__(self):
        Extension.__init__(self,
                           'audiotools._accuraterip',
                           sources=['src/accuraterip.c'])


class audiotools_output(Extension):
    def __init__(self, system_libraries):
        self.__library_manifest__ = []

        sources = ['src/output.c']
        defines = []
        libraries = set()
        extra_link_args = []

        #assume MacOS X always has CoreAudio
        if (sys.platform == 'darwin'):
            sources.append('src/output/core_audio.c')
            defines.append(("CORE_AUDIO", "1"))
            extra_link_args.extend(["-framework", "AudioToolbox",
                                    "-framework", "AudioUnit",
                                    "-framework", "CoreServices"])
            self.__library_manifest__.append(("CoreAudio",
                                              "Core Audio output",
                                              True))
        elif (sys.platform.startswith("linux")):
            #only check for ALSA on Linux
            if (system_libraries.present("alsa")):
                if (system_libraries.guaranteed_present("alsa")):
                    libraries.add("asound")
                else:
                    extra_link_args.extend(
                        system_libraries.extra_link_args("alsa"))
                sources.append("src/output/alsa.c")
                sources.append("src/pcmconv.c")
                defines.append(("ALSA", "1"))
                self.__library_manifest__.append(("libasound2",
                                                  "ALSA output",
                                                  True))
            else:
                self.__library_manifest__.append(("libasound2",
                                                  "ALSA output",
                                                  False))

        if (system_libraries.present("libpulse")):
            if (system_libraries.guaranteed_present("libpulse")):
                libraries.add("pulse")
            else:
                extra_link_args.extend(
                    system_libraries.extra_link_args("libpulse"))
            sources.append("src/output/pulseaudio.c")
            #only include pcmconv once
            if ("src/pcmconv.c" not in sources):
                sources.append("src/pcmconv.c")
            defines.append(("PULSEAUDIO", "1"))
            self.__library_manifest__.append(("libpulse",
                                              "PulseAudio output",
                                              True))
        else:
            self.__library_manifest__.append(("libpulse",
                                              "PulseAudio output",
                                              False))

        Extension.__init__(self,
                           'audiotools.output',
                           sources=sources,
                           define_macros=defines,
                           libraries=list(libraries),
                           extra_link_args=extra_link_args)

    def library_manifest(self):
        for values in self.__library_manifest__:
            yield values


ext_audiotools_cdio = audiotools_cdio(system_libraries)

ext_modules = [audiotools_pcm(),
               audiotools_pcmconverter(),
               audiotools_replaygain(),
               audiotools_decoders(system_libraries),
               audiotools_encoders(system_libraries),
               audiotools_bitstream(),
               audiotools_ogg(),
               audiotools_verify(),
               audiotools_accuraterip(),
               audiotools_output(system_libraries)]

scripts = ["audiotools-config",
           "coverdump",
           "covertag",
           "coverview",
           "dvda2track",
           "dvdainfo",
           "track2cd",
           "track2track",
           "trackcat",
           "trackcmp",
           "trackinfo",
           "tracklength",
           "tracklint",
           "trackplay",
           "trackrename",
           "tracksplit",
           "tracktag",
           "trackverify"]

if (ext_audiotools_cdio.libraries_present()):
    ext_modules.append(ext_audiotools_cdio)
    scripts.extend(["cd2track", "cdinfo", "cdplay"])

# Build out data_files
if (os.access('/etc', os.W_OK)): # See if we can place it in the system /etc
    data_files = [("/etc", ["audiotools.cfg"])]
else:
    # Check that the prefixed etc directory exists
    if (not os.path.isdir(os.path.join(sys.prefix, 'etc'))
            and os.access(sys.prefix, os.W_OK)):
        os.mkdir(os.path.join(sys.prefix, 'etc'))

    # Check if we can place it in the prefix etc
    if (os.access(os.path.join(sys.prefix, 'etc'), os.W_OK)):
        data_files = [(os.path.join(sys.prefix, 'etc'), ["audiotools.cfg"])]
    else:
        # See if we can place it in the 'user' home dir
        if (os.access(os.path.expanduser('~/'), os.W_OK)):
            data_files = [(os.path.expanduser('~/'), [".audiotools.cfg"])]
        else:
            print >> sys.stderr, \
                    "*** Could not find writable path to place audiotools.cfg"
            sys.exit(1)

setup(name='Python Audio Tools',
      version=VERSION,
      description='A collection of audio handling utilities',
      author='Brian Langenberger',
      author_email='tuffy@users.sourceforge.net',
      url='http://audiotools.sourceforge.net',
      packages=["audiotools",
                "audiotools.py_decoders",
                "audiotools.py_encoders"],
      ext_modules=ext_modules,
      cmdclass={"build_ext": build_ext},
      data_files=data_files,
      scripts=scripts)
