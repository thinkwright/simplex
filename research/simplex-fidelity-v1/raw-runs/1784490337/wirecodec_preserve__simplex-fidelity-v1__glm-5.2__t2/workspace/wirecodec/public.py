"""Public wire-codec API.

Encodes and decodes compact JSON wire records. Version 2 records carry a
SHA-256 checksum over the canonical (compact, sorted) JSON of the id, value and
version fields. Only the Python standard library is used.
"""

import hashlib
import json

__all__ = ["encode", "decode", "CodecError"]

_CURRENT_VERSION = 2
_SUPPORTED_VERSIONS = (1, 2)
_BASE_FIELDS = ("id", "value", "version")


class CodecError(Exception):
    """Raised when wire data is malformed, unsupported or fails validation."""


def _canonical_payload(record_id, value, version):
    """Return compact, sorted-key JSON for the checksum input fields."""
    payload = {"id": record_id, "value": value, "version": version}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum(record_id, value, version):
    """Return the lowercase SHA-256 hex digest of the canonical payload."""
    data = _canonical_payload(record_id, value, version).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _is_valid_id(record_id):
    return isinstance(record_id, str) and record_id != ""


def _is_valid_value(value):
    # bool is a subclass of int, so it must be rejected explicitly.
    return not isinstance(value, bool) and isinstance(value, int)


def encode(record):
    """Encode a record into a compact, deterministic version 2 JSON string.

    ``record`` must contain a non-empty string ``id`` and an integer
    (non-boolean) ``value``. The input is never mutated. Invalid input raises
    ``ValueError``.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict containing 'id' and 'value'")
    if "id" not in record or "value" not in record:
        raise ValueError("record must contain 'id' and 'value'")

    record_id = record["id"]
    value = record["value"]

    if not _is_valid_id(record_id):
        raise ValueError("'id' must be a non-empty string")
    if not _is_valid_value(value):
        raise ValueError("'value' must be an integer and not a boolean")

    checksum = _checksum(record_id, value, _CURRENT_VERSION)
    output = {
        "checksum": checksum,
        "id": record_id,
        "value": value,
        "version": _CURRENT_VERSION,
    }
    return json.dumps(output, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a JSON wire-record string into a new dict.

    Returns a dict with ``id``, ``value`` and ``version`` (absent version is
    treated as 1). Unknown top-level fields are preserved in an ``extras`` dict,
    omitted when empty. Version 2 records are checksum-validated. Any malformed,
    unsupported, invalid or checksum-mismatching input raises ``CodecError``.
    """
    if not isinstance(text, str):
        raise CodecError("decode input must be a JSON object string")

    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise CodecError("malformed JSON: %s" % exc) from exc

    if not isinstance(parsed, dict):
        raise CodecError("wire data must be a JSON object")

    # Resolve version: absent means 1.
    if "version" in parsed:
        version = parsed["version"]
        if isinstance(version, bool) or not isinstance(version, int):
            raise CodecError("invalid 'version' field")
        if version not in _SUPPORTED_VERSIONS:
            raise CodecError("unsupported version: %r" % (version,))
    else:
        version = 1

    # Validate required fields.
    if "id" not in parsed:
        raise CodecError("missing 'id' field")
    record_id = parsed["id"]
    if not _is_valid_id(record_id):
        raise CodecError("invalid 'id' field")

    if "value" not in parsed:
        raise CodecError("missing 'value' field")
    value = parsed["value"]
    if not _is_valid_value(value):
        raise CodecError("invalid 'value' field")

    # Validate version 2 checksum before returning.
    if version == 2:
        if "checksum" not in parsed:
            raise CodecError("missing 'checksum' field for version 2")
        checksum = parsed["checksum"]
        if not isinstance(checksum, str):
            raise CodecError("invalid 'checksum' field")
        expected = _checksum(record_id, value, _CURRENT_VERSION)
        if checksum != expected:
            raise CodecError("checksum mismatch")

    # Preserve unknown top-level fields.
    known = set(_BASE_FIELDS)
    if version == 2:
        known.add("checksum")
    extras = {key: val for key, val in parsed.items() if key not in known}

    result = {"id": record_id, "value": value, "version": version}
    if extras:
        result["extras"] = extras
    return result