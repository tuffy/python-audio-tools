#include "cppm.h"
#include "ioctl.h"
#include "dvd_css.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

/* The block size of a DVD. */
#define DVDCPXM_BLOCK_SIZE     2048

int
CPPMDecoder_init(prot_CPPMDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    char *mkb_file;
    char *dvda_device;

    self->media_type = 0;
    self->media_key = 0;
    self->id_album_media = 0;

    if (!PyArg_ParseTuple(args, "ss", &dvda_device, &mkb_file))
        return -1;

    /*initialize the decoder from the device path and mkb_file path*/
    switch (cppm_init(self, dvda_device, mkb_file)) {
    case -1: /*I/O error*/
        PyErr_SetFromErrno(PyExc_IOError);
        return -1;
    case -2: /*unsupported protection type*/
        PyErr_SetString(PyExc_ValueError, "unsupported protection type");
        return -1;
    default: /*all okay*/
        break;
    }

    return 0;
}

void
CPPMDecoder_dealloc(prot_CPPMDecoder *self)
{
    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
CPPMDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    prot_CPPMDecoder *self;

    self = (prot_CPPMDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
CPPMDecoder_media_type(prot_CPPMDecoder *self, void *closure) {
    return Py_BuildValue("i", self->media_type);
}

static PyObject*
CPPMDecoder_media_key(prot_CPPMDecoder *self, void *closure) {
    return Py_BuildValue("K", self->media_key);
}

static PyObject*
CPPMDecoder_id_album_media(prot_CPPMDecoder *self, void *closure) {
    return Py_BuildValue("K", self->id_album_media);
}

static PyObject*
CPPMDecoder_decode(prot_CPPMDecoder *self, PyObject *args) {
    char* input_buffer;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t input_len;
#else
    int input_len;
#endif
    uint8_t* output_buffer;
    int output_len;
    PyObject* decoded;

    if (!PyArg_ParseTuple(args, "s#", &input_buffer, &input_len))
        return NULL;

    if (input_len % DVDCPXM_BLOCK_SIZE) {
        PyErr_SetString(PyExc_ValueError,
                        "encoded block must be a multiple of 2048");
        return NULL;
    }

    output_len = input_len;
    output_buffer = malloc(sizeof(uint8_t) * output_len);
    memcpy(output_buffer, input_buffer, input_len);

    cppm_decrypt(self,
                 output_buffer,
                 output_len / DVDCPXM_BLOCK_SIZE,
                 1);

    decoded = PyString_FromStringAndSize((char *)output_buffer,
                                         (Py_ssize_t)output_len);
    free(output_buffer);
    return decoded;
}

#define B2N_16(x)                               \
  x = ((((x) & 0xff00) >> 8) |                  \
       (((x) & 0x00ff) << 8))
#define B2N_32(x)                               \
  x = ((((x) & 0xff000000) >> 24) |             \
       (((x) & 0x00ff0000) >>  8) |             \
       (((x) & 0x0000ff00) <<  8) |             \
       (((x) & 0x000000ff) << 24))
#define B2N_64(x)                               \
  x = ((((x) & 0xff00000000000000LL) >> 56) |     \
       (((x) & 0x00ff000000000000LL) >> 40) |     \
       (((x) & 0x0000ff0000000000LL) >> 24) |     \
       (((x) & 0x000000ff00000000LL) >>  8) |     \
       (((x) & 0x00000000ff000000LL) <<  8) |     \
       (((x) & 0x0000000000ff0000LL) << 24) |     \
       (((x) & 0x000000000000ff00LL) << 40) |     \
       (((x) & 0x00000000000000ffLL) << 56))

const static uint8_t sbox[256] = {
    0x3a, 0xd0, 0x9a, 0xb6, 0xf5, 0xc1, 0x16, 0xb7,
    0x58, 0xf6, 0xed, 0xe6, 0xd9, 0x8c, 0x57, 0xfc,
    0xfd, 0x4b, 0x9b, 0x47, 0x0e, 0x8e, 0xff, 0xf3,
    0xbb, 0xba, 0x0a, 0x80, 0x15, 0xd7, 0x2b, 0x36,
    0x6a, 0x43, 0x5a, 0x89, 0xb4, 0x5d, 0x71, 0x19,
    0x8f, 0xa0, 0x88, 0xb8, 0xe8, 0x8a, 0xc3, 0xae,
    0x7c, 0x4e, 0x3d, 0xb5, 0x96, 0xcc, 0x21, 0x00,
    0x1a, 0x6b, 0x12, 0xdb, 0x1f, 0xe4, 0x11, 0x9d,
    0xd3, 0x93, 0x68, 0xb0, 0x7f, 0x3b, 0x52, 0xb9,
    0x94, 0xdd, 0xa5, 0x1b, 0x46, 0x60, 0x31, 0xec,
    0xc9, 0xf8, 0xe9, 0x5e, 0x13, 0x98, 0xbf, 0x27,
    0x56, 0x08, 0x91, 0xe3, 0x6f, 0x20, 0x40, 0xb2,
    0x2c, 0xce, 0x02, 0x10, 0xe0, 0x18, 0xd5, 0x6c,
    0xde, 0xcd, 0x87, 0x79, 0xaf, 0xa9, 0x26, 0x50,
    0xf2, 0x33, 0x92, 0x6e, 0xc0, 0x3f, 0x39, 0x41,
    0xaa, 0x5b, 0x7d, 0x24, 0x03, 0xd6, 0x2f, 0xeb,
    0x0b, 0x99, 0x86, 0x4c, 0x51, 0x45, 0x8d, 0x2e,
    0xef, 0x07, 0x7b, 0xe2, 0x4d, 0x7a, 0xfe, 0x25,
    0x5c, 0x29, 0xa2, 0xa8, 0xb1, 0xf0, 0xb3, 0xc4,
    0x30, 0x7e, 0x63, 0x38, 0xcb, 0xf4, 0x4f, 0xd1,
    0xdf, 0x44, 0x32, 0xdc, 0x17, 0x5f, 0x66, 0x2a,
    0x81, 0x9e, 0x77, 0x4a, 0x65, 0x67, 0x34, 0xfa,
    0x54, 0x1e, 0x14, 0xbe, 0x04, 0xf1, 0xa7, 0x9c,
    0x8b, 0x37, 0xee, 0x85, 0xab, 0x22, 0x0f, 0x69,
    0xc5, 0xd4, 0x05, 0x84, 0xa4, 0x73, 0x42, 0xa1,
    0x64, 0xe1, 0x70, 0x83, 0x90, 0xc2, 0x48, 0x0d,
    0x61, 0x1c, 0xc6, 0x72, 0xfb, 0x76, 0x74, 0xe7,
    0x01, 0xd8, 0xc8, 0xd2, 0x75, 0xa3, 0xcf, 0x28,
    0x82, 0x1d, 0x49, 0x35, 0xc7, 0xbd, 0xca, 0xa6,
    0xac, 0x0c, 0x62, 0xad, 0xf9, 0x3c, 0xea, 0x2d,
    0x59, 0xda, 0x3e, 0x97, 0x6d, 0x09, 0xf7, 0x55,
    0xe5, 0x23, 0x53, 0x9f, 0x06, 0xbc, 0x95, 0x78,
};

/*Do these vary from CPU to CPU?
  Otherwise, why does the reference lib initialize them at run-time
  instead of predefining them at compile-time?*/
const static uint32_t sbox_f[256] = {
    0xCF22BE3A, 0x647F6BD1, 0x4D36FF98, 0xFDB3A7B5,
    0xF0DB21F1, 0x205D49C4, 0x7FA7E610, 0xF993A5B0,
    0x466E7A50, 0xFCBB27FF, 0x90D811E7, 0xBCB907ED,
    0x405E79D5, 0x15F4D381, 0x7A8F6459, 0xD4FA33F3,
    0xD0DA31ED, 0x0A0C5C5A, 0x4916FD89, 0x3A8D4454,
    0x1FA4D61A, 0x1DB4D79B, 0xD89A35E9, 0xE81B2DE4,
    0xC912BDA3, 0xCD32BFA3, 0x0F24DE10, 0x2575CB9B,
    0x73C7E009, 0x789F65CA, 0x8B009C35, 0xFFA3A629,
    0x8E281E4A, 0x2A0D4C62, 0x4E2E7E78, 0x0154D9AA,
    0xF5F3A390, 0x52CE7078, 0xE24B2857, 0x4346F83E,
    0x1994D5A7, 0xA5718B89, 0x0574DBA2, 0xC572BB93,
    0x84781BC4, 0x0D34DFA7, 0x281D4DED, 0x9DB09781,
    0xD6EA324C, 0x1EAC567F, 0xD3C2B00F, 0xF1D3A186,
    0x7DB7E7A2, 0x14FC53F9, 0xA3418817, 0x2765CA37,
    0x4F26FE22, 0x8A081C52, 0x6F27EE28, 0x481E7DE0,
    0x5B86F423, 0xB4F903D9, 0x6347E82F, 0x51D6F1A2,
    0x681F6D93, 0x6917EDD2, 0x86681A2A, 0xE573ABF3,
    0xDA8A343B, 0xCB02BC7E, 0x6E2F6E14, 0xC152B9FE,
    0x75F7E3DC, 0x50DE7194, 0xB1D181EF, 0x4B06FC50,
    0x3EAD460A, 0xA6690A2D, 0xE343A87F, 0x94F813A3,
    0x005C5999, 0xC47A3BA9, 0x805819BB, 0x5EAE760D,
    0x6B07EC47, 0x4576FBCD, 0xD992B5E9, 0xBB818470,
    0x7EAF660E, 0x0764DA51, 0x6157E9CB, 0xA8190DB8,
    0x9A881433, 0xA7618A7D, 0x266D4A1E, 0xED33AFED,
    0x97E0924C, 0x1CBC57AF, 0x2F25CE60, 0x6767EA73,
    0xA4790B84, 0x4766FA7D, 0x70DF61B3, 0x96E8120B,
    0x5CBE77B6, 0x10DC51A4, 0x3995C5ED, 0xC24A3812,
    0x999095C3, 0x815099C4, 0xBFA18648, 0x666F6A3F,
    0xEC3B2F82, 0xEB03AC42, 0x6D37EFE0, 0x9EA8161D,
    0x247D4BB4, 0xDB82B44A, 0xC342B84F, 0x224D4836,
    0x8D309FD2, 0x4A0E7C22, 0xD2CA3007, 0xB7E1825F,
    0x2B05CC7F, 0x7CBF67AB, 0x9B809451, 0x88181D94,
    0x0B04DC8B, 0x4156F918, 0x3DB5C704, 0x16EC52CF,
    0x624F68D5, 0x32CD40C0, 0x11D4D10B, 0x9FA096A9,
    0x98981567, 0x3B85C48E, 0xCA0A3CF1, 0xAC390F69,
    0x12CC50C1, 0xCE2A3EF7, 0xDCBA3770, 0xB3C180AA,
    0x56EE72CC, 0x834098B8, 0xAD318F30, 0x85709B3B,
    0xE153A925, 0xE47B2B65, 0xE913AD25, 0x34FD4353,
    0xE763AAA8, 0xDEAA36E7, 0xAA090CF9, 0xC762BAA3,
    0x081C5D57, 0xF4FB2369, 0x1A8C54D1, 0x605F694E,
    0x589E757F, 0x36ED42E5, 0xEF23AE90, 0x54FE737F,
    0x7B87E4B3, 0x5A8E74FA, 0xBEA906C0, 0x8F209E8D,
    0x2155C929, 0x5DB6F737, 0xFA8B24DD, 0x0E2C5EE1,
    0xB2C900C9, 0xBA8904CA, 0xF7E3A29A, 0xCC3A3F55,
    0x76EF62E4, 0x5FA6F6AF, 0x77E7E2A6, 0xDDB2B70D,
    0x37E5C2B0, 0xE05B2944, 0xB9918511, 0x55F6F32B,
    0x0914DD33, 0xFB83A48E, 0x9CB81754, 0x31D5C13E,
    0x89109D17, 0xAF218E9F, 0x1B84D4B1, 0x824818D6,
    0x30DD4105, 0x74FF6315, 0x33C5C0C7, 0x35F5C347,
    0xB5F18360, 0xEA0B2CB6, 0x2E2D4E84, 0xA1518966,
    0xB6E902AC, 0xA0590928, 0xE66B2ABA, 0x2915CD48,
    0x6577EB5C, 0x2C3D4F0F, 0x066C5A86, 0x13C4D0C2,
    0xA24908B1, 0x57E6F2CD, 0x3CBD4714, 0xEE2B2EA1,
    0xC81A3D2F, 0xFEAB26A3, 0xF6EB22A2, 0xB8990530,
    0x2345C8D9, 0x447E7B01, 0x047C5B12, 0x6C3F6F09,
    0xF2CB20A9, 0xA9118D7E, 0x189C5511, 0x87609AF7,
    0x2D35CF62, 0x53C6F0FC, 0x024C58AB, 0xF3C3A0D6,
    0x389D4523, 0xD1D2B158, 0x0C3C5F2C, 0xBDB18741,
    0x95F09344, 0x17E4D2E5, 0xAE290E88, 0x91D09146,
    0xC05A3915, 0xD7E2B2D1, 0x8C381F04, 0x93C090C2,
    0x424E78A9, 0x4C3E7F2B, 0xDFA2B6CC, 0x7997E564,
    0x92C81099, 0x0344D8FC, 0xF89B2501, 0x72CF60A2,
    0xB0D9011D, 0xAB018CDA, 0x6A0F6CA9, 0x5996F564,
    0x3FA5C6FA, 0xD5F2B341, 0x71D7E16B, 0xC66A3A87
};

static device_key_t cppm_device_keys[] =
{
    {0x00, 0x5f58, 0x53e173beec3b8cLL},

    {0x00, 0x4821, 0x6d05086b755c81LL},
    {0x01, 0x091c, 0x97ace18dd26973LL},
    {0x02, 0x012a, 0xfefc0a25a38d42LL},
    {0x03, 0x469b, 0x0780491970db2cLL},
    {0x04, 0x0f9b, 0x0bedd116d43484LL},
    {0x05, 0x59b2, 0x566936bcebe294LL},
    {0x06, 0x5fc8, 0xdc610f649b1fc0LL},
    {0x07, 0x11de, 0x6ee01d3872c2d9LL},
    {0x08, 0x52b6, 0xd0132c376e439bLL},
    {0x09, 0x135f, 0x800faa66206922LL},
    {0x0a, 0x3806, 0x9d1aa1460885c2LL},
    {0x0b, 0x2da2, 0x9833f21818ba33LL},
    {0x0c, 0x113f, 0xd50aa7d022045aLL},
    {0x0d, 0x11ec, 0x88abee7bb83a32LL},
    {0x0e, 0x071b, 0x9b45eea4e7d140LL},
    {0x0f, 0x5c55, 0x5a49f860cca5cfLL},

    {0x00, 0x0375, 0x1a12793404c279LL},
    {0x01, 0x4307, 0x61418b44cea550LL},
    {0x02, 0x1f70, 0x52bde5b73adcdaLL},
    {0x03, 0x1bbc, 0x70a031ae493159LL},
    {0x04, 0x1f9d, 0x0a570636aedb61LL},
    {0x05, 0x4e7b, 0xc313563e7883e9LL},
    {0x06, 0x07c4, 0x32c55f7bc42d45LL},
    {0x07, 0x4216, 0x4f854df6c1d721LL},
    {0x08, 0x11c5, 0xc0e3f0f3df33ccLL},
    {0x09, 0x0486, 0xbfca7754db5de6LL},
    {0x0a, 0x2f82, 0xa964fc061af87cLL},
    {0x0b, 0x236a, 0xb96d68856c45d5LL},
    {0x0c, 0x5beb, 0xd2ca3cbb7d13ccLL},
    {0x0d, 0x3db6, 0x58cf827ff3c540LL},
    {0x0e, 0x4b22, 0xbb4037442a869cLL},
    {0x0f, 0x59b5, 0x3a83e0ddf37a6eLL},
};

/* The encrypted part of the block. */
#define DVDCPXM_ENCRYPTED_SIZE 1920

#define CCI_BYTE 0x00;

int
cppm_init(prot_CPPMDecoder *p_ctx,
          char *dvd_dev,
          char *psz_file) {
    int copyright;
    int dvd_fd;
    int ret;
    uint8_t *p_mkb;

    p_ctx->media_type = -1;

    if ((dvd_fd = open(dvd_dev, O_RDONLY)) < 0)
        return -1;

    if (ioctl_ReadCopyright(dvd_fd, 0, &copyright) < 0) {
        close(dvd_fd);
        return -1;
    }

    p_ctx->media_type = copyright;

    switch (copyright) {
    case COPYRIGHT_PROTECTION_NONE:
        break;
    case COPYRIGHT_PROTECTION_CPPM:
        if (cppm_set_id_album(p_ctx, dvd_fd) == 0) {
            p_mkb = cppm_get_mkb(psz_file);
            if (p_mkb) {
                ret = cppm_process_mkb(p_mkb,
                                       cppm_device_keys,
                                       sizeof(cppm_device_keys) /
                                       sizeof(*cppm_device_keys),
                                       &p_ctx->media_key);
                free(p_mkb);
                if (ret) break;
            }
        }
        break;
    default:
        /*unsupported protection type*/
        return -2;
    }

    close(dvd_fd);

    return p_ctx->media_type;
}

int
cppm_set_id_album(prot_CPPMDecoder *p_ctx,
                  int i_fd) {
    uint8_t p_buffer[DVD_DISCKEY_SIZE];
    int i;
    css_t css;

    p_ctx->id_album_media = 0;
    if (GetBusKey(i_fd, &css))
        return -1;
    if (ioctl_ReadDiscKey(i_fd, &css.agid, p_buffer))
        return -1;
    if (GetASF(i_fd) != 1)
    {
        ioctl_InvalidateAgid(i_fd, &css.agid);
        return -1;
    }
    for (i = 0; i < DVD_DISCKEY_SIZE; i++)
        p_buffer[i] ^= css.p_bus_key[4 - (i % KEY_SIZE)];
    p_ctx->id_album_media = *(uint64_t*)&p_buffer[80];
    B2N_64(p_ctx->id_album_media);
    return 0;
}

uint8_t*
cppm_get_mkb(char *psz_mkb) {
    FILE    *f_mkb;
    uint8_t *p_mkb = NULL;
    char    mkb_signature[12];
    size_t  mkb_size;

    f_mkb = fopen(psz_mkb, "rb");
    if (!f_mkb)
        return NULL;
    if (fread(mkb_signature, 1, 12, f_mkb) == 12) {
        if (memcmp(mkb_signature, "DVDAUDIO.MKB", 12) == 0) {
            if (fread(&mkb_size, 1, 4, f_mkb) == 4) {
                B2N_32(mkb_size);
                p_mkb = malloc(mkb_size);
                if (p_mkb) {
                    if (fread(p_mkb, 1, mkb_size, f_mkb) != mkb_size) {
                        free(p_mkb);
                        p_mkb = NULL;
                    }
                }
            }
        }
    }
    fclose(f_mkb);
    return p_mkb;
}

static uint32_t
rol32(uint32_t code, int n) {
    return (code << n) | (code >> (32 - n));
}

static uint32_t
F(uint32_t code, uint32_t key) {
    uint32_t work;

    work = code + key;
    work ^= sbox_f[work & 0xff];
    work ^= rol32(work, 9) ^ rol32(work, 22);
    return work;
}

static uint64_t
c2_dec(uint64_t code, uint64_t key) {
    uint32_t L, R, t;
    uint32_t ktmpa, ktmpb, ktmpc, ktmpd;
    uint32_t sk[10];
    int      round;

    L  =    (uint32_t)((code >> 32) & 0xffffffff);
    R  =    (uint32_t)((code      ) & 0xffffffff);
    ktmpa = (uint32_t)((key  >> 32) & 0x00ffffff);
    ktmpb = (uint32_t)((key       ) & 0xffffffff);
    for (round = 0; round < 10; round++) {
        ktmpa &= 0x00ffffff;
        sk[round] = ktmpb + ((uint32_t)sbox[(ktmpa & 0xff) ^ round] << 4);
        ktmpc = (ktmpb >> (32 - 17));
        ktmpd = (ktmpa >> (24 - 17));
        ktmpa = (ktmpa << 17) | ktmpc;
        ktmpb = (ktmpb << 17) | ktmpd;
    }
    for (round = 9; round >= 0; round--) {
        L -= F(R, sk[round]);
        t = L; L = R; R = t;
    }
    t = L; L = R; R = t;
    return (((uint64_t)L) << 32) | R;
}

#define f(c, r) (((uint64_t)c << 32) | (uint64_t)r)

int
cppm_process_mkb(uint8_t *p_mkb,
                 device_key_t *p_dev_keys,
                 int nr_dev_keys,
                 uint64_t *p_media_key) {
    int mkb_pos, length, i, i_dev_key, no_more_keys, no_more_records;
    uint8_t record_type, column;
    uint64_t buffer;
    uint64_t media_key = 0;
    uint64_t verification_data = 0;

    i_dev_key = 0;
    no_more_keys = 0;
    while (!no_more_keys) {
        mkb_pos = 0;
        no_more_records = 0;
        while (!no_more_records) {
            record_type = *(uint8_t*)&p_mkb[mkb_pos];
            length = *(uint32_t*)&p_mkb[mkb_pos] & 0xffffff00;
            B2N_32(length);
            if (length >= 12) {
                buffer = *(uint64_t*)&p_mkb[mkb_pos + 4];
            }
            else {
                if (length < 4)
                    length = 4;
            }
            switch (record_type) {
            case 0x82: /* Conditionally calculate media key record */
                B2N_64(buffer);
                buffer = c2_dec(buffer, media_key);
                if ((buffer & 0xffffffff00000000LL) != 0xdeadbeef00000000LL)
                    break;
                B2N_64(buffer);
            case 0x01: /* Calculate media key record */
                column = ((uint8_t*)&buffer)[4];
                /*
                if (column >= 16 || ((uint8_t*)&buffer)[5] != 0 || ((uint8_t*)&buffer)[6] != 0 || ((uint8_t*)&buffer)[7] != 1)
                    break;
                */
                /* Get appropriate device key for column */
                no_more_keys = 1;
                for (i = i_dev_key; i < nr_dev_keys; i++) {
                    if (p_dev_keys[i].col == column) {
                        no_more_keys = 0;
                        i_dev_key = i;
                        break;
                    }
                }
                if (no_more_keys)
                    break;
                if (12 + p_dev_keys[i_dev_key].row * 8 + 8 > length)
                    break;
                buffer = *(uint64_t*)&p_mkb[mkb_pos + 12 + p_dev_keys[i_dev_key].row * 8];
                B2N_64(buffer);
                if (record_type == 0x82)
                    buffer = c2_dec(buffer, media_key);
                media_key = (c2_dec(buffer, p_dev_keys[i_dev_key].key) & 0x00ffffffffffffffLL) ^ f(column, p_dev_keys[i_dev_key].row);
                buffer = c2_dec(verification_data, media_key);
                if ((buffer & 0xffffffff00000000LL) == 0xdeadbeef00000000LL) {
                    *p_media_key = media_key;
                    return 0;
                }
                break;
            case 0x02: /* End of media key record */
                no_more_records = 1;
                break;
            case 0x81: /* Verify media key record */
                B2N_64(buffer);
                verification_data = buffer;
                break;
            default:
                break;
            }
            mkb_pos += length;
        }
        i_dev_key++;
    }
    return -1;
}

int
cppm_decrypt(prot_CPPMDecoder *p_ctx,
             uint8_t *p_buffer,
             int nr_blocks,
             int preserve_cci) {
    int i;
    int encrypted = 0;

    switch (p_ctx->media_type) {
    case COPYRIGHT_PROTECTION_CPPM:
        for (i = 0; i < nr_blocks; i++)
            encrypted += cppm_decrypt_block(p_ctx,
                                            p_buffer + i * DVDCPXM_BLOCK_SIZE,
                                            preserve_cci);
        return encrypted;
    default:
        return 0;
    }
}

static uint64_t
c2_enc(uint64_t code, uint64_t key) {
    uint32_t L, R, t;
    uint32_t ktmpa, ktmpb, ktmpc, ktmpd;
    uint32_t sk[10];
    int      round;

    L     = (uint32_t)((code >> 32) & 0xffffffff);
    R     = (uint32_t)((code      ) & 0xffffffff);
    ktmpa = (uint32_t)((key  >> 32) & 0x00ffffff);
    ktmpb = (uint32_t)((key       ) & 0xffffffff);
    for (round = 0; round < 10; round++)
    {
        ktmpa &= 0x00ffffff;
        sk[round] = ktmpb + ((uint32_t)sbox[(ktmpa & 0xff) ^ round] << 4);
        ktmpc = (ktmpb >> (32 - 17));
        ktmpd = (ktmpa >> (24 - 17));
        ktmpa = (ktmpa << 17) | ktmpc;
        ktmpb = (ktmpb << 17) | ktmpd;
    }
    for (round = 0; round < 10; round++)
    {
        L += F(R, sk[round]);
        t = L; L = R; R = t;
    }
    t = L; L = R; R = t;
    return (((uint64_t)L) << 32) | R;
}

static uint64_t
c2_g(uint64_t code, uint64_t key) {
    return c2_enc(code, key) ^ code;
}

static void
c2_dcbc(uint64_t *p_buffer, uint64_t key, int length) {
    uint32_t L, R, t;
    uint32_t ktmpa, ktmpb, ktmpc, ktmpd;
    uint32_t sk[10];
    uint64_t inout, inkey;
    int      round, key_round, i;

    inkey = key;
    key_round = 10;
    for (i = 0; i < length; i += 8)
    {
        inout = *(uint64_t*)p_buffer;
        B2N_64(inout);
        L  =    (uint32_t)((inout >> 32) & 0xffffffff);
        R  =    (uint32_t)((inout      ) & 0xffffffff);
        ktmpa = (uint32_t)((inkey >> 32) & 0x00ffffff);
        ktmpb = (uint32_t)((inkey      ) & 0xffffffff);
        for (round = 0; round < key_round; round++)
        {
            ktmpa &= 0x00ffffff;
            sk[round] = ktmpb + ((uint32_t)sbox[(ktmpa & 0xff) ^ round] << 4);
            ktmpc = (ktmpb >> (32 - 17));
            ktmpd = (ktmpa >> (24 - 17));
            ktmpa = (ktmpa << 17) | ktmpc;
            ktmpb = (ktmpb << 17) | ktmpd;
        }
        for (round = 9; round >= 0; round--)
        {
            L -= F(R, sk[round % key_round]);
            t = L; L = R; R = t;
            if (round == 5)
            {
                inkey = key ^ (((uint64_t)(R & 0x00ffffff) << 32) | L);
            }
        }
        t = L; L = R; R = t;
        inout = (((uint64_t)L) << 32) | R;
        B2N_64(inout);
        /* *((uint64_t*)p_buffer)++ = inout; */
        *(p_buffer)++ = inout;
        key_round = 2;
    }
}

int
cppm_decrypt_block(prot_CPPMDecoder *p_ctx,
                   uint8_t *p_buffer,
                   int preserve_cci) {
    uint64_t d_kc_i, k_au, k_i, k_c;
    int encrypted;

    encrypted = 0;
    if (mpeg2_check_pes_scrambling_control(p_buffer)) {
        k_au = c2_g(p_ctx->id_album_media, p_ctx->media_key) &
            0x00ffffffffffffffLL;
        d_kc_i = *(uint64_t*)&p_buffer[24];
        B2N_64(d_kc_i);
        k_i = c2_g(d_kc_i, k_au) & 0x00ffffffffffffffLL;
        d_kc_i = *(uint64_t*)&p_buffer[32];
        B2N_64(d_kc_i);
        k_i = c2_g(d_kc_i, k_i) & 0x00ffffffffffffffLL;
        d_kc_i = *(uint64_t*)&p_buffer[40];
        B2N_64(d_kc_i);
        k_i = c2_g(d_kc_i, k_i) & 0x00ffffffffffffffLL;
        d_kc_i = *(uint64_t*)&p_buffer[48];
        B2N_64(d_kc_i);
        k_i = c2_g(d_kc_i, k_i) & 0x00ffffffffffffffLL;
        d_kc_i = *(uint64_t*)&p_buffer[84];
        B2N_64(d_kc_i);
        k_c = c2_g(d_kc_i, k_i) & 0x00ffffffffffffffLL;
        c2_dcbc((uint64_t*)(&p_buffer[DVDCPXM_BLOCK_SIZE -
                                      DVDCPXM_ENCRYPTED_SIZE]),
                k_c, DVDCPXM_ENCRYPTED_SIZE);
        mpeg2_reset_pes_scrambling_control(p_buffer);
        encrypted = 1;
    }
    if (!preserve_cci)
        mpeg2_reset_cci(p_buffer);
    return encrypted;
}

int
mpeg2_check_pes_scrambling_control(uint8_t *p_block) {
    if (*(uint32_t*)p_block == 0xba010000)
        return (p_block[20] & 0x30) >> 4;
    else
        return 0;
}

void
mpeg2_reset_pes_scrambling_control(uint8_t *p_block) {
    if (*(uint32_t*)p_block == 0xba010000)
        p_block[20] &= 0xCD;
}

void
mpeg2_reset_cci(uint8_t *p_block) {
    uint8_t *p_mlp_pcm, *p_curr;
    int pes_sid;
    int pes_len;

    p_curr = p_block;
    if (*(uint32_t*)p_block == 0xba010000) {
        p_curr += 14 + (p_curr[13] & 0x07);
        while (p_curr < p_block + DVDCPXM_BLOCK_SIZE) {
            pes_len = (p_curr[4] << 8) + p_curr[5];
            if ((*(uint32_t*)p_curr & 0x00ffffff) == 0x00010000) {
                pes_sid = p_curr[3];
                if (pes_sid == 0xbd) { /* private stream 1*/
                    p_mlp_pcm = p_curr + 9 + p_curr[8];
                    switch (p_mlp_pcm[0]) { /* stream id */
                    case 0xa0: /* PCM */
                        /* reset CCI */
                        if (p_mlp_pcm[3] > 8) p_mlp_pcm[12] = CCI_BYTE;
                        break;
                    case 0xa1: /* MLP */
                        /* reset CCI */
                        if (p_mlp_pcm[3] > 4) p_mlp_pcm[8] = CCI_BYTE;
                        break;
                    }
                }
                p_curr += 6 + pes_len;
            } else {
                break;
            }
        }
    }
}
