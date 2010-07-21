struct mpeg_header {
    int frame_sync;
    int mpeg_id;
    int layer_description;
    int protection;
    int bitrate;
    int sample_rate;
    int pad;
    int private;
    int channel_assignment;
    int mode_extension;
    int copyright;
    int original;
    int emphasis;
};

status
verifymodule_read_mpeg_header(Bitstream *bs, struct mpeg_header *header);

void
verifymodule_print_mpeg_header(struct mpeg_header *header);

int
verifymodule_mpeg_bitrate(struct mpeg_header *header);

int
verifymodule_mpeg_sample_rate(struct mpeg_header *header);

int
verifymodule_mpeg_channel_count(struct mpeg_header *header);
