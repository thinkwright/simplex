"""Public API for the wirecodec package.

Exposes ``encode``, ``decode``, and ``CodecError`` as the stable import surface.
"""

from wirecodec.codec import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]