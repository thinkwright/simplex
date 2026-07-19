"""Wire codec public API.

Only the Python standard library is used. The cryptographic digest is
SHA-256 from :mod:`hashlib`.

Public surface:
    encode(record)  -> str   : deterministic version 2 wire record.
    decode(text)    -> dict  : parse a version 1 or version 2 wire record.
    CodecError                 : raised for malformed/invalid wire input.
"""

import hashlib
import json

__all__ = ["CodecError", "decode", "encode"]

# The version produced by :func:`encode`.
_CURRENT_VERSION = 2

# Versions that :func:`decode` understands.
_SUPPORTED_VERSIONS = (1, 2)


class CodecError(Exception):
    """Raised when a wire record is malformed, unsupported, or invalid."""


def _canonical_payload(identifier, value, version):
    """Return compact, key-sorted JSON for the known data fields.

    This is the exact byte sequence over which the SHA-256 checksum is
    computed for version 2 records.
    """
    return json.dumps(
        {"id": identifier, "value": value, "version": version},
        sort_keys=True,
        separators=(",", ":"),
    )


def encode(record):
    """Encode a record as a compact, deterministic version 2 wire string.

    ``record`` must be a mapping containing exactly two entries:

    * ``id``   -- a non-empty string.
    * ``value`` -- an integer that is not a :class:`bool`.

    The input is never mutated. Invalid input raises :class:`ValueError`.

    The returned string is compact JSON with sorted object keys and four
    fields: ``checksum``, ``id``, ``value`` and ``version``. ``checksum``
    is the lowercase SHA-256 hex digest of the canonical payload built from
    only ``id``, ``value`` and ``version``.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value'")

    identifier = record["id"]
    value = record["value"]

    if not isinstance(identifier, str) or identifier == "":
        raise ValueError("id must be a non-empty string")
    # bool is a subclass of int in Python; reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer and not a boolean")

    payload = _canonical_payload(identifier, value, _CURRENT_VERSION)
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return json.dumps(
        {
            "id": identifier,
            "value": value,
            "version": _CURRENT_VERSION,
            "checksum": checksum,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def decode(text):
    """Decode a wire record string into a new ``{id, value, version}`` dict.

    ``text`` must be a JSON object string. A missing ``version`` field is
    treated as version 1. Unknown top-level fields are discarded after the
    known fields are validated.

    :class:`CodecError` is raised for malformed JSON, a non-object payload,
    unsupported versions, invalid known fields, or (for version 2) a
    checksum mismatch.
    """
    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        # json.JSONDecodeError and UnicodeDecodeError are ValueError
        # subclasses; non-str/bytes input raises TypeError.
        raise CodecError("malformed JSON input") from exc

    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")

    version = obj["version"] if "version" in obj else 1
    if isinstance(version, bool) or not isinstance(version, int):
        raise CodecError("invalid version field")
    if version not in _SUPPORTED_VERSIONS:
        raise CodecError("unsupported version: %r" % (version,))

    if "id" not in obj:
        raise CodecError("missing id field")
    identifier = obj["id"]
    if not isinstance(identifier, str) or identifier == "":
        raise CodecError("invalid id field")

    if "value" not in obj:
        raise CodecError("missing value field")
    value = obj["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodecError("invalid value field")

    if version == 2:
        if "checksum" not in obj:
            raise CodecError("missing checksum field")
        checksum = obj["checksum"]
        if not isinstance(checksum, str):
            raise CodecError("invalid checksum field")
        expected = hashlib.sha256(
            _canonical_payload(identifier, value, version).encode("utf-8")
        ).hexdigest()
        if expected != checksum:
            raise CodecError("checksum mismatch")

    # Unknown top-level fields are discarded: only the known data fields are
    # returned, in a brand new dict.
    return {"id": identifier, "value": value, "version": version}