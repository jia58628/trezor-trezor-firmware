/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>

#include "ecdsa.h"
#include "fw_signatures.h"
#include "memory.h"
#include "memzero.h"
#include "secp256k1.h"
#include "sha2.h"

const uint32_t FIRMWARE_MAGIC_NEW = 0x465a5254;  // TRZF

#define PUBKEYS 5

#if DEBUG_T1_SIGNATURES

// Make build explode if combining debug sigs with production
#if PRODUCTION
#error "Can't have production device with debug keys! Build aborted"
#endif

// These are **only** for debugging signatures with SignMessage
// Use this mnemonic for testing signing:
// "table table table table table table table table table table table advance"
// the "SignMessage"-style public keys, third signing scheme
static const uint8_t * const pubkey_v3[PUBKEYS] = {
        (const uint8_t *)"\x03\x73\x08\xe1\x40\x77\x16\x1c\x36\x5d\xea\x0f\x5c\x80\xaa\x6c\x5d\xba\x34\x71\x9e\x82\x5b\xd2\x3a\xe5\xf7\xe7\xd2\x98\x8a\xdb\x0f",
        (const uint8_t *)"\x03\x9c\x1b\x24\x60\xe3\x43\x71\x2e\x98\x2e\x07\x32\xe7\xed\x17\xf6\x0d\xe4\xc9\x33\x06\x5b\x71\x70\xd9\x9c\x6e\x7f\xe7\xcc\x7f\x4b",
        (const uint8_t *)"\x03\x15\x2b\x37\xfd\xf1\x26\x11\x12\x74\xc8\x94\xc3\x48\xdc\xc9\x75\xb5\x7c\x11\x5e\xe2\x4c\xeb\x19\xb5\x19\x0a\xc7\xf7\xb6\x51\x73",
        (const uint8_t *)"\x02\x83\x91\x8a\xbf\x1b\x6e\x1d\x2a\x1d\x08\xea\x29\xc9\xd2\xae\x2e\x97\xe3\xc0\x1f\x4e\xa8\x59\x2b\x08\x8d\x28\x03\x5b\x44\x4e\xd0",
        (const uint8_t *)"\x03\xc6\x83\x63\x85\x07\x8a\x18\xe8\x1d\x74\x77\x68\x1e\x0d\x30\x86\x66\xf3\x99\x59\x4b\xe9\xe8\xab\xcb\x45\x58\xa6\xe2\x47\x32\xfc"
};

// the "new", or second signing scheme keys
static const uint8_t * const pubkey_v2[PUBKEYS] = {
        (const uint8_t *)"\x02\xd5\x71\xb7\xf1\x48\xc5\xe4\x23\x2c\x38\x14\xf7\x77\xd8\xfa\xea\xf1\xa8\x42\x16\xc7\x8d\x56\x9b\x71\x04\x1f\xfc\x76\x8a\x5b\x2d",
        (const uint8_t *)"\x03\x63\x27\x9c\x0c\x08\x66\xe5\x0c\x05\xc7\x99\xd3\x2b\xd6\xba\xb0\x18\x8b\x6d\xe0\x65\x36\xd1\x10\x9d\x2e\xd9\xce\x76\xcb\x33\x5c",
        (const uint8_t *)"\x02\x43\xae\xdb\xb6\xf7\xe7\x1c\x56\x3f\x8e\xd2\xef\x64\xec\x99\x81\x48\x25\x19\xe7\xef\x4f\x4a\xa9\x8b\x27\x85\x4e\x8c\x49\x12\x6d",
        (const uint8_t *)"\x02\x87\x7c\x39\xfd\x7c\x62\x23\x7e\x03\x82\x35\xe9\xc0\x75\xda\xb2\x61\x63\x0f\x78\xee\xb8\xed\xb9\x24\x87\x15\x9f\xff\xed\xfd\xf6",
        (const uint8_t *)"\x03\x73\x84\xc5\x1a\xe8\x1a\xdd\x0a\x52\x3a\xdb\xb1\x86\xc9\x1b\x90\x6f\xfb\x64\xc2\xc7\x65\x80\x2b\xf2\x6d\xbd\x13\xbd\xf1\x2c\x31"
};
#else

// These public keys are production keys
// - used in production devices
// - used in debug non-production builds for QA testing

// the "SignMessage"-style public keys, third signing scheme
static const uint8_t * const pubkey_v3[PUBKEYS] = {
        (const uint8_t *)"\x02\xd5\x71\xb7\xf1\x48\xc5\xe4\x23\x2c\x38\x14\xf7\x77\xd8\xfa\xea\xf1\xa8\x42\x16\xc7\x8d\x56\x9b\x71\x04\x1f\xfc\x76\x8a\x5b\x2d",
        (const uint8_t *)"\x03\x63\x27\x9c\x0c\x08\x66\xe5\x0c\x05\xc7\x99\xd3\x2b\xd6\xba\xb0\x18\x8b\x6d\xe0\x65\x36\xd1\x10\x9d\x2e\xd9\xce\x76\xcb\x33\x5c",
        (const uint8_t *)"\x02\x43\xae\xdb\xb6\xf7\xe7\x1c\x56\x3f\x8e\xd2\xef\x64\xec\x99\x81\x48\x25\x19\xe7\xef\x4f\x4a\xa9\x8b\x27\x85\x4e\x8c\x49\x12\x6d",
        (const uint8_t *)"\x02\x87\x7c\x39\xfd\x7c\x62\x23\x7e\x03\x82\x35\xe9\xc0\x75\xda\xb2\x61\x63\x0f\x78\xee\xb8\xed\xb9\x24\x87\x15\x9f\xff\xed\xfd\xf6",
        (const uint8_t *)"\x03\x73\x84\xc5\x1a\xe8\x1a\xdd\x0a\x52\x3a\xdb\xb1\x86\xc9\x1b\x90\x6f\xfb\x64\xc2\xc7\x65\x80\x2b\xf2\x6d\xbd\x13\xbd\xf1\x2c\x31"
};

// the "new", or second signing scheme keys
static const uint8_t * const pubkey_v2[PUBKEYS] = {
        (const uint8_t *)"\x02\xd5\x71\xb7\xf1\x48\xc5\xe4\x23\x2c\x38\x14\xf7\x77\xd8\xfa\xea\xf1\xa8\x42\x16\xc7\x8d\x56\x9b\x71\x04\x1f\xfc\x76\x8a\x5b\x2d",
        (const uint8_t *)"\x03\x63\x27\x9c\x0c\x08\x66\xe5\x0c\x05\xc7\x99\xd3\x2b\xd6\xba\xb0\x18\x8b\x6d\xe0\x65\x36\xd1\x10\x9d\x2e\xd9\xce\x76\xcb\x33\x5c",
        (const uint8_t *)"\x02\x43\xae\xdb\xb6\xf7\xe7\x1c\x56\x3f\x8e\xd2\xef\x64\xec\x99\x81\x48\x25\x19\xe7\xef\x4f\x4a\xa9\x8b\x27\x85\x4e\x8c\x49\x12\x6d",
        (const uint8_t *)"\x02\x87\x7c\x39\xfd\x7c\x62\x23\x7e\x03\x82\x35\xe9\xc0\x75\xda\xb2\x61\x63\x0f\x78\xee\xb8\xed\xb9\x24\x87\x15\x9f\xff\xed\xfd\xf6",
        (const uint8_t *)"\x03\x73\x84\xc5\x1a\xe8\x1a\xdd\x0a\x52\x3a\xdb\xb1\x86\xc9\x1b\x90\x6f\xfb\x64\xc2\xc7\x65\x80\x2b\xf2\x6d\xbd\x13\xbd\xf1\x2c\x31"
};
#endif

#define SIGNATURES 3

#define FLASH_META_START 0x08008000
#define FLASH_META_CODELEN (FLASH_META_START + 0x0004)
#define FLASH_META_SIGINDEX1 (FLASH_META_START + 0x0008)
#define FLASH_META_SIGINDEX2 (FLASH_META_START + 0x0009)
#define FLASH_META_SIGINDEX3 (FLASH_META_START + 0x000A)
#define FLASH_OLD_APP_START 0x08010000
#define FLASH_META_SIG1 (FLASH_META_START + 0x0040)
#define FLASH_META_SIG2 (FLASH_META_START + 0x0080)
#define FLASH_META_SIG3 (FLASH_META_START + 0x00C0)

/*
 * 0x18 in message prefix is coin info, 0x20 is the length of hash
 * that follows.
 * See `core/src/apps/bitcoin/sign_message.py`.
 */
#define VERIFYMESSAGE_PREFIX \
  ("\x18"                    \
   "Bitcoin Signed Message:\n\x20")
#define PREFIX_LENGTH (sizeof(VERIFYMESSAGE_PREFIX) - 1)
#define SIGNED_LENGTH (PREFIX_LENGTH + 32)

void compute_firmware_fingerprint(const image_header *hdr, uint8_t hash[32]) {
  image_header copy = {0};
  memcpy(&copy, hdr, sizeof(image_header));
  memzero(copy.sig1, sizeof(copy.sig1));
  memzero(copy.sig2, sizeof(copy.sig2));
  memzero(copy.sig3, sizeof(copy.sig3));
  copy.sigindex1 = 0;
  copy.sigindex2 = 0;
  copy.sigindex3 = 0;
  sha256_Raw((const uint8_t *)&copy, sizeof(image_header), hash);
}

void compute_firmware_fingerprint_for_verifymessage(const image_header *hdr,
                                                    uint8_t hash[32]) {
  uint8_t prefixed_header[SIGNED_LENGTH] = VERIFYMESSAGE_PREFIX;
  uint8_t header_hash[32];
  uint8_t hash_before_double_hashing[32];
  compute_firmware_fingerprint(hdr, header_hash);
  memcpy(prefixed_header + PREFIX_LENGTH, header_hash, sizeof(header_hash));
  sha256_Raw(prefixed_header, sizeof(prefixed_header),
             hash_before_double_hashing);
  // We need to do hash the previous result again because SignMessage
  // computes it this way, see `core/src/apps/bitcoin/sign_message.py`
  sha256_Raw(hash_before_double_hashing, sizeof(hash_before_double_hashing),
             hash);
}

bool firmware_present_new(void) {
  const image_header *hdr =
      (const image_header *)FLASH_PTR(FLASH_FWHEADER_START);
  if (hdr->magic != FIRMWARE_MAGIC_NEW) return false;
  // we need to ignore hdrlen for now
  // because we keep reset_handler ptr there
  // for compatibility with older bootloaders
  // after this is no longer necessary, let's uncomment the line below:
  // if (hdr->hdrlen != FLASH_FWHEADER_LEN) return false;
  if (hdr->codelen > FLASH_APP_LEN) return false;
  if (hdr->codelen < 4096) return false;

  return true;
}

int signatures_new_ok(const image_header *hdr, uint8_t store_fingerprint[32],
                      bool use_verifymessage) {
  uint8_t hash[32] = {0};
  // which set of public keys depend on scheme
  const uint8_t * const * pubkey_ptr = NULL;
  if (use_verifymessage) {
    pubkey_ptr = pubkey_v3;
    compute_firmware_fingerprint_for_verifymessage(hdr, hash);
  } else {
    pubkey_ptr = pubkey_v2;
    compute_firmware_fingerprint(hdr, hash);
  }

  if (store_fingerprint) {
    memcpy(store_fingerprint, hash, 32);
  }

  if (hdr->sigindex1 < 1 || hdr->sigindex1 > PUBKEYS)
    return SIG_FAIL;  // invalid index
  if (hdr->sigindex2 < 1 || hdr->sigindex2 > PUBKEYS)
    return SIG_FAIL;  // invalid index
  if (hdr->sigindex3 < 1 || hdr->sigindex3 > PUBKEYS)
    return SIG_FAIL;  // invalid index

  if (hdr->sigindex1 == hdr->sigindex2) return SIG_FAIL;  // duplicate use
  if (hdr->sigindex1 == hdr->sigindex3) return SIG_FAIL;  // duplicate use
  if (hdr->sigindex2 == hdr->sigindex3) return SIG_FAIL;  // duplicate use

  if (0 != ecdsa_verify_digest(&secp256k1, pubkey_ptr[hdr->sigindex1 - 1],
                               hdr->sig1, hash)) {  // failure
    return SIG_FAIL;
  }
  if (0 != ecdsa_verify_digest(&secp256k1, pubkey_ptr[hdr->sigindex2 - 1],
                               hdr->sig2, hash)) {  // failure
    return SIG_FAIL;
  }
  if (0 != ecdsa_verify_digest(&secp256k1, pubkey_ptr[hdr->sigindex3 - 1],
                               hdr->sig3, hash)) {  // failure
    return SIG_FAIL;
  }

  return SIG_OK;
}

int signatures_match(const image_header *hdr, uint8_t store_fingerprint[32]) {
  int result = 0;
  // Return success if "verify message" or the "new" style matches.
  // Signature of one hash can't be used to get signature of the other method
  // under assumption of SHA2 preimage resistance.
  // Use XOR to always force computing both signatures.
  // Return only the hash for the "new style" computation so that it is
  // the same shown in previous bootloader.
  result ^= signatures_new_ok(hdr, store_fingerprint, false);
  result ^= signatures_new_ok(hdr, NULL, true);
  if (result != SIG_OK) {
    return SIG_FAIL;
  }
  return SIG_OK;
}

int mem_is_empty(const uint8_t *src, uint32_t len) {
  for (uint32_t i = 0; i < len; i++) {
    if (src[i]) return 0;
  }
  return 1;
}

int check_firmware_hashes(const image_header *hdr) {
  uint8_t hash[32] = {0};
  // check hash of the first code chunk
  sha256_Raw(FLASH_PTR(FLASH_APP_START), (64 - 1) * 1024, hash);
  if (0 != memcmp(hash, hdr->hashes, 32)) return SIG_FAIL;
  // check remaining used chunks
  uint32_t total_len = FLASH_FWHEADER_LEN + hdr->codelen;
  int used_chunks = total_len / FW_CHUNK_SIZE;
  if (total_len % FW_CHUNK_SIZE > 0) {
    used_chunks++;
  }
  for (int i = 1; i < used_chunks; i++) {
    sha256_Raw(FLASH_PTR(FLASH_FWHEADER_START + (64 * i) * 1024), 64 * 1024,
               hash);
    if (0 != memcmp(hdr->hashes + 32 * i, hash, 32)) return SIG_FAIL;
  }
  // check unused chunks
  for (int i = used_chunks; i < 16; i++) {
    if (!mem_is_empty(hdr->hashes + 32 * i, 32)) return SIG_FAIL;
  }
  // all OK
  return SIG_OK;
}
