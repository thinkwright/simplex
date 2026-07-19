"""wirecodec: compact JSON record codec with version 2 checksums."""

from wirecodec.public import CodecError, decode, encode

__all__ = ["CodecError", "decode", "encode"]
__version__ = "2.0.0"