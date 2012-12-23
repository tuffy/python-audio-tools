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

VERSION = '2.20alpha1'

import sys

if (sys.version_info < (2, 6, 0, 'final', 0)):
    print >> sys.stderr, "*** Python 2.6.0 or better required"
    sys.exit(1)

from distutils.core import setup, Extension


cdiomodule = Extension('audiotools.cdio',
                       sources=['src/cdiomodule.c'],
                       libraries=['cdio', 'cdio_paranoia',
                                  'cdio_cdda', 'm'])

pcmmodule = Extension('audiotools.pcm',
                      sources=['src/pcm.c'])

pcmconvmodule = Extension('audiotools.pcmconverter',
                          sources=['src/pcmconverter.c',
                                   'src/pcmconv.c',
                                   'src/array.c',
                                   'src/bitstream.c'])

replaygainmodule = Extension('audiotools.replaygain',
                             sources=['src/replaygain.c',
                                      'src/pcmconv.c',
                                      'src/array.c',
                                      'src/bitstream.c'])

decoders_defines = [("VERSION", VERSION)]
decoders_sources = ['src/array.c',
                    'src/pcmconv.c',
                    'src/common/md5.c',
                    'src/bitstream.c',
                    'src/huffman.c',
                    'src/decoders/flac.c',
                    'src/decoders/oggflac.c',
                    'src/common/flac_crc.c',
                    'src/common/ogg_crc.c',
                    'src/common/tta_crc.c',
                    'src/decoders/shn.c',
                    'src/decoders/alac.c',
                    'src/decoders/wavpack.c',
                    # 'src/decoders/vorbis.c',
                    'src/decoders/tta.c',
                    'src/decoders/mlp.c',
                    'src/decoders/aobpcm.c',
                    'src/decoders/aob.c',
                    'src/decoders/sine.c',
                    'src/decoders/ogg.c',
                    'src/decoders/mod_cppm.c',
                    'src/decoders.c']

if (sys.platform == 'linux2'):
    decoders_defines.extend([('DVD_STRUCT_IN_LINUX_CDROM_H', None),
                             ('HAVE_LINUX_DVD_STRUCT', None),
                             ('HAS_UNPROT', None)])
    decoders_sources.extend(['src/decoders/cppm.c',
                             'src/decoders/ioctl.c',
                             'src/decoders/dvd_css.c'])

decodersmodule = Extension('audiotools.decoders',
                           sources=decoders_sources,
                           define_macros=decoders_defines)

encodersmodule = Extension('audiotools.encoders',
                           sources=['src/array.c',
                                    'src/pcmconv.c',
                                    'src/bitstream.c',
                                    'src/common/md5.c',
                                    'src/encoders/flac.c',
                                    'src/common/flac_crc.c',
                                    'src/encoders/shn.c',
                                    'src/encoders/alac.c',
                                    'src/encoders/wavpack.c',
                                    'src/encoders.c'],
                           define_macros=[("VERSION", VERSION)])

bitstreammodule = Extension('audiotools.bitstream',
                            sources=['src/mod_bitstream.c',
                                     'src/bitstream.c',
                                     'src/huffman.c'])

verifymodule = Extension('audiotools.verify',
                         sources=['src/verify.c',
                                  'src/common/ogg_crc.c',
                                  'src/bitstream.c'])

output_sources = ['src/output.c']
output_defines = []
output_link_args = []

if (sys.platform == 'darwin'):
    output_sources.append('src/output/core_audio.c')
    output_defines.append(("CORE_AUDIO", "1"))
    output_link_args.extend(["-framework", "AudioToolbox",
                             "-framework", "AudioUnit",
                             "-framework", "CoreServices"])

outputmodule = Extension('audiotools.output',
                         sources=output_sources,
                         define_macros=output_defines,
                         extra_link_args=output_link_args)

setup(name='Python Audio Tools',
      version=VERSION,
      description='A collection of audio handling utilities',
      author='Brian Langenberger',
      author_email='tuffy@users.sourceforge.net',
      url='http://audiotools.sourceforge.net',
      packages=["audiotools",
                "audiotools.py_decoders",
                "audiotools.py_encoders"],
      ext_modules=[cdiomodule,
                   pcmmodule,
                   pcmconvmodule,
                   replaygainmodule,
                   decodersmodule,
                   encodersmodule,
                   bitstreammodule,
                   verifymodule,
                   outputmodule],
      data_files=[("/etc", ["audiotools.cfg"])],
      scripts=["audiotools-config",
               "cd2track",
               "cdinfo",
               "cdplay",
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
               "trackverify"])
