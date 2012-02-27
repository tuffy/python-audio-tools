#ifndef INC_CPPM
#define INC_CPPM
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

/* The block size of a DVD. */
const static unsigned DVDCPXM_BLOCK_SIZE = 2048;

struct cppm_decoder {
    int        media_type;     /*read from DVD side data*/
    uint64_t   media_key;      /*read from AUDIO_TS/DVDAUDIO.MKB file*/
    uint64_t   id_album_media; /*pulled from DVD side data*/
};

typedef enum {COPYRIGHT_PROTECTION_NONE = 0,
              COPYRIGHT_PROTECTION_CPPM = 1} protection;

typedef struct {
    uint8_t  col;
    uint16_t row;
    uint64_t key;
} device_key_t;

int
cppm_init(struct cppm_decoder *p_ctx,
          char *dvd_dev,
          char *psz_file);

int
cppm_set_id_album(struct cppm_decoder *p_ctx,
                  int i_fd);

uint8_t*
cppm_get_mkb(char *psz_mkb);

int
cppm_process_mkb(uint8_t *p_mkb,
                 device_key_t *p_dev_keys,
                 int nr_dev_keys,
                 uint64_t *p_media_key);

int
cppm_decrypt(struct cppm_decoder *p_ctx,
             uint8_t *p_buffer,
             int nr_blocks,
             int preserve_cci);

int
cppm_decrypt_block(struct cppm_decoder *p_ctx,
                   uint8_t *p_buffer,
                   int preserve_cci);

/*given a block of raw AOB data, determine if its protection bit is set*/
int
mpeg2_check_pes_scrambling_control(uint8_t *p_block);

/*sets a block's protection bit to 0*/
void
mpeg2_reset_pes_scrambling_control(uint8_t *p_block);

/*locates a block's CCI bit and sets it to 0*/
void
mpeg2_reset_cci(uint8_t *p_block);
#endif
