#This makefile is for generating debug standalone executables

VERSION = "3.0alpha2"
OBJS = array.o pcm.o pcmconv.o bitstream.a
FLAGS = -Wall -g
BINARIES = alacdec \
flacdec \
oggflacdec \
shndec \
wvdec \
alacenc \
flacenc \
oggflacdec \
shnenc \
wvenc \
huffman \
bitstream \
ttaenc \
ttadec

all: $(BINARIES)

clean:
	rm -f $(BINARIES) $(OBJS)

flacdec: $(OBJS) decoders/flac.c decoders/flac.h flac_crc.o md5.o
	$(CC) $(FLAGS) -o flacdec decoders/flac.c $(OBJS) flac_crc.o md5.o -DSTANDALONE -DEXECUTABLE

oggflacdec: $(OBJS) decoders/oggflac.c decoders/oggflac.h flac.o flac_crc.o md5.o ogg.o ogg_crc.o
	$(CC) $(FLAGS) -o oggflacdec decoders/oggflac.c $(OBJS) flac.o flac_crc.o md5.o ogg.o ogg_crc.o -DSTANDALONE

wvdec: $(OBJS) decoders/wavpack.c decoders/wavpack.h md5.o
	$(CC) $(FLAGS) -o wvdec decoders/wavpack.c $(OBJS) md5.o -DSTANDALONE

alacdec: $(OBJS) decoders/alac.c decoders/alac.h
	$(CC) $(FLAGS) -o alacdec decoders/alac.c $(OBJS) -DSTANDALONE

shndec: $(OBJS) decoders/shn.c decoders/shn.h
	$(CC) $(FLAGS) -o shndec decoders/shn.c $(OBJS) -DSTANDALONE -lm

ttadec: $(OBJS) decoders/tta.c decoders/tta.h
	$(CC) $(FLAGS) -o ttadec decoders/tta.c $(OBJS) -DSTANDALONE

flacenc: $(OBJS) encoders/flac.c encoders/flac.h flac_crc.o md5.o
	$(CC) $(FLAGS) -DVERSION=$(VERSION) -o flacenc encoders/flac.c $(OBJS) md5.o flac_crc.o -DSTANDALONE -lm

alacenc: $(OBJS) encoders/alac.c encoders/alac.h
	$(CC) $(FLAGS) -DVERSION=$(VERSION) -o alacenc encoders/alac.c $(OBJS) -DSTANDALONE -lm

shnenc: $(OBJS) encoders/shn.c encoders/shn.h
	$(CC) $(FLAGS) -DVERSION=$(VERSION) -o shnenc encoders/shn.c $(OBJS) -DSTANDALONE -lm

wvenc: $(OBJS) encoders/wavpack.c encoders/wavpack.h md5.o
	$(CC) $(FLAGS) -o wvenc encoders/wavpack.c md5.o $(OBJS) -DSTANDALONE

ttaenc: $(OBJS) encoders/tta.c encoders/tta.h
	$(CC) $(FLAGS) -o ttaenc encoders/tta.c $(OBJS) -DSTANDALONE

aobdec: decoders/aob.c decoders/aob.h $(OBJS) mlp.o aobpcm.o
	$(CC) $(FLAGS) -o aobdec decoders/aob.c $(OBJS) mlp.o aobpcm.o -DSTANDALONE

# mlpdec: decoders/mlp.c decoders/mlp.h array.o bitstream.o
# 	$(CC) $(FLAGS) -o mlpdec decoders/mlp.c array.o bitstream.o -DSTANDALONE

dvdadec: dvda/dvda.c dvda/dvda.h bitstream.a
	$(CC) $(FLAGS) -o dvdadec dvda/dvda.c bitstream.a -DSTANDALONE

vorbisenc: $(OBJS) encoders/vorbis.c
	$(CC) $(FLAGS) -o vorbisenc encoders/vorbis.c $(OBJS) -DSTANDALONE -lvorbis -logg -lvorbisenc

opusenc: $(OBJS) encoders/opus.c
	$(CC) $(FLAGS) -o opusenc encoders/opus.c $(OBJS) -DSTANDALONE `pkg-config --cflags --libs opus ogg`

huffman: huffman.c huffman.h parson.o
	$(CC) $(FLAGS) -o huffman huffman.c parson.o -DSTANDALONE -DEXECUTABLE

pcm.o: pcm.c pcm.h
	$(CC) $(FLAGS) -c pcm.c -DSTANDALONE

pcmconv.o: pcmconv.c pcmconv.h
	$(CC) $(FLAGS) -c pcmconv.c -DSTANDALONE

bitstream.o: bitstream.c bitstream.h
	$(CC) $(FLAGS) -c bitstream.c -DSTANDALONE

md5.o: common/md5.c common/md5.h
	$(CC) $(FLAGS) -c common/md5.c -DSTANDALONE

flac.o: decoders/flac.c decoders/flac.h
	$(CC) $(FLAGS) -c decoders/flac.c -DSTANDALONE

mlp.o: decoders/mlp.c decoders/mlp.h
	$(CC) $(FLAGS) -c decoders/mlp.c -DSTANDALONE

aobpcm.o: decoders/aobpcm.c decoders/aobpcm.h
	$(CC) $(FLAGS) -c decoders/aobpcm.c -DSTANDALONE

ogg.o: ogg.c ogg.h
	$(CC) $(FLAGS) -c ogg.c -DSTANDALONE

ogg_crc.o: ogg_crc.c ogg_crc.h
	$(CC) $(FLAGS) -c ogg_crc.c -DSTANDALONE

flac_crc.o: common/flac_crc.c common/flac_crc.h
	$(CC) $(FLAGS) -c common/flac_crc.c -DSTANDALONE

huffman.o: huffman.c huffman.h
	$(CC) $(FLAGS) -c huffman.c -DSTANDALONE

buffer.o: buffer.c buffer.h
	$(CC) $(FLAGS) -c buffer.c

func_io.o: func_io.c func_io.h
	$(CC) $(FLAGS) -c func_io.c

bitstream.a: bitstream.o huffman.o buffer.o func_io.o
	$(AR) -r $@ bitstream.o huffman.o buffer.o func_io.o

bitstream: bitstream.c bitstream.h huffman.o buffer.o func_io.o
	$(CC) $(FLAGS) bitstream.c huffman.o buffer.o func_io.o -DEXECUTABLE -DSTANDALONE -o $@

array: array.c array.h
	$(CC) $(FLAGS) array.c -DEXECUTABLE -o $@

parson.o: parson.c parson.h
	$(CC) $(FLAGS) -c parson.c
