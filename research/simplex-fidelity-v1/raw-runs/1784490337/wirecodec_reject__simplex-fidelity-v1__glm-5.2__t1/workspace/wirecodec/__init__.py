"""Public API for the wirecodec package.

This module exposes :func:`encode`, :func:`decode` and :class:`CodecError`
as the stable, importable surface of the package (see ``wirecodec.public``).

Only the Python standard library is used; message integrity is provided by
SHA-256 from :mod:`hashlib`.
"""

from .public import CodecError, decode, encode

__all__ = ["CodecError", "encode", "decode"]