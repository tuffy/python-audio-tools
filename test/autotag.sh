#!/bin/sh

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
