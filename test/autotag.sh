#!/bin/sh

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2016  Brian Langenberger

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

tracktag -r "$1"
trackinfo "$1"

echo "Adding Track Name:"
sleep 1
tracktag "--name=Track Name" "$1"
trackinfo "$1"

echo "Adding Artist Name:"
sleep 1
tracktag "--artist=Artist Name" "$1"
trackinfo "$1"

echo "Adding Performer Name:"
sleep 1
tracktag "--performer=Performer Name" "$1"
trackinfo "$1"

echo "Adding Composer Name:"
sleep 1
tracktag "--composer=Composer Name" "$1"
trackinfo "$1"

echo "Adding Conductor Name:"
sleep 1
tracktag "--conductor=Conductor Name" "$1"
trackinfo "$1"

echo "Adding Album Name:"
sleep 1
tracktag "--album=Album Name" "$1"
trackinfo "$1"

echo "Adding Catalog Number:"
sleep 1
tracktag "--catalog=Catalog Number" "$1"
trackinfo "$1"

echo "Adding Track Number:"
sleep 1
tracktag "--number=2" "$1"
trackinfo "$1"

echo "Adding Album Number:"
sleep 1
tracktag "--album-number=3" "$1"
trackinfo "$1"

echo "Adding ISRC:"
sleep 1
tracktag "--ISRC=US-PR3-08-12345" "$1"
trackinfo "$1"

echo "Adding Publisher Name:"
sleep 1
tracktag "--publisher=Publisher Name" "$1"
trackinfo "$1"

echo "Adding Media:"
sleep 1
tracktag "--media-type=CD" "$1"
trackinfo "$1"

echo "Adding Year:"
sleep 1
tracktag "--year=2008" "$1"
trackinfo "$1"

echo "Adding Date:"
sleep 1
tracktag "--date=2008-10-17" "$1"
trackinfo "$1"

echo "Adding Copyright:"
sleep 1
tracktag "--copyright=Test Copyright" "$1"
trackinfo "$1"
