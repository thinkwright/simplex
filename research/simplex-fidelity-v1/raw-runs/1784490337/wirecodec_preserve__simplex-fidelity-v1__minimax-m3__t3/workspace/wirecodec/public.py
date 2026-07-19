"""Public API for the wirecodec package."""

from wirecodec._codec import CodecError, decode, encode

__all__ = ["CodecError", "decode", "encode"]