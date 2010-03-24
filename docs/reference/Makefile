FIGURES = binary.pdf figures/pcm.pdf figures/wav_stream.pdf \
figures/wav_fmt.pdf figures/wav_fmtext.pdf figures/wav_data.pdf \
figures/flac_stream.pdf figures/flac_streaminfo.pdf \
figures/flac_application.pdf figures/flac_seektable.pdf \
figures/flac_vorbiscomment.pdf

CHAPTERS = basics.tex wav.tex flac.tex

all: audiotools.pdf

clean:
	rm -f *.toc *.aux *.log *.pdf

audiotools.pdf: audiotools.tex audiotools.toc $(CHAPTERS) $(FIGURES)
	pdflatex audiotools.tex

audiotools.toc: audiotools.tex $(CHAPTERS) $(FIGURES)
	pdflatex audiotools.tex

binary.pdf: binary.fig
	fig2dev -L pdf binary.fig binary.pdf

figures/pcm.pdf: figures/pcm.fig
	fig2dev -Z 3 -L pdf $< $@

figures/pcm.fig: figures/pcm.plot
	./figures/pcm.plot > $@

.SUFFIXES: .pdf .xml

.xml.pdf:
	./bitdiagram.py -i $< -o $@

