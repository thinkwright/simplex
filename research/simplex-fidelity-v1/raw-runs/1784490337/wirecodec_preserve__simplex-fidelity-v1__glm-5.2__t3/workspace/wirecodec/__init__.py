"""wirecodec: deterministic versioned wire-format codec."""

from wirecodec.public import CodecError, decode, encode

__all__ = ["encode", "decode", "CodecError"]