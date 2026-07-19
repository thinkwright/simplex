"""Public API for the wirecodec package.

Exposes:
    - encode(record): produce a compact, deterministic version 2 JSON string
      with a SHA-256 checksum over the canonical payload.
    - decode(text): parse a JSON record, accepting version 1 (no checksum)
      and version 2 (checksum-validated) records.
    - CodecError: raised for malformed, unsupported, or checksum-invalid input.
"""

from .codec import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]