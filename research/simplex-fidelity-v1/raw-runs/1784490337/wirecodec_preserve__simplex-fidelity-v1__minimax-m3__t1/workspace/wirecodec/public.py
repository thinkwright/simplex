"""Public API for wirecodec.

Exposes:
    - encode(record): produce a deterministic version 2 JSON string with checksum.
    - decode(text): parse a JSON record (version 1 or 2) and validate it.
    - CodecError: raised for malformed, unsupported, or checksum-invalid input.
"""

from .codec import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]