"""Public API for wirecodec.

Exposes encode, decode, and CodecError as required by the contract.
"""

from wirecodec.errors import CodecError
from wirecodec.codec import encode, decode

__all__ = ["encode", "decode", "CodecError"]