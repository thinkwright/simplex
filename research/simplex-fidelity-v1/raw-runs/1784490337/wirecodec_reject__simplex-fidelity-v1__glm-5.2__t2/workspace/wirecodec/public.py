"""Public API for the wirecodec wire-format codec.

This module exposes :func:`encode`, :func:`decode` and :class:`CodecError`.

Only the Python standard library is used (``json`` and ``hashlib``); the
checksum is a lowercase SHA-256 hex digest.
"""

import hashlib
import json

__all__ = ["encode", "decode", "CodecError"]

# Current wire format version produced by :func:`encode`.
_CURRENT_VERSION = 2

# Top-level fields allowed for each supported version.
_KNOWN_FIELDS = {
    1: frozenset({"id", "value", "version"}),
    2: frozenset({"id", "value", "version", "checksum"}),
}


class CodecError(Exception):
    """Raised when a wire-format record cannot be decoded."""


def _is_non_empty_string(value):
    return isinstance(value, str) and len(value) > 0


def _is_integer_non_bool(value):
    # ``bool`` is a subclass of ``int``; exclude it explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_json(obj):
    """Compact JSON with sorted keys -- deterministic across calls."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _checksum(record_id, record_value, version):
    payload = _canonical_json(
        {"id": record_id, "value": record_value, "version": version}
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into the version 2 wire format.

    ``record`` must be a mapping containing exactly a non-empty string ``id``
    and an integer (non-boolean) ``value``.  The input is never mutated.
    Returns a compact, deterministically ordered JSON string.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Read-only access: never mutate the caller's mapping.
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value'")

    record_id = record["id"]
    record_value = record["value"]

    if not _is_non_empty_string(record_id):
        raise ValueError("id must be a non-empty string")
    if not _is_integer_non_bool(record_value):
        raise ValueError("value must be an integer and not a boolean")

    digest = _checksum(record_id, record_value, _CURRENT_VERSION)
    return _canonical_json(
        {
            "id": record_id,
            "value": record_value,
            "version": _CURRENT_VERSION,
            "checksum": digest,
        }
    )


def decode(text):
    """Decode a wire-format JSON string into a record dict.

    Returns a new dict with ``id``, ``value`` and ``version``.  Absent
    ``version`` is treated as 1.  Raises :class:`CodecError` for malformed
    JSON, unsupported versions, invalid or unknown fields, or a version 2
    checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("input must be a JSON string")

    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise CodecError("malformed JSON: %s" % exc) from exc

    if not isinstance(obj, dict):
        raise CodecError("wire record must be a JSON object")

    if "version" in obj:
        version = obj["version"]
        if not _is_integer_non_bool(version) or version not in (1, 2):
            raise CodecError("unsupported version: %r" % (version,))
    else:
        version = 1

    known_fields = _KNOWN_FIELDS[version]
    unknown = set(obj.keys()) - known_fields
    if unknown:
        raise CodecError(
            "unknown top-level field(s): %s" % ", ".join(sorted(unknown))
        )

    if "id" not in obj or not _is_non_empty_string(obj["id"]):
        raise CodecError("invalid field 'id'")
    if "value" not in obj or not _is_integer_non_bool(obj["value"]):
        raise CodecError("invalid field 'value'")

    record_id = obj["id"]
    record_value = obj["value"]

    if version == 2:
        checksum = obj.get("checksum")
        if not isinstance(checksum, str):
            raise CodecError("invalid field 'checksum'")
        if checksum != _checksum(record_id, record_value, _CURRENT_VERSION):
            raise CodecError("checksum mismatch")

    return {"id": record_id, "value": record_value, "version": version}