"""Public API for wirecodec.

Exposes encode, decode, and CodecError.
"""

from ._codec import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]