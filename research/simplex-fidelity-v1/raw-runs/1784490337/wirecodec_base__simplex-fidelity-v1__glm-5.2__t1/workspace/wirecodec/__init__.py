"""Public wirecodec API.

This package exposes a stable public surface for encoding and decoding
versioned wire records. The canonical location of the public API is
:mod:`wirecodec.public`; the package root re-exports the same names for
convenience.
"""

from .public import CodecError, decode, encode

__all__ = ["CodecError", "decode", "encode"]