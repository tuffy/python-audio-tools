struct ogg_header {
    uint32_t magic_number;
    uint8_t version;
    uint8_t header_type;
    uint64_t granule_position;
    uint32_t bitstream_serial_number;
    uint32_t page_sequence_number;
    uint32_t checksum;
    uint8_t page_segment_count;
    uint8_t page_segment_lengths[0x100];
};
