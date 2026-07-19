"""wirecodec: a small deterministic wire codec for versioned JSON records.

Only the Python standard library is used. Record integrity is provided by a
SHA-256 checksum (from :mod:`hashlib`).
"""

from .public import CodecError, decode, encode

__all__ = ["CodecError", "decode", "encode"]