PYTHON = python
MAN_PATH = /usr/share/man
MAN_PAGES = \
audiotools-config.1 \
audiotools.cfg.5 \
cd2track.1 \
cdinfo.1 \
cdplay.1 \
coverdump.1 \
covertag.1 \
coverview.1 \
dvda2track.1 \
dvdainfo.1 \
track2cd.1 \
track2track.1 \
trackcat.1 \
trackcmp.1 \
trackinfo.1 \
tracklength.1 \
tracklint.1 \
trackplay.1 \
trackrename.1 \
tracksplit.1 \
tracktag.1 \
trackverify.1

MAN_SOURCES = \
audiotools-config.xml \
audiotools.cfg.xml \
cd2track.xml \
cdinfo.xml \
cdplay.xml \
coverdump.xml \
covertag.xml \
coverview.xml \
dvda2track.xml \
dvdainfo.xml \
track2cd.xml \
track2track.xml \
trackcat.xml \
trackcmp.xml \
trackinfo.xml \
tracklength.xml \
tracklint.xml \
trackplay.xml \
trackrename.xml \
tracksplit.xml \
tracktag.xml \
trackverify.xml

.SUFFIXES: .xml .1 .5

.xml.1:
	$(PYTHON) manpagexml.py -i $< $(MAN_SOURCES) > $@

.xml.5:
	$(PYTHON) manpagexml.py -i $< $(MAN_SOURCES) > $@

TARGETS = audioformats-letter.pdf audioformats-a4.pdf \
audiotools-letter.pdf audiotools-a4.pdf \
$(MAN_PAGES)

all: $(TARGETS)

clean: .FORCE
	rm -fv $(TARGETS)

.FORCE:

install: $(MAN_PAGES)
	for m in $(MAN_PAGES); do install -m 644 $$m $(MAN_PATH)/man1/$$m; done
	install -m 644 audiotools.cfg.5 $(MAN_PATH)/man5/audiotools.cfg.5

audioformats-letter.pdf:
	cd reference && make audioformats-letter.pdf
	cp -fv reference/audioformats-letter.pdf .

audioformats-a4.pdf:
	cd reference && make audioformats-a4.pdf
	cp -fv reference/audioformats-a4.pdf .

audiotools-letter.pdf:
	sphinx-build -b latex -d programming/build/doctrees/ -D latex_paper_size=letter programming/source/ programming/build/latex/letter
	cd programming/build/latex/letter && make PythonAudioTools.pdf
	cp -fv programming/build/latex/letter/PythonAudioTools.pdf $@
	python pdftag.py "--title=Python Audio Tools Documentation" "--author=Brian Langenberger" $@

audiotools-a4.pdf:
	sphinx-build -b latex -d programming/build/doctrees/ -D latex_paper_size=a4 programming/source/ programming/build/latex/a4
	cd programming/build/latex/a4 && make PythonAudioTools.pdf
	cp -fv programming/build/latex/a4/PythonAudioTools.pdf $@
	python pdftag.py "--title=Python Audio Tools Documentation" "--author=Brian Langenberger" $@
