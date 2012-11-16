#This makefile is for generating debug standalone executables

VERSION = "2.19beta1"
OBJS = array.o pcm.o bitstream.o
FLAGS = -Wall -g
BINARIES = alacdec flacdec oggflacdec shndec wvdec \
alacenc flacenc oggflacdec shnenc wvenc \
huffman bitstream

all: $(BINARIES)

flacdec: $(OBJS) decoders/flac.c decoders/flac.h flac_crc.o md5.o pcmconv.o
	$(CC) $(FLAGS) -o flacdec decoders/flac.c $(OBJS) flac_crc.o md5.o pcmconv.o -DSTANDALONE -DEXECUTABLE

oggflacdec: $(OBJS) decoders/oggflac.c decoders/oggflac.h flac.o flac_crc.o md5.o pcmconv.o ogg.o ogg_crc.o
	$(CC) $(FLAGS) -o oggflacdec decoders/oggflac.c $(OBJS) flac.o flac_crc.o md5.o pcmconv.o ogg.o ogg_crc.o -DSTANDALONE

wvdec: $(OBJS) decoders/wavpack.c decoders/wavpack.h md5.o pcmconv.o
	$(CC) $(FLAGS) -o wvdec decoders/wavpack.c $(OBJS) md5.o pcmconv.o -DSTANDALONE

alacdec: $(OBJS) decoders/alac.c decoders/alac.h pcmconv.o
	$(CC) $(FLAGS) -o alacdec decoders/alac.c $(OBJS) pcmconv.o -DSTANDALONE

shndec: $(OBJS) decoders/shn.c decoders/shn.h pcmconv.o
	$(CC) $(FLAGS) -o shndec decoders/shn.c $(OBJS) pcmconv.o -DSTANDALONE -lm

flacenc: $(OBJS) encoders/flac.c encoders/flac.h flac_crc.o md5.o pcmconv.o
	$(CC) $(FLAGS) -DVERSION=$(VERSION) -o flacenc encoders/flac.c $(OBJS) md5.o flac_crc.o pcmconv.o -DSTANDALONE -lm

alacenc: $(OBJS) encoders/alac.c encoders/alac.h pcmconv.o
	$(CC) $(FLAGS) -DVERSION=$(VERSION) -o alacenc encoders/alac.c pcmconv.o $(OBJS) -DSTANDALONE -lm

shnenc: $(OBJS) encoders/shn.c encoders/shn.h pcmconv.o
	$(CC) $(FLAGS) -DVERSION=$(VERSION) -o shnenc encoders/shn.c pcmconv.o $(OBJS) -DSTANDALONE -lm

wvenc: $(OBJS) encoders/wavpack.c encoders/wavpack.h md5.o pcmconv.o
	$(CC) $(FLAGS) -o wvenc encoders/wavpack.c md5.o pcmconv.o $(OBJS) -DSTANDALONE

aobdec: decoders/aob.c decoders/aob.h $(OBJS) mlp.o aobpcm.o pcmconv.o
	$(CC) $(FLAGS) -o aobdec decoders/aob.c $(OBJS) mlp.o aobpcm.o pcmconv.o -DSTANDALONE

# mlpdec: decoders/mlp.c decoders/mlp.h array.o bitstream.o
# 	$(CC) $(FLAGS) -o mlpdec decoders/mlp.c array.o bitstream.o -DSTANDALONE

dvdadec: dvda/dvda.c dvda/dvda.h bitstream.o
	$(CC) $(FLAGS) -o dvdadec dvda/dvda.c bitstream.o -DSTANDALONE

huffman: huffman.c huffman.h parson.o
	$(CC) $(FLAGS) -o huffman huffman.c parson.o -DSTANDALONE -DEXECUTABLE

clean:
	rm -f $(BINARIES) *.o

array.o: array.c array.h
	$(CC) $(FLAGS) -c array.c -DSTANDALONE

pcm.o: pcm.c pcm.h
	$(CC) $(FLAGS) -c pcm.c -DSTANDALONE

pcmconv.o: pcmconv.c pcmconv.h
	$(CC) $(FLAGS) -c pcmconv.c -DSTANDALONE

bitstream.o: bitstream.c bitstream.h
	$(CC) $(FLAGS) -c bitstream.c

md5.o: common/md5.c common/md5.h
	$(CC) $(FLAGS) -c common/md5.c -DSTANDALONE

flac.o: decoders/flac.c decoders/flac.h
	$(CC) $(FLAGS) -c decoders/flac.c -DSTANDALONE

mlp.o: decoders/mlp.c decoders/mlp.h
	$(CC) $(FLAGS) -c decoders/mlp.c -DSTANDALONE

aobpcm.o: decoders/aobpcm.c decoders/aobpcm.h
	$(CC) $(FLAGS) -c decoders/aobpcm.c -DSTANDALONE

ogg.o: decoders/ogg.c decoders/ogg.h
	$(CC) $(FLAGS) -c decoders/ogg.c -DSTANDALONE

ogg_crc.o: common/ogg_crc.c common/ogg_crc.h
	$(CC) $(FLAGS) -c common/ogg_crc.c -DSTANDALONE

flac_crc.o: common/flac_crc.c common/flac_crc.h
	$(CC) $(FLAGS) -c common/flac_crc.c -DSTANDALONE

huffman.o: huffman.c huffman.h
	$(CC) $(FLAGS) -c huffman.c -DSTANDALONE

bitstream: bitstream.c bitstream.h huffman.o
	$(CC) $(FLAGS) bitstream.c huffman.o -DEXECUTABLE -o $@

parson.o: parson.c parson.h
	$(CC) $(FLAGS) -c parson.c
