"""wirecodec – a small deterministic JSON wire codec with SHA-256 checksums."""

from wirecodec.public import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]
