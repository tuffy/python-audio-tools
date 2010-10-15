#ifndef MD5_H
#define MD5_H

#include <stdint.h>

/*
 * This is the header file for the MD5 message-digest algorithm.
 * The algorithm is due to Ron Rivest.  This code was
 * written by Colin Plumb in 1993, no copyright is claimed.
 * This code is in the public domain; do with it what you wish.
 *
 * Equivalent code is available from RSA Data Security, Inc.
 * This code has been tested against that, and is equivalent,
 * except that you don't need to include two pages of legalese
 * with every copy.
 *
 * To compute the message digest of a chunk of bytes, declare an
 * MD5Context structure, pass it to MD5Init, call MD5Update as
 * needed on buffers full of bytes, and then call MD5Final, which
 * will fill a supplied 16-byte array with the digest.
 *
 * Changed so as no longer to depend on Colin Plumb's `usual.h'
 * header definitions; now uses stuff from dpkg's config.h
 *  - Ian Jackson <ijackson@nyx.cs.du.edu>.
 * Still in the public domain.
 *
 * Josh Coalson: made some changes to integrate with libFLAC.
 * Brian Langenberger: made more changes to integrate with Python Audio Tools
 * Still in the public domain, with no warranty.
 */

typedef struct {
    uint32_t in[16];
    uint32_t buf[4];
    uint32_t bytes[2];
    unsigned char *internal_buf;
    size_t capacity;
} audiotools__MD5Context;

void
audiotools__MD5Init(audiotools__MD5Context *context);

void
audiotools__MD5Final(unsigned char *digest,
                     audiotools__MD5Context *ctx);

void
audiotools__MD5Update(audiotools__MD5Context *ctx,
                      const void *buf,
                      unsigned long len);

#endif
