FIGURES = binary.pdf

CHAPTERS = basics.tex

all: audiotools.pdf

clean:
	rm -f *.toc *.aux *.log *.pdf

audiotools.pdf: audiotools.tex audiotools.toc $(CHAPTERS) $(FIGURES)
	pdflatex audiotools.tex

audiotools.toc: audiotools.tex $(CHAPTERS) $(FIGURES)
	pdflatex audiotools.tex

binary.pdf: binary.fig
	fig2dev -L pdf binary.fig binary.pdf
