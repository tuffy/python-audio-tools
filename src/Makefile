#This makefile is for generating debug standalone executables

FLAGS = -Wall -g
BINARIES = \
alacdec \
shndec \
wvdec \
alacenc \
flacenc \
shnenc \
wvenc \
huffman \
bitstream \
bitstream-table \
ttaenc \
opusenc

all: $(BINARIES)

clean:
	rm -f $(BINARIES) *.o *.a

alacdec: $(OBJS) decoders/alac.c decoders/alac.h pcm_conv.o
	$(CC) $(FLAGS) -o alacdec decoders/alac.c $(OBJS) pcm_conv.o -DSTANDALONE

shndec: $(OBJS) decoders/shn.c decoders/shn.h buffer.o pcm_conv.o
	$(CC) $(FLAGS) -o shndec decoders/shn.c $(OBJS) buffer.o pcm_conv.o -DSTANDALONE -lm

wvdec: $(OBJS) decoders/wavpack.c decoders/wavpack.h md5.o pcm_conv.o
	$(CC) $(FLAGS) -o wvdec decoders/wavpack.c $(OBJS) md5.o pcm_conv.o -DSTANDALONE

alacenc: encoders/alac.c encoders/alac.h bitstream.a array.o pcmreader.o pcm_conv.o m4a_atoms.o
	$(CC) $(FLAGS) -o alacenc encoders/alac.c bitstream.a array.o pcmreader.o pcm_conv.o m4a_atoms.o -DSTANDALONE -lm

flacenc: encoders/flac.c encoders/flac.h bitstream.a pcmreader.o pcm_conv.o md5.o flac_crc.o
	$(CC) $(FLAGS) -o $@ encoders/flac.c bitstream.a pcmreader.o pcm_conv.o md5.o flac_crc.o -DSTANDALONE -DEXECUTABLE -lm

shnenc: encoders/shn.c encoders/shn.h bitstream.a array.o pcmreader.o pcm_conv.o
	$(CC) $(FLAGS) -o shnenc encoders/shn.c bitstream.a array.o pcmreader.o pcm_conv.o -DSTANDALONE -lm

wvenc: $(OBJS) encoders/wavpack.c pcmreader.o pcm_conv.o bitstream.a md5.o
	$(CC) $(FLAGS) -o wvenc encoders/wavpack.c pcmreader.o pcm_conv.o bitstream.a md5.o -DSTANDALONE `pkg-config --cflags --libs wavpack`

ttaenc: encoders/tta.c encoders/tta.h pcmreader.o pcm_conv.o bitstream.a
	$(CC) $(FLAGS) -o ttaenc encoders/tta.c pcmreader.o pcm_conv.o bitstream.a -DSTANDALONE

vorbisenc: $(OBJS) encoders/vorbis.c
	$(CC) $(FLAGS) -o vorbisenc encoders/vorbis.c $(OBJS) -DSTANDALONE -lvorbis -logg -lvorbisenc

opusenc: $(OBJS) encoders/opus.c bitstream.a pcm_conv.o pcmreader.o
	$(CC) $(FLAGS) -o opusenc encoders/opus.c bitstream.a pcm_conv.o pcmreader.o -DSTANDALONE `pkg-config --cflags --libs opus ogg`

huffman: huffman.c huffman.h parson.o
	$(CC) $(FLAGS) -o huffman huffman.c parson.o -DEXECUTABLE

pcm.o: pcm.c pcm.h
	$(CC) $(FLAGS) -c pcm.c -DSTANDALONE

pcmconv.o: pcmconv.c pcmconv.h
	$(CC) $(FLAGS) -c pcmconv.c -DSTANDALONE

framelist.o: framelist.c framelist.c
	$(CC) $(FLAGS) -c framelist.c -DSTANDALONE

pcm_conv.o: pcm_conv.h pcm_conv.c
	$(CC) $(FLAGS) -c pcm_conv.c

pcmreader: pcmreader.h pcmreader.c pcm.o
	$(CC) -Wall -g -o $@ pcmreader.c pcm.o -DSTANDALONE -DEXECUTABLE

pcmreader.o: pcmreader.c pcmreader.h
	$(CC) $(FLAGS) -c pcmreader.c -DSTANDALONE

bitstream.o: bitstream.c bitstream.h
	$(CC) $(FLAGS) -c bitstream.c

md5.o: common/md5.c common/md5.h
	$(CC) $(FLAGS) -c common/md5.c -DSTANDALONE

flac.o: decoders/flac.c decoders/flac.h
	$(CC) $(FLAGS) -c decoders/flac.c -DSTANDALONE

ogg.o: ogg.c ogg.h
	$(CC) $(FLAGS) -c ogg.c -DSTANDALONE

ogg_crc.o: ogg_crc.c ogg_crc.h
	$(CC) $(FLAGS) -c ogg_crc.c -DSTANDALONE

flac_crc.o: common/flac_crc.c common/flac_crc.h
	$(CC) $(FLAGS) -c common/flac_crc.c -DSTANDALONE

huffman.o: huffman.c huffman.h
	$(CC) $(FLAGS) -c huffman.c -DSTANDALONE

array.o: array.c array.h
	$(CC) $(FLAGS) -c array.c

buffer.o: buffer.c buffer.h
	$(CC) $(FLAGS) -c buffer.c

func_io.o: func_io.c func_io.h
	$(CC) $(FLAGS) -c func_io.c

mini-gmp.o: mini-gmp.c mini-gmp.h
	$(CC) $(FLAGS) -c mini-gmp.c

m4a_atoms.o: common/m4a_atoms.c common/m4a_atoms.h
	$(CC) $(FLAGS) -c common/m4a_atoms.c

bitstream.a: bitstream.o huffman.o func_io.o mini-gmp.o
	$(AR) -r $@ bitstream.o huffman.o func_io.o mini-gmp.o

bitstream: bitstream.c bitstream.h huffman.o func_io.o mini-gmp.o
	$(CC) $(FLAGS) bitstream.c huffman.o func_io.o mini-gmp.o -DEXECUTABLE -DDEBUG -o $@

array: array.c array.h
	$(CC) $(FLAGS) array.c -DEXECUTABLE -o $@

parson.o: parson.c parson.h
	$(CC) $(FLAGS) -c parson.c

bitstream-table: bitstream-table.c
	$(CC) $(FLAGS) -o $@ bitstream-table.c

m4a-atoms: common/m4a_atoms.c common/m4a_atoms.h bitstream.a
	$(CC) $(FLAGS) -o $@ common/m4a_atoms.c bitstream.a -DSTANDALONE
