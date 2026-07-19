"""Implementation of the wirecodec encode/decode functions.

Only the Python standard library and hashlib (SHA-256) are used.
"""

import hashlib
import json

from wirecodec.errors import CodecError

_CURRENT_VERSION = 2
_KNOWN_FIELDS_V1 = {"id", "value", "version"}
_KNOWN_FIELDS_V2 = {"id", "value", "version", "checksum"}


def _validate_record(record):
    """Validate that record is a dict with a non-empty string id and a non-bool int value.

    Returns (id_str, value_int) on success.
    Raises ValueError on invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if "id" not in record:
        raise ValueError("record must contain an 'id' field")
    if "value" not in record:
        raise ValueError("record must contain a 'value' field")
    id_val = record["id"]
    if not isinstance(id_val, str):
        raise ValueError("'id' must be a string")
    if id_val == "":
        raise ValueError("'id' must be a non-empty string")
    value_val = record["value"]
    # bool is a subclass of int in Python; explicitly reject booleans.
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise ValueError("'value' must be an integer (non-boolean)")
    return id_val, value_val


def _canonical_payload(record):
    """Build the compact sorted-key JSON payload used for checksum input.

    Only includes id, value, and version.
    """
    payload = {
        "id": record["id"],
        "value": record["value"],
        "version": record["version"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum_for(record):
    """Compute the lowercase SHA-256 hex digest over the canonical payload."""
    canonical = _canonical_payload(record)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a deterministic version 2 JSON string.

    Requirements:
      - record must be a dict with non-empty string id and non-boolean int value
      - record is not mutated
      - returns compact JSON with sorted keys containing version, id, value, checksum
      - checksum is lowercase SHA-256 hex over compact sorted JSON of {id, value, version}
    """
    id_val, value_val = _validate_record(record)

    # Build the version 2 record without mutating the input.
    out_record = {
        "id": id_val,
        "value": value_val,
        "version": _CURRENT_VERSION,
    }
    out_record["checksum"] = _checksum_for(out_record)

    return json.dumps(out_record, sort_keys=True, separators=(",", ":"))


def _parse_json_object(text):
    """Parse text as a JSON object. Raises CodecError on failure."""
    if not isinstance(text, str):
        raise CodecError("input must be a string")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CodecError("malformed JSON: {}".format(exc)) from exc
    if not isinstance(obj, dict):
        raise CodecError("JSON input must be an object")
    return obj


def _check_unknown_fields(obj, known):
    """Raise CodecError if obj contains any field not in known."""
    for key in obj.keys():
        if key not in known:
            raise CodecError("unknown field: {}".format(key))


def _validate_v1_fields(obj):
    """Validate the field types for a version 1 record (no checksum)."""
    id_val = obj.get("id")
    if not isinstance(id_val, str) or id_val == "":
        raise CodecError("'id' must be a non-empty string")
    value_val = obj.get("value")
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("'value' must be an integer (non-boolean)")


def _validate_v2_fields(obj):
    """Validate the field types for a version 2 record (including checksum)."""
    id_val = obj.get("id")
    if not isinstance(id_val, str) or id_val == "":
        raise CodecError("'id' must be a non-empty string")
    value_val = obj.get("value")
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("'value' must be an integer (non-boolean)")
    checksum_val = obj.get("checksum")
    if not isinstance(checksum_val, str):
        raise CodecError("'checksum' must be a string")


def decode(text):
    """Decode a wirecodec JSON string into a new dict.

    - Accepts a JSON object string.
    - Absent version is treated as version 1.
    - Returns a new dict containing id, value, and version.
    - For version 2, validates the checksum before returning.
    - Raises CodecError for malformed JSON, unsupported versions,
      invalid fields, unknown top-level fields, or checksum mismatch.
    """
    obj = _parse_json_object(text)

    # Determine version (absent -> 1).
    if "version" in obj:
        version_val = obj["version"]
        if isinstance(version_val, bool) or not isinstance(version_val, int):
            raise CodecError("'version' must be an integer")
        version = version_val
    else:
        version = 1

    if version == 1:
        _check_unknown_fields(obj, _KNOWN_FIELDS_V1)
        _validate_v1_fields(obj)
        return {
            "id": obj["id"],
            "value": obj["value"],
            "version": 1,
        }

    if version == 2:
        _check_unknown_fields(obj, _KNOWN_FIELDS_V2)
        _validate_v2_fields(obj)
        # Recompute checksum over canonical payload and compare.
        canonical_record = {
            "id": obj["id"],
            "value": obj["value"],
            "version": 2,
        }
        expected = _checksum_for(canonical_record)
        if obj["checksum"] != expected:
            raise CodecError("checksum mismatch")
        return {
            "id": obj["id"],
            "value": obj["value"],
            "version": 2,
        }

    raise CodecError("unsupported version: {}".format(version))