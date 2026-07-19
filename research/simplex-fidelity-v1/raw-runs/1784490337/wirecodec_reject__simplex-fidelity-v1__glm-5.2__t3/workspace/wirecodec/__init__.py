"""wirecodec package: deterministic JSON wire codec with SHA-256 checksums."""

from wirecodec.public import CodecError, decode, encode

__all__ = ["encode", "decode", "CodecError"]