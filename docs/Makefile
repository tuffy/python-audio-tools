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
tracklint.1

install: $(MAN_PAGES)
	for m in $(MAN_PAGES); do install --mode=644 $$m $(MAN_PATH)/man1/$$m; done
	install --mode=644 audiotools.cfg.5 $(MAN_PATH)/man5/audiotools.cfg.5

