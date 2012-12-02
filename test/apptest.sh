#!/bin/sh

echo "Extracting CD"
mkdir -v testdisc1
cd2track -t flac -D -d testdisc1

echo "Transcoding CD"
mkdir -v testdisc2
track2track -t wv testdisc1/*.flac -d testdisc2

echo "Getting info"
trackinfo testdisc2/*.wv

echo "Comparing CD to original"
trackcmp testdisc1 testdisc2

echo "Calculating lengths"
tracklength testdisc1
tracklength testdisc2

echo "Converting disc data to single file"
trackcat testdisc1/*.flac -t flac -q 1 -o testdisc1.flac
trackcat testdisc2/*.wv -t flac -q 1 -o testdisc2.flac

echo "Comparing single files"
trackcmp testdisc1.flac testdisc2.flac

echo "Getting CUE file from cdrdao"
cdrdao read-toc --device /dev/cdrom -v 0 test.toc
toc2cue -v 0 test.toc test.cue

echo "Splitting single file into tracks"
mkdir -v testdisc3
tracksplit --cue test.cue testdisc1.flac -d testdisc3 -t flac -q 1

echo "Comparing split tracks to original files"
trackcmp testdisc3 testdisc1
rm -fv testdisc1.flac testdisc2.flac

echo "Adding album cover"
covertag --front-cover=testcover.png testdisc2/*01*.wv

echo "Checking album cover"
mkdir -v "covers"
coverdump -d covers testdisc2/*01*.wv
cmp testcover.png covers/front_cover.png

echo "Removing test data"
rm -rfv testdisc1 testdisc2 testdisc3
rm -rfv covers
rm -fv test.cue test.toc
