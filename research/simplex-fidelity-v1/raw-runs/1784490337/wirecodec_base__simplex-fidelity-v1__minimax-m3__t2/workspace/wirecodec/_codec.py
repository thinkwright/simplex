"""Internal codec implementation.

Only the standard library is used (hashlib for SHA-256).
"""

import hashlib
import json


class CodecError(Exception):
    """Raised when decoding fails for any reason (malformed, unsupported, checksum mismatch)."""


_CURRENT_VERSION = 2


def _validate_record(record):
    """Validate the input record for encoding.

    Returns a (id_str, value_int) pair on success.
    Raises ValueError on invalid input. Does not mutate record.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if "id" not in record:
        raise ValueError("record must contain an 'id' field")
    if "value" not in record:
        raise ValueError("record must contain a 'value' field")

    id_value = record["id"]
    if not isinstance(id_value, str):
        raise ValueError("'id' must be a string")
    if id_value == "":
        raise ValueError("'id' must be a non-empty string")

    value = record["value"]
    # bool is a subclass of int in Python; explicitly reject booleans.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'value' must be an integer (non-boolean)")

    return id_value, value


def _canonical_payload(id_str, value):
    """Build the compact JSON payload used for the checksum (sorted keys)."""
    payload = {"id": id_str, "value": value, "version": _CURRENT_VERSION}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum(id_str, value):
    """Compute the lowercase SHA-256 hex digest over the canonical payload."""
    canonical = _canonical_payload(id_str, value)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a compact version 2 JSON string with a checksum.

    The record must be a dict with a non-empty string 'id' and an integer
    (non-boolean) 'value'. The input is not mutated. Returns a compact JSON
    object string with sorted keys containing version, id, value, and checksum.
    """
    id_str, value = _validate_record(record)

    checksum = _checksum(id_str, value)
    out = {
        "version": _CURRENT_VERSION,
        "id": id_str,
        "value": value,
        "checksum": checksum,
    }
    return json.dumps(out, sort_keys=True, separators=(",", ":"))


def _parse_json_object(text):
    """Parse text as a JSON object, raising CodecError on failure."""
    if not isinstance(text, str):
        raise CodecError("input must be a string")
    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise CodecError("JSON input must be an object")
    return obj


def _coerce_id(raw):
    if not isinstance(raw, str):
        raise CodecError("'id' must be a string")
    if raw == "":
        raise CodecError("'id' must be a non-empty string")
    return raw


def _coerce_value(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise CodecError("'value' must be an integer (non-boolean)")
    return raw


def _decode_v1(obj):
    """Decode a version 1 (or absent-version) record."""
    if "id" not in obj:
        raise CodecError("missing required field 'id'")
    if "value" not in obj:
        raise CodecError("missing required field 'value'")
    id_str = _coerce_id(obj["id"])
    value = _coerce_value(obj["value"])
    return {"id": id_str, "value": value, "version": 1}


def _decode_v2(obj):
    """Decode a version 2 record, validating the checksum."""
    if "id" not in obj:
        raise CodecError("missing required field 'id'")
    if "value" not in obj:
        raise CodecError("missing required field 'value'")
    if "checksum" not in obj:
        raise CodecError("missing required field 'checksum'")
    id_str = _coerce_id(obj["id"])
    value = _coerce_value(obj["value"])
    checksum = obj["checksum"]
    if not isinstance(checksum, str):
        raise CodecError("'checksum' must be a string")

    expected = _checksum(id_str, value)
    if checksum != expected:
        raise CodecError("checksum mismatch")

    return {"id": id_str, "value": value, "version": 2}


def decode(text):
    """Decode a JSON record string.

    Accepts version 1 (or absent version) and version 2 records. Version 2
    records are validated against their checksum. Unknown top-level fields
    are discarded after validation. Raises CodecError on malformed JSON,
    unsupported versions, invalid fields, or checksum mismatch.
    """
    obj = _parse_json_object(text)

    if "version" not in obj:
        return _decode_v1(obj)

    version = obj["version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise CodecError("'version' must be an integer")

    if version == 1:
        return _decode_v1(obj)
    if version == 2:
        return _decode_v2(obj)
    raise CodecError(f"unsupported version: {version}")