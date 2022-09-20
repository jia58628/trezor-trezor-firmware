from trezorcrypto import bip340, curve25519, ed25519, nist256p1, secp256k1  # noqa: F401

# from trezorcrypto import curve25519, ed25519, nist256p1, secp256k1
# import mock_bip340 as bip340  # noqa: F401


class bip340____:  # noqa: F401
    BYTES = 32 * b"\x00"
    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def generate_secret() -> bytes:
        """
        Generate secret key.
        """
        return BYTES

    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def publickey(secret_key: bytes) -> bytes:
        """
        Computes public key from secret key.
        """
        return BYTES

    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def sign(
        secret_key: bytes,
        digest: bytes,
    ) -> bytes:
        """
        Uses secret key to produce the signature of the digest.
        """
        return BYTES + BYTES

    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def verify_publickey(public_key: bytes) -> bool:
        """
        Verifies whether the public key is valid.
        Returns True on success.
        """
        return True

    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
        """
        Uses public key to verify the signature of the digest.
        Returns True on success.
        """
        return True

    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def tweak_public_key(
        public_key: bytes,
        root_hash: bytes | None = None,
    ) -> bytes:
        """
        Tweaks the public key with the specified root_hash.
        """
        return BYTES

    # extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
    @staticmethod
    def tweak_secret_key(
        secret_key: bytes,
        root_hash: bytes | None = None,
    ) -> bytes:
        """
        Tweaks the secret key with the specified root_hash.
        """
        return BYTES
