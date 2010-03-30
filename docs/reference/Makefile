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
figures/flac_rice1.pdf figures/flac_rice2.pdf figures/flac_rice3.pdf \
figures/flac_channels.pdf \
figures/flac_stream2.pdf \
figures/flac_nonexhaustive.pdf figures/flac_exhaustive.pdf \
figures/flac_hann.pdf figures/flac_rectangular.pdf figures/flac_tukey.pdf \
figures/flac_lag.pdf \
figures/m4a_quicktime.pdf figures/m4a_atom.pdf figures/m4a_atom2.pdf \
figures/m4a_atoms.pdf figures/m4a_ftyp.pdf figures/m4a_mvhd.pdf \
figures/m4a_tkhd.pdf figures/m4a_mdhd.pdf figures/m4a_hdlr.pdf \
figures/m4a_smhd.pdf figures/m4a_dref.pdf figures/m4a_stsd.pdf \
figures/m4a_mp4a.pdf figures/m4a_stts.pdf figures/m4a_stsc.pdf \
figures/m4a_stsz.pdf figures/m4a_stco.pdf \
figures/m4a_meta_atoms.pdf figures/m4a_meta.pdf figures/m4a_data.pdf \
figures/m4a_trkn.pdf figures/m4a_disk.pdf \
figures/mp3_stream.pdf figures/mp3_xing.pdf \
figures/mp3_id3v1.pdf figures/mp3_id3v11.pdf \
figures/mp3_id3v2_stream.pdf \
figures/mp3_id3v22_header.pdf figures/mp3_id3v22_frame.pdf \
figures/mp3_id3v22_textframe.pdf figures/mp3_id3v22_pic.pdf \
figures/mp3_id3v23_header.pdf figures/mp3_id3v23_frame.pdf \
figures/mp3_id3v23_textframe.pdf figures/mp3_id3v23_apic.pdf

CHAPTERS = basics.tex wav.tex flac.tex m4a.tex mp3.tex

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

figures/flac_rice3.pdf: figures/flac_rice3.fig
	fig2dev -Z 6 -L pdf $< $@

figures/flac_lag.pdf: figures/flac_lag.fig
	fig2dev -Z 6 -L pdf $< $@

figures/flac_nonexhaustive.pdf: figures/flac_nonexhaustive.fig
	fig2dev -Z 3.5 -L pdf $< $@

figures/flac_exhaustive.pdf: figures/flac_exhaustive.fig
	fig2dev -Z 3.5 -L pdf $< $@

figures/m4a_atoms.pdf: figures/m4a_atoms.fig
	fig2dev -Z 6 -L pdf $< $@

figures/m4a_meta_atoms.pdf: figures/m4a_meta_atoms.fig
	fig2dev -Z 3 -L pdf $< $@

.SUFFIXES: .pdf .xml

.xml.pdf:
	./bitdiagram.py -i $< -o $@

figures/m4a_ftyp.pdf: figures/m4a_ftyp.xml
	./bitdiagram.py -w 270 -i $< -o $@

figures/m4a_mvhd.pdf: figures/m4a_mvhd.xml
	./bitdiagram.py -w 270 -i $< -o $@

figures/m4a_meta.pdf: figures/m4a_meta.xml
	./bitdiagram.py -w 306 -i $< -o $@

figures/m4a_data.pdf: figures/m4a_data.xml
	./bitdiagram.py -w 306 -i $< -o $@