#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007  Brian Langenberger

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


from distutils.core import setup, Extension

cdiomodule = Extension('audiotools.cdio',
                    sources = ['src/cdiomodule.c'],
                    libraries = ['cdio','cdio_paranoia',
                                 'cdio_cdda','m'])

bitstreammodule = Extension('audiotools.bitstream',
                            sources = ['src/bitstream.c'])

pcmstreammodule = Extension('audiotools.pcmstream',
                            sources = ['src/pcmstream.c'],
                            libraries = ['samplerate'])

setup (name = 'Python Audio Tools',
       version = '2.4',
       description = 'A collection of audio handling utilities',
       author = 'Brian Langenberger',
       author_email = 'tuffy@users.sourceforge.net',
       url='http://audiotools.sourceforge.net',
       packages = ["audiotools"],
       ext_modules = [cdiomodule,bitstreammodule,pcmstreammodule],
       data_files = [("etc",["audiotools.cfg"]),
                     ("share/audiotools",["glade/coverview.glade"])],
       scripts = ["cd2track","cd2xmcd",
                  "track2track","track2xmcd","trackrename","trackinfo",
                  "tracklength","track2cd","trackcmp","trackcat","trackplay",
                  "tracktag","editxmcd","audiotools-config", 
                  "coverdump","coverview"])
