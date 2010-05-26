#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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

VERSION = '2.15alpha3'

import sys

if (sys.version_info < (2,5,0,'final',0)):
    print >>sys.stderr,"*** Python 2.5.0 or better required"
    sys.exit(1)

from distutils.core import setup, Extension
import subprocess,re

def pkg_config(package, option):
    sub = subprocess.Popen(["pkg-config",option,package],
                           stdout=subprocess.PIPE)
    spaces = re.compile('\s+',re.DOTALL)
    args = spaces.split(sub.stdout.read().strip())
    sub.stdout.close()
    sub.wait()
    return args

cdiomodule = Extension('audiotools.cdio',
                    sources = ['src/cdiomodule.c'],
                    libraries = ['cdio','cdio_paranoia',
                                 'cdio_cdda','m'])

resamplemodule = Extension('audiotools.resample',
                            sources = ['src/resample.c'])

pcmmodule = Extension('audiotools.pcm',
                      sources = ['src/pcm.c'])

replaygainmodule = Extension('audiotools.replaygain',
                             sources = ['src/replaygain.c'])

decodersmodule = Extension('audiotools.decoders',
                           sources = ['src/array.c',
                                      'src/bitstream_r.c',
                                      'src/decoders/flac.c',
                                      'src/decoders/shn.c',
                                      'src/decoders/alac.c',
                                      'src/decoders.c'],
                           define_macros = [("VERSION",VERSION)])

encodersmodule = Extension('audiotools.encoders',
                           sources = ['src/array.c',
                                      'src/bitstream_w.c',
                                      'src/pcmreader.c',
                                      'src/md5.c',
                                      'src/encoders/flac.c',
                                      'src/encoders/flac_lpc.c',
                                      'src/encoders/shn.c',
                                      'src/encoders.c'],
                           define_macros = [("VERSION",VERSION)])

extensions = [cdiomodule,
              resamplemodule,
              pcmmodule,
              replaygainmodule,
              decodersmodule,
              encodersmodule]


#This is an ALSA extension module, not quite ready for use.
#It chokes on a large number of hi-def PCM combinations
#which makes it not yet suitable for general use.
# try:
#     if (subprocess.call(["pkg-config","--exists","alsa"]) == 0):
#         #ALSA available
#         extensions.append(Extension(
#             'audiotools.alsa',
#             sources = ['src/alsa.c'],
#             include_dirs = [f[2:] for f in pkg_config('alsa','--cflags') if
#                             (f.startswith('-I'))],
#             libraries = [f[2:] for f in pkg_config('alsa','--libs') if
#                          (f.startswith('-l'))],
#             library_dirs = [f[2:] for f in pkg_config('alsa','--libs') if
#                             (f.startswith('-L'))]))

# except OSError:
#     pass #pkg-config not available

# try:
#     if (subprocess.call(["pkg-config","--exists","libpulse"]) == 0):
#         #libpulse available
#         extensions.append(Extension(
#             'audiotools.pulse',
#             sources = ['src/pulse.c'],
#             include_dirs = [f[2:] for f in
#                             pkg_config('libpulse-simple','--cflags') if
#                             (f.startswith('-I'))],
#             libraries = [f[2:] for f in
#                          pkg_config('libpulse-simple','--libs') if
#                          (f.startswith('-l'))],
#             library_dirs = [f[2:] for f in
#                             pkg_config('libpulse-simple','--libs') if
#                             (f.startswith('-L'))]
#             ))

# except OSError:
#     pass #pkg-config not available

setup (name = 'Python Audio Tools',
       version = VERSION,
       description = 'A collection of audio handling utilities',
       author = 'Brian Langenberger',
       author_email = 'tuffy@users.sourceforge.net',
       url='http://audiotools.sourceforge.net',
       packages = ["audiotools",
                   "audiotools.construct",
                   "audiotools.construct.lib"],
       ext_modules = extensions,
       data_files = [("/etc",["audiotools.cfg"]),
                     ("share/audiotools",["glade/coverview.glade"]),
                     ("share/audiotools",["glade/editxmcd.glade"])],
       scripts = ["cd2track","cd2xmcd","cdinfo",
                  "track2track","track2xmcd","trackrename","trackinfo",
                  "tracklength","track2cd","trackcmp","trackplay",
                  "tracktag","editxmcd","audiotools-config",
                  "trackcat","tracksplit",
                  "tracklint",
                  "coverdump","coverview","record2track"])
