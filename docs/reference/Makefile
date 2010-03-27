#FIXME - reorganize this big mess
FIGURES = binary.pdf figures/pcm.pdf figures/wav_stream.pdf \
figures/wav_fmt.pdf figures/wav_fmtext.pdf figures/wav_data.pdf \
figures/flac_stream.pdf figures/flac_streaminfo.pdf \
figures/flac_application.pdf figures/flac_seektable.pdf \
figures/flac_vorbiscomment.pdf figures/flac_cuesheet.pdf \
figures/flac_picture.pdf \
figures/flac_frame.pdf \
figures/flac_verbatim.pdf figures/flac_fixed.pdf figures/flac_lpc.pdf \
figures/flac_residual.pdf \
figures/flac_rice1.pdf figures/flac_rice2.pdf \
figures/flac_channels.pdf \
figures/flac_stream2.pdf \
figures/flac_nonexhaustive.pdf figures/flac_exhaustive.pdf \
figures/flac_hann.pdf figures/flac_rectangular.pdf figures/flac_tukey.pdf \
figures/flac_lag.pdf

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

figures/flac_hann.pdf: figures/flac_hann.fig
	fig2dev -Z 2 -L pdf $< $@

figures/flac_hann.fig: figures/flac_hann.plot
	./figures/flac_hann.plot > $@

figures/flac_rectangular.pdf: figures/flac_rectangular.fig
	fig2dev -Z 2 -L pdf $< $@

figures/flac_rectangular.fig: figures/flac_rectangular.plot
	./figures/flac_rectangular.plot > $@

figures/flac_tukey.pdf: figures/flac_tukey.fig
	fig2dev -Z 2 -L pdf $< $@

figures/flac_tukey.fig: figures/flac_tukey.plot
	./figures/flac_tukey.plot > $@

figures/flac_rice1.pdf: figures/flac_rice1.fig
	fig2dev -Z 5 -L pdf $< $@

figures/flac_rice2.pdf: figures/flac_rice2.fig
	fig2dev -Z 6 -L pdf $< $@

figures/flac_lag.pdf: figures/flac_lag.fig
	fig2dev -Z 6 -L pdf $< $@

figures/flac_nonexhaustive.pdf: figures/flac_nonexhaustive.fig
	fig2dev -Z 3.5 -L pdf $< $@

figures/flac_exhaustive.pdf: figures/flac_exhaustive.fig
	fig2dev -Z 3.5 -L pdf $< $@

.SUFFIXES: .pdf .xml

.xml.pdf:
	./bitdiagram.py -i $< -o $@

