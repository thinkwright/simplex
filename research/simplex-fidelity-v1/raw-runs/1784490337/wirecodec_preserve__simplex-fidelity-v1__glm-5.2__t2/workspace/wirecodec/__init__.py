"""wirecodec: deterministic JSON wire records with SHA-256 checksums."""

from .public import CodecError, decode, encode

__all__ = ["encode", "decode", "CodecError"]