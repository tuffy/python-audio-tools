MAN_PATH = /usr/share/man
MAN_PAGES = \
cd2track.1 \
cd2xmcd.1 \
cdinfo.1 \
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
editxmcd.1 \
coverview.1 \
coverdump.1 \
record2track.1 \
tracksplit.1 \
tracklint.1 \
audiotools-config.1

TARGETS = audioformats-letter.pdf audioformats-a4.pdf \
audiotools-letter.pdf audiotools-a4.pdf

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
