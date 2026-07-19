"""wirecodec public API: encode, decode, CodecError."""

import json
import hashlib


class CodecError(Exception):
    """Raised when decoding fails due to malformed, unsupported, or invalid data."""
    pass


_KNOWN_FIELDS = {"id", "value", "version", "checksum"}


def _compute_checksum(id_val, value, version):
    """Compute SHA-256 hex checksum over compact sorted JSON of id, value, version."""
    payload = {"id": id_val, "value": value, "version": version}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record dict into a compact version-2 JSON string.

    Requires record to have a non-empty string 'id' and an integer non-boolean 'value'.
    Does not mutate the input record.
    Raises ValueError for invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Validate id
    if "id" not in record:
        raise ValueError("record must contain 'id'")
    id_val = record["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("'id' must be a non-empty string")

    # Validate value
    if "value" not in record:
        raise ValueError("record must contain 'value'")
    value = record["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'value' must be an integer (not boolean)")

    version = 2
    checksum = _compute_checksum(id_val, value, version)

    output = {
        "checksum": checksum,
        "id": id_val,
        "value": value,
        "version": version,
    }
    return json.dumps(output, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a JSON string into a record dict.

    Treats absent version as version 1.
    Validates version 2 checksum.
    Preserves unknown top-level fields in an 'extras' dict (omitted when empty).
    Raises CodecError for malformed JSON, unsupported versions, invalid fields,
    or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("input must be a string")

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise CodecError(f"malformed JSON: {e}")

    if not isinstance(data, dict):
        raise CodecError("JSON must be an object")

    # Determine version
    version = data.get("version", 1)

    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("version must be an integer")

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # Validate id
    if "id" not in data:
        raise CodecError("missing 'id' field")
    id_val = data["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise CodecError("'id' must be a non-empty string")

    # Validate value
    if "value" not in data:
        raise CodecError("missing 'value' field")
    value = data["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodecError("'value' must be an integer (not boolean)")

    # Version 2 checksum validation
    if version == 2:
        if "checksum" not in data:
            raise CodecError("version 2 record missing checksum")
        expected_checksum = _compute_checksum(id_val, value, version)
        if data["checksum"] != expected_checksum:
            raise CodecError("checksum mismatch")

    # Build result
    result = {"id": id_val, "value": value, "version": version}

    # Collect extras (unknown top-level fields)
    extras = {}
    for key, val in data.items():
        if key not in _KNOWN_FIELDS:
            extras[key] = val
    if extras:
        result["extras"] = extras

    return result
