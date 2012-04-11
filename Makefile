PYTHON = python

all:
	$(PYTHON) setup.py build

install: .FORCE
	$(PYTHON) setup.py install
	cd docs && $(MAKE) install

check: .FORCE
	cd test && $(PYTHON) test.py

clean: .FORCE
	rm -rfv build
	rm -fv audiotools/*.pyc

distclean: clean
	cd docs && $(MAKE) clean

.FORCE:

construct:
	### This target is no longer required ###

construct_install:
	### This target is no longer required ###


#translation specific targets below

EXECUTABLES = \
audiotools_config \
cd2track \
cdinfo \
cdplay \
coverdump \
coverview \
dvda2track \
dvdainfo \
track2cd \
track2track \
trackcat \
trackcmp \
trackinfo \
tracklength \
tracklint \
trackplay \
trackrename \
tracksplit \
tracktag

MODULES = \
__aiff__.py \
__ape__.py \
__au__.py \
__dvda__.py \
__flac__.py \
__id3__.py \
__id3v1__.py \
__image__.py \
__init__.py \
__m4a__.py \
__m4a_atoms__.py \
__mp3__.py \
__musepack__.py \
__ogg__.py \
__shn__.py \
__vorbis__.py \
__vorbiscomment__.py \
__wav__.py \
__wavpack__.py \
cue.py \
delta.py \
freedb.py \
musicbrainz.py \
player.py \
toc.py \
ui.py

audiotools.mo: en_US.po
	msgfmt $< --output-file=$@

en_US.po: audiotools.pot
	msginit --input=$< --locale=en_US --output-file=$@

audiotools.pot: audiotools-cli.pot audiotools-gui.pot
	msgcat -o audiotools.pot audiotools-cli.pot audiotools-gui.pot

audiotools-cli.pot: $(EXECUTABLES) $(MODULES)
	xgettext -L Python --keyword=_ --output=$@ $(EXECUTABLES) $(MODULES)

audiotools-gui.pot: $(GLADE_H_FILES)
	xgettext --keyword=N_ --from-code=UTF-8 --output=$@ $(GLADE_H_FILES)
