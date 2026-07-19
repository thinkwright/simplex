"""wirecodec: a small deterministic JSON wire-format codec.

The public API lives in :mod:`wirecodec.public` and is re-exported here for
convenience.
"""

from wirecodec.public import CodecError, decode, encode

__all__ = ["encode", "decode", "CodecError"]