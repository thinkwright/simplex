"""Exception types for wirecodec."""


class CodecError(Exception):
    """Raised when decoding fails for any reason (malformed, unsupported, checksum mismatch)."""