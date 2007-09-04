FORMATS = $(FORMAT_BASICS) $(FORMAT_VORBIS) $(FORMAT_MP3) \
format_wav.ms \
format_flac.ms  \
codec_flac.ms \
format_ape.ms \
format_aiff.ms \
format_au.ms  \
format_m4a.ms \
format_xing.ms \
format_wavpack.ms \
format_xmcd.ms \
format_musepack.ms \
format_alac.ms \
format_oggflac.ms \
codec_alac.ms

FORMAT_MP3 = format_mp3.ms \
format_id3v1.ms \
format_id3v2.ms format_id3v2_2.ms format_id3v2_3.ms format_id3v2_4.ms

FORMAT_BASICS = format_basics.ms format_basics_hex.ms format_basics_pcm.ms

FORMAT_VORBIS = format_ogg.ms format_vorbiscomment.ms format_speex.ms

INSTALLATION = install.ms prereqs.ms configfile.ms

SUBSECTIONS = $(INSTALLATION) macros.ms programming.ms freedb.ms usage.ms \
references.ms
FIGURES = binary.eps freedb-sequence.eps pcm.eps rice1.eps
TOC_ORDER_MANUAL = 1,_1-_1,2-_2
TOC_ORDER_FORMATS = 1,_2-_1,2-_3

MAN_PATH = /usr/share/man
MAN_PAGES = \
cd2track.1 \
cd2xmcd.1 \
track2cd.1 \
track2track.1 \
track2xmcd.1 \
trackcat.1 \
trackcmp.1 \
trackinfo.1 \
trackplay.1 \
trackrename.1 \
tracktag.1 \
tracklength.1 \
editxmcd.1

MAN_SECTIONS =  \
cd2track_man.eps \
cd2xmcd_man.eps \
track2cd_man.eps \
track2track_man.eps \
track2xmcd_man.eps \
trackcat_man.eps \
trackcmp_man.eps \
trackinfo_man.eps \
trackplay_man.eps \
trackrename_man.eps \
tracktag_man.eps \
tracklength_man.eps \
editxmcd_man.eps


ifndef PDFLICENSE
  PDFLICENSE = cp -fv
endif


all: audiotools_letter.pdf audiotools_a4.pdf \
audioformats_letter.pdf audioformats_a4.pdf

clean:
	rm -fv *.ps $(MAN_SECTIONS) $(FIGURES) usage.eps *_unlicensed.pdf

distclean: clean
	rm -fv *.pdf

install: $(MAN_PAGES)
	for m in $(MAN_PAGES); do install --mode=644 $$m $(MAN_PATH)/man1/$$m; done

%.pdf: %.ps
	ps2pdf $< > $@


audiotools_letter.pdf: audiotools_letter_unlicensed.pdf
	rm -f $@
	$(PDFLICENSE) $< $@

audiotools_a4.pdf: audiotools_a4_unlicensed.pdf
	rm -f $@
	$(PDFLICENSE) $< $@

audioformats_letter.pdf: audioformats_letter_unlicensed.pdf
	rm -f $@
	$(PDFLICENSE) $< $@

audioformats_a4.pdf: audioformats_a4_unlicensed.pdf
	rm -f $@
	$(PDFLICENSE) $< $@


audiotools_letter_unlicensed.pdf: audiotools_letter.ps properties_audiotools.txt
	gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
-sPAPERSIZE=letter -sOutputFile=$@ audiotools_letter.ps properties_audiotools.txt

audiotools_a4_unlicensed.pdf: audiotools_a4.ps properties_audiotools.txt
	gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
-sPAPERSIZE=a4 -sOutputFile=$@ audiotools_a4.ps properties_audiotools.txt

audioformats_letter_unlicensed.pdf: audioformats_letter.ps properties_audioformats.txt
	gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
-sPAPERSIZE=letter -sOutputFile=$@ audioformats_letter.ps properties_audioformats.txt

audioformats_a4_unlicensed.pdf: audioformats_a4.ps properties_audioformats.txt
	gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
-sPAPERSIZE=a4 -sOutputFile=$@ audioformats_a4.ps properties_audioformats.txt

audiotools_letter.ps: audiotools_letter_unsorted.ps
	psselect -p$(TOC_ORDER_MANUAL) $< $@ 

audiotools_a4.ps: audiotools_a4_unsorted.ps
	psselect -p$(TOC_ORDER_MANUAL) $< $@ 

audioformats_letter.ps: audioformats_letter_unsorted.ps
	psselect -p$(TOC_ORDER_FORMATS) $< $@ 

audioformats_a4.ps: audioformats_a4_unsorted.ps
	psselect -p$(TOC_ORDER_FORMATS) $< $@

audiotools_letter_unsorted.ps: audiotools.ms prereqs.ms install.ms usage.ms usage.eps programming.ms $(MAN_SECTIONS)
	cat audiotools.ms | gsoelim | ./dformat | groff -p -t -e -ms -Tps -dpaper=letter -P-pletter > $@

audiotools_a4_unsorted.ps: audiotools.ms prereqs.ms install.ms usage.ms usage.eps programming.ms $(MAN_SECTIONS)
	cat audiotools.ms | gsoelim | ./dformat | groff -p -t -e -ms -Tps -dpaper=a4 -P-pa4 > $@

audioformats_letter_unsorted.ps: audioformats.ms freedb.ms references.ms $(FORMATS) $(FIGURES)
	cat audioformats.ms | gsoelim | ./dformat | groff -p -t -e -ms -Tps -dpaper=letter -P-pletter > $@

audioformats_a4_unsorted.ps: audioformats.ms freedb.ms references.ms $(FORMATS) $(FIGURES)
	cat audioformats.ms | gsoelim | ./dformat | groff -p -t -e -ms -Tps -dpaper=a4 -P-pa4 > $@

%.ps: %.1
	groff -man $< > $@

%_man.ps: %.1 deman.py
	./deman.py < $< | groff -man > $@

%_man.eps: %_man.ps
	ps2epsi $< $@

freedb-sequence.eps: freedb-sequence.fig
	fig2dev -L eps freedb-sequence.fig freedb-sequence.eps

binary.eps: binary.fig
	fig2dev -L eps binary.fig binary.eps

rice1.eps: rice1.fig
	fig2dev -L eps rice1.fig rice1.eps

pcm.eps: pcm.plot
	./pcm.plot > pcm.eps

usage.eps: usage.fig
	fig2dev -L eps usage.fig usage.eps

