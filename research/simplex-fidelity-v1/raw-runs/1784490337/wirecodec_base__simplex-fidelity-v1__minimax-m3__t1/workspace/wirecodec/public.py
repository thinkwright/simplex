"""Public API for the wirecodec package."""

from wirecodec._codec import encode, decode, CodecError

__all__ = ["encode", "decode", "CodecError"]