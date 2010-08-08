#FIXME - reorganize this big mess
FIGURES = binary.pdf figures/pcm.pdf figures/wav_stream.pdf \
figures/wav_fmt.pdf figures/wav_fmtext.pdf figures/wav_data.pdf \
figures/aiff_stream.pdf figures/aiff_comm.pdf figures/aiff_ssnd.pdf \
figures/au_stream.pdf \
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
figures/flac_lag.pdf figures/oggflac_stream.pdf \
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
figures/mp3_id3v23_textframe.pdf figures/mp3_id3v23_apic.pdf \
figures/mp3_id3v24_header.pdf figures/mp3_id3v24_frame.pdf \
figures/mp3_id3v24_textframe.pdf figures/mp3_id3v24_apic.pdf \
figures/ogg_stream.pdf figures/ogg_packets.pdf \
figures/vorbis_identification.pdf figures/vorbis_comment.pdf \
figures/wavpack_stream.pdf figures/wavpack_block_header.pdf \
figures/wavpack_subblock_header.pdf \
figures/wavpack_decorr_terms.pdf figures/wavpack_decorr_weights.pdf \
figures/wavpack_decorr_samples.pdf \
figures/ape_stream.pdf figures/ape_descriptor.pdf figures/ape_header.pdf \
figures/apev2_tag.pdf figures/apev2_tagheader.pdf figures/apev2_flags.pdf \
figures/speex_header.pdf \
figures/musepack_sv7_stream.pdf figures/musepack_sv8_stream.pdf \
figures/musepack_sv8_sh.pdf figures/musepack_sv8_rg.pdf \
figures/musepack_sv8_ei.pdf figures/musepack_sv8_nut.pdf \
figures/freedb_sequence.pdf figures/freedb_discid.pdf \
figures/musicbrainz_discid.pdf figures/musicbrainz_xml.pdf \
figures/shorten_stream.pdf figures/shorten_unsigned.pdf \
figures/shorten_signed.pdf figures/shorten_diff.pdf \
figures/shorten_verbatim.pdf figures/shorten_qlpc.pdf \
figures/shorten_sandwich.pdf \
figures/alac_stream.pdf figures/alac_atoms.pdf figures/alac_alac_atom.pdf \
figures/alac_frame_header.pdf figures/alac_subframe_header.pdf \
figures/alac_uncompressed_frame.pdf figures/alac_compressed_frame.pdf \
figures/alac_read_residual.pdf figures/alac_residual.pdf \
figures/alac_wasted.pdf figures/alac_write_residual.pdf \
figures/alac_residual_w.pdf figures/alac_lag.pdf \
figures/bitstream_struct.pdf figures/bitstream_bigendian.pdf \
figures/bitstream_littleendian.pdf figures/bitstream_littleendian_alt.pdf

CHAPTERS = basics.tex wav.tex flac.tex m4a.tex mp3.tex vorbis.tex \
wavpack.tex ape.tex aiff.tex au.tex speex.tex oggflac.tex musepack.tex \
freedb.tex musicbrainz.tex musicbrainz_mmd.tex replaygain.tex references.tex \
license.tex introduction.tex shorten.tex alac.tex

all: audioformats-letter.pdf audioformats-a4.pdf

clean:
	rm -f *.toc *.aux *.log *.out $(FIGURES)
	rm -f figures/pcm.fig figures/flac_hann.fig figures/flac_rectangular.fig figures/flac_tukey.fig
	rm -f audiotools-a4.tex audiotools-letter.tex

audioformats-letter.pdf: audioformats-letter.tex $(CHAPTERS) $(FIGURES)
	python pdflatexbuild.py -halt-on-error audioformats-letter.tex
	python ../pdftag.py "--title=Audio Formats Reference" "--author=Brian Langenberger" $@

audioformats-a4.pdf: audioformats-a4.tex $(CHAPTERS) $(FIGURES)
	python pdflatexbuild.py -halt-on-error audioformats-a4.tex
	python ../pdftag.py "--title=Audio Formats Reference" "--author=Brian Langenberger" $@

audioformats-letter.tex: audioformats.m4
	m4 -D PAPERSIZE=letterpaper $< > $@

audioformats-a4.tex: audioformats.m4
	m4 -D PAPERSIZE=a4paper $< > $@

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

figures/freedb_sequence.pdf: figures/freedb_sequence.fig
	fig2dev -Z 4 -L pdf $< $@

figures/musicbrainz_xml.pdf: figures/musicbrainz_xml.fig
	fig2dev -Z 4 -L pdf $< $@

figures/m4a_atoms.pdf: figures/m4a_atoms.fig
	fig2dev -Z 6 -L pdf $< $@

figures/m4a_meta_atoms.pdf: figures/m4a_meta_atoms.fig
	fig2dev -Z 3 -L pdf $< $@

figures/alac_atoms.pdf: figures/alac_atoms.fig
	fig2dev -Z 5 -L pdf $< $@

figures/alac_read_residual.pdf: figures/alac_read_residual.fig
	fig2dev -Z 5 -L pdf $< $@

figures/alac_write_residual.pdf: figures/alac_write_residual.fig
	fig2dev -Z 5 -L pdf $< $@

figures/alac_residual.pdf: figures/alac_residual.fig
	fig2dev -Z 5 -L pdf $< $@

figures/alac_residual_w.pdf: figures/alac_residual_w.fig
	fig2dev -Z 5 -L pdf $< $@

figures/alac_lag.pdf: figures/alac_lag.fig
	fig2dev -Z 6 -L pdf $< $@

figures/bitstream_bigendian.pdf: figures/bitstream_bigendian.fig
	fig2dev -Z 6 -L pdf $< $@

figures/bitstream_littleendian.pdf: figures/bitstream_littleendian.fig
	fig2dev -Z 6 -L pdf $< $@

figures/bitstream_littleendian_alt.pdf: figures/bitstream_littleendian_alt.fig
	fig2dev -Z 6 -L pdf $< $@

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

figures/alac_alac_atom.pdf: figures/alac_alac_atom.xml
	./bitdiagram.py -w 324 -i $< -o $@

figures/shorten_unsigned.pdf: figures/shorten_unsigned.fig
	fig2dev -Z 2 -L pdf $< $@

figures/shorten_signed.pdf: figures/shorten_signed.fig
	fig2dev -Z 2 -L pdf $< $@
