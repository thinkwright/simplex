"""Public wire-codec API.

Only the Python standard library is used. The checksum is a SHA-256 digest
obtained from :mod:`hashlib`.

Public surface:
    encode(record) -> str   encode a record into a version 2 wire string
    decode(text)    -> dict  decode a version 1 or version 2 wire string
    CodecError               raised when a wire string cannot be decoded
"""

import hashlib
import json

__all__ = ["encode", "decode", "CodecError"]

# Current wire format version produced by :func:`encode`.
_CURRENT_VERSION = 2

# Fields permitted at the top level of each supported version.
_ALLOWED_FIELDS = {
    1: frozenset({"id", "value", "version"}),
    2: frozenset({"id", "value", "version", "checksum"}),
}


class CodecError(Exception):
    """Raised when a wire record is malformed or fails validation."""


def _is_valid_id(identifier):
    """Return True when ``identifier`` is a non-empty ``str``."""
    return isinstance(identifier, str) and identifier != ""


def _is_valid_value(value):
    """Return True when ``value`` is an ``int`` and not a ``bool``."""
    # ``bool`` is a subclass of ``int`` in Python, so exclude it explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_payload(identifier, value, version):
    """Return the compact, key-sorted JSON string of the known fields."""
    payload = {"id": identifier, "value": value, "version": version}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum_of(identifier, value, version):
    """Return the lowercase SHA-256 hex digest of the canonical payload."""
    payload = _canonical_payload(identifier, value, version)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode(record):
    """Encode ``record`` into a compact, deterministic version 2 wire string.

    ``record`` must supply a non-empty string ``id`` and an integer,
    non-boolean ``value``. The input is never mutated. Invalid input raises
    :class:`ValueError`.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if "id" not in record:
        raise ValueError("record is missing required field 'id'")
    if "value" not in record:
        raise ValueError("record is missing required field 'value'")

    identifier = record["id"]
    value = record["value"]

    if not _is_valid_id(identifier):
        raise ValueError("'id' must be a non-empty string")
    if not _is_valid_value(value):
        raise ValueError("'value' must be a non-boolean integer")

    checksum = _checksum_of(identifier, value, _CURRENT_VERSION)
    output = {
        "id": identifier,
        "value": value,
        "version": _CURRENT_VERSION,
        "checksum": checksum,
    }
    return json.dumps(output, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a version 1 or version 2 wire string into a new dict.

    Returns a fresh dict containing ``id``, ``value`` and ``version``. Absent
    ``version`` is treated as ``1``. Malformed JSON, unsupported versions,
    invalid fields, unknown fields or a checksum mismatch raise
    :class:`CodecError`.
    """
    if not isinstance(text, str):
        raise CodecError("wire input must be a string")

    try:
        record = json.loads(text)
    except ValueError as exc:  # json.JSONDecodeError is a ValueError subclass
        raise CodecError("malformed JSON: {}".format(exc))

    if not isinstance(record, dict):
        raise CodecError("wire record must be a JSON object")

    version = record.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int):
        raise CodecError("'version' must be an integer")
    if version not in _ALLOWED_FIELDS:
        raise CodecError("unsupported version: {!r}".format(version))

    allowed = _ALLOWED_FIELDS[version]
    unknown = set(record) - allowed
    if unknown:
        raise CodecError(
            "unknown field(s) for version {}: {}".format(
                version, sorted(unknown)
            )
        )

    if "id" not in record:
        raise CodecError("wire record is missing required field 'id'")
    if "value" not in record:
        raise CodecError("wire record is missing required field 'value'")

    identifier = record["id"]
    value = record["value"]
    if not _is_valid_id(identifier):
        raise CodecError("'id' must be a non-empty string")
    if not _is_valid_value(value):
        raise CodecError("'value' must be a non-boolean integer")

    if version == 2:
        checksum = record.get("checksum")
        if not isinstance(checksum, str):
            raise CodecError("'checksum' must be a string")
        expected = _checksum_of(identifier, value, version)
        # Constant-time comparison to avoid leaking digest information.
        if not _constant_time_equal(checksum, expected):
            raise CodecError("checksum mismatch")

    return {"id": identifier, "value": value, "version": version}


def _constant_time_equal(left, right):
    """Compare two strings without short-circuiting on the first difference."""
    if len(left) != len(right):
        return False
    result = 0
    for a, b in zip(left, right):
        result |= ord(a) ^ ord(b)
    return result == 0