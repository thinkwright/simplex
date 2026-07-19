"""Public API for the wirecodec package."""

import json
import hashlib


class CodecError(Exception):
    """Raised when decoding encounters malformed, unsupported, or invalid data."""
    pass


def _compute_checksum(id_val, value_val, version):
    """Compute SHA-256 hex digest over compact sorted JSON of {id, value, version}."""
    payload = json.dumps(
        {"id": id_val, "value": value_val, "version": version},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a compact version-2 JSON string with checksum.

    The record must be a dict with exactly a non-empty string 'id' and an
    integer (non-boolean) 'value'.  The input dict is never mutated.

    Returns compact JSON (sorted keys) containing version, id, value, checksum.
    Raises ValueError on invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value'")

    id_val = record["id"]
    value_val = record["value"]

    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("id must be a non-empty string")

    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise ValueError("value must be an integer (not boolean)")

    checksum = _compute_checksum(id_val, value_val, 2)

    result = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": 2,
    }
    return json.dumps(result, separators=(",", ":"), sort_keys=True)


def decode(text):
    """Decode a JSON wire-format string into a record dict.

    - Absent version is treated as version 1.
    - Version 2 records are checksum-validated.
    - Unknown top-level fields are collected into an 'extras' dict (omitted
      when empty).

    Returns a new dict with at least id, value, and version.
    Raises CodecError for malformed JSON, unsupported versions, invalid
    fields, or checksum mismatch.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise CodecError("JSON value must be an object")

    # Determine version (absent → 1)
    version = data.get("version", 1)

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # Validate id
    if "id" not in data:
        raise CodecError("missing 'id' field")
    id_val = data["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise CodecError("invalid 'id' field")

    # Validate value
    if "value" not in data:
        raise CodecError("missing 'value' field")
    value_val = data["value"]
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("invalid 'value' field")

    # Version-2 checksum validation
    if version == 2:
        if "checksum" not in data:
            raise CodecError("missing checksum for version 2 record")
        expected = _compute_checksum(id_val, value_val, 2)
        if data["checksum"] != expected:
            raise CodecError("checksum mismatch")

    # Build result
    result = {"id": id_val, "value": value_val, "version": version}

    # Collect unknown top-level fields into extras
    known_fields = {"id", "value", "version"}
    if version == 2:
        known_fields.add("checksum")

    extras = {k: v for k, v in data.items() if k not in known_fields}
    if extras:
        result["extras"] = extras

    return result
