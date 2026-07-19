"""wirecodec: compact JSON record codec with versioned checksums."""

from wirecodec.public import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]