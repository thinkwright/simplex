"""Public API for the wirecodec package.

Exposes :func:`encode`, :func:`decode`, and :class:`CodecError`.
"""

from .codec import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]