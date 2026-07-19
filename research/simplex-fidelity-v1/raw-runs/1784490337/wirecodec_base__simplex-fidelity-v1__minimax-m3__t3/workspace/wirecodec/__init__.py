"""wirecodec: deterministic JSON record codec with version 2 checksums."""

from .public import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]