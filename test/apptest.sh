#!/bin/sh

echo "Getting XMCD info from CD"
cd2xmcd -x testdisc1.xmcd

echo "Extracting CD"
mkdir -v testdisc1
cd2track -t wav -d testdisc1

echo "Transcoding CD"
mkdir -v testdisc2
track2track -t flac -q 1 testdisc1/*.wav -d testdisc2 -x testdisc1.xmcd

echo "Getting info"
trackinfo testdisc2/*.flac

echo "Comparing CD to original"
trackcmp testdisc1 testdisc2

echo "Calculating lengths"
tracklength testdisc1
tracklength testdisc2

echo "Converting disc data to single file"
trackcat testdisc1/*.wav -t flac -q 1 -o testdisc1.flac
trackcat testdisc2/*.flac -t flac -q 1 -o testdisc2.flac
echo "Comparing single files"
trackcmp testdisc1.flac testdisc2.flac
rm -fv testdisc1.flac testdisc2.flac

echo "Removing transcoded CD and trying again"
rm -rfv testdisc2
mkdir -v testdisc2
track2track -t flac -q 1 testdisc1/*.wav -d testdisc2
trackrename -x testdisc1.xmcd testdisc2/*.flac
trackcmp testdisc1 testdisc2

echo "Grabbing metadata from transcoded CD and comparing"
track2xmcd -x testdisc2.xmcd testdisc2/*.flac
diff -q testdisc1.xmcd testdisc2.xmcd

echo "Adding album cover"
tracktag --front-cover=testcover.png testdisc2/*01*.flac

echo "Checking album cover"
mkdir -v "covers"
coverdump -d covers testdisc2/*01*.flac
cmp testcover.png covers/front_cover.png

echo "Removing test data"
rm -fv testdisc1.xmcd testdisc2.xmcd
rm -rfv testdisc1 testdisc2
rm -rfv covers