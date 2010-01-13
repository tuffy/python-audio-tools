OBJS = array.o bitstream_w.o pcmreader.o

flacenc: $(OBJS)
	echo "Hello World"

array.o: array.c array.h
	gcc -c array.c -DSTANDALONE

bitstream_w.o: bitstream_w.c bitstream_w.h
	gcc -c bitstream_w.c -DSTANDALONE

pcmreader.o: pcmreader.c pcmreader.h
	gcc -c pcmreader.c -DSTANDALONE


