"""Wire codec implementation.

A small, dependency-free codec for "wire" records.

* :func:`encode` turns an in-memory record into a compact, deterministic
  version 2 JSON string protected by a SHA-256 checksum.
* :func:`decode` turns a wire string back into a fresh record dict, accepting
  legacy version 1 records (no checksum) and validating version 2 checksums.

Only the Python standard library is used (``json`` and ``hashlib``).
"""

import hashlib
import json

__all__ = ["CodecError", "encode", "decode"]

# Current wire format version produced by :func:`encode`.
_CURRENT_VERSION = 2

# Top-level fields permitted for each supported version. Any field outside
# these sets makes a record invalid (see R6).
_ALLOWED_FIELDS = {
    1: frozenset({"id", "value", "version"}),
    2: frozenset({"id", "value", "version", "checksum"}),
}


class CodecError(Exception):
    """Raised when a wire string is malformed or fails validation."""


def _is_non_empty_string(value):
    """Return True when *value* is a ``str`` that is not empty."""
    return isinstance(value, str) and value != ""


def _is_int_non_bool(value):
    """Return True when *value* is an ``int`` but not a ``bool``.

    ``bool`` is a subclass of ``int`` in Python, so it has to be excluded
    explicitly (see R2 / R7).
    """
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_payload(record_id, value, version):
    """Return the compact, sorted-keys JSON of the checksummed fields.

    The checksum is computed over exactly ``id``, ``value`` and ``version``
    (see R3).
    """
    payload = {"id": record_id, "value": value, "version": version}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum(record_id, value, version):
    """Return the lowercase SHA-256 hex digest of the canonical payload."""
    data = _canonical_payload(record_id, value, version).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def encode(record):
    """Encode *record* into a compact, deterministic version 2 wire string.

    *record* must be a mapping containing exactly a non-empty string ``id``
    and an integer (non-boolean) ``value``. The input is never mutated.

    Raises:
        ValueError: when *record* is not a dict, has the wrong keys, or the
            ``id`` / ``value`` fields fail validation.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # The record must contain exactly the ``id`` and ``value`` fields.
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value'")

    record_id = record["id"]
    value = record["value"]

    if not _is_non_empty_string(record_id):
        raise ValueError("'id' must be a non-empty string")
    if not _is_int_non_bool(value):
        raise ValueError("'value' must be an integer and not a boolean")

    digest = _checksum(record_id, value, _CURRENT_VERSION)
    output = {
        "version": _CURRENT_VERSION,
        "id": record_id,
        "value": value,
        "checksum": digest,
    }
    # Compact JSON with sorted keys -> byte-for-byte stable output (R7).
    return json.dumps(output, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a wire string *text* into a fresh ``{id, value, version}`` dict.

    A missing ``version`` field is treated as version 1 (legacy records with
    no checksum). Version 2 records are validated against their SHA-256
    checksum before being returned.

    Raises:
        CodecError: for malformed JSON, non-object input, unsupported
            versions, invalid fields, unknown fields or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("decode input must be a string")

    try:
        record = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError("malformed JSON") from exc

    if not isinstance(record, dict):
        raise CodecError("wire input must be a JSON object")

    # Determine the version: absent means 1, otherwise it must be 1 or 2.
    if "version" in record:
        version = record["version"]
        if not (_is_int_non_bool(version) and version in (1, 2)):
            raise CodecError("unsupported version")
    else:
        version = 1

    # Reject any unknown top-level field for both version 1 and 2 (R6).
    allowed = _ALLOWED_FIELDS[version]
    for key in record:
        if key not in allowed:
            raise CodecError("unknown field: %r" % (key,))

    # Validate the required fields.
    if "id" not in record or not _is_non_empty_string(record["id"]):
        raise CodecError("invalid 'id' field")
    if "value" not in record or not _is_int_non_bool(record["value"]):
        raise CodecError("invalid 'value' field")

    record_id = record["id"]
    value = record["value"]

    if version == 2:
        checksum = record.get("checksum")
        if not isinstance(checksum, str):
            raise CodecError("invalid 'checksum' field")
        expected = _checksum(record_id, value, version)
        if checksum != expected:
            raise CodecError("checksum mismatch")

    # Return a brand new dict containing only id, value and version (R4).
    return {"id": record_id, "value": value, "version": version}