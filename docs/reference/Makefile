FIGURES = binary.pdf figures/pcm.pdf figures/wav_stream.pdf \
figures/wav_fmt.pdf figures/wav_fmtext.pdf

CHAPTERS = basics.tex wav.tex

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

figures/wav_stream.pdf: figures/wav_stream.xml
	./bitdiagram.py -i $< -o $@

figures/wav_fmt.pdf: figures/wav_fmt.xml
	./bitdiagram.py -i $< -o $@

figures/wav_fmtext.pdf: figures/wav_fmtext.xml
	./bitdiagram.py -i $< -o $@