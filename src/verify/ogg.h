struct ogg_header {
    uint32_t magic_number;
    uint8_t version;
    uint8_t type;
    uint64_t granule_position;
    uint32_t bitstream_serial_number;
    uint32_t page_sequence_number;
    uint32_t checksum;
    uint8_t page_segment_count;
    uint8_t page_segment_lengths[0x100];
    uint32_t segment_length_total;
};

status
verifymodule_read_ogg_header(Bitstream *bs, struct ogg_header *header);

void
verifymodule_print_ogg_header(struct ogg_header *header);

void
verifymodule_ogg_checksum(uint8_t byte, void *checksum);
