"""Public API for the wirecodec package."""

import json
import hashlib


class CodecError(Exception):
    """Raised when a wire-format record is malformed, unsupported, or fails checksum."""


def _validate_id(id_val):
    """Return True if id_val is a non-empty string."""
    return isinstance(id_val, str) and len(id_val) > 0


def _validate_value(value_val):
    """Return True if value_val is an integer but not a boolean."""
    return isinstance(value_val, int) and not isinstance(value_val, bool)


def _compact_json(obj):
    """Produce compact JSON with sorted keys."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _compute_checksum(id_val, value_val, version):
    """Compute SHA-256 hex digest over the canonical known-field payload."""
    payload = _compact_json({"id": id_val, "value": value_val, "version": version})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a version-2 wire-format JSON string.

    Parameters
    ----------
    record : dict
        Must contain exactly a non-empty string ``id`` and an integer
        (non-boolean) ``value``.

    Returns
    -------
    str
        Compact JSON with sorted keys containing version, id, value,
        and checksum.

    Raises
    ------
    ValueError
        If the record is invalid (missing/wrong-type fields, boolean value,
        empty id, etc.).
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Must have exactly 'id' and 'value'
    if "id" not in record:
        raise ValueError("record must contain 'id'")
    if "value" not in record:
        raise ValueError("record must contain 'value'")

    id_val = record["id"]
    value_val = record["value"]

    if not _validate_id(id_val):
        raise ValueError("'id' must be a non-empty string")
    if not _validate_value(value_val):
        raise ValueError("'value' must be an integer (not a boolean)")

    version = 2
    checksum = _compute_checksum(id_val, value_val, version)

    full_record = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": version,
    }

    return _compact_json(full_record)


def decode(text):
    """Decode a wire-format JSON string into a record dict.

    Parameters
    ----------
    text : str
        A JSON object string representing a version-1 or version-2 record.

    Returns
    -------
    dict
        A new dict containing ``id``, ``value``, and ``version``.

    Raises
    ------
    CodecError
        If the JSON is malformed, the version is unsupported, fields are
        invalid, or the checksum does not match (version 2).
    """
    if not isinstance(text, str):
        raise CodecError("input must be a string")

    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise CodecError("JSON root must be an object")

    # Determine version: absent means version 1
    version = obj.get("version", 1)

    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("'version' must be an integer")

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # Validate required fields
    if "id" not in obj:
        raise CodecError("missing required field 'id'")
    if "value" not in obj:
        raise CodecError("missing required field 'value'")

    id_val = obj["id"]
    value_val = obj["value"]

    if not _validate_id(id_val):
        raise CodecError("'id' must be a non-empty string")
    if not _validate_value(value_val):
        raise CodecError("'value' must be an integer (not a boolean)")

    if version == 2:
        # Validate checksum
        if "checksum" not in obj:
            raise CodecError("version 2 record missing checksum")

        expected_checksum = _compute_checksum(id_val, value_val, version)
        actual_checksum = obj["checksum"]

        if not isinstance(actual_checksum, str):
            raise CodecError("checksum must be a string")

        if actual_checksum != expected_checksum:
            raise CodecError(
                f"checksum mismatch: expected {expected_checksum}, "
                f"got {actual_checksum}"
            )

    # Return only known fields (discard unknown top-level fields)
    return {"id": id_val, "value": value_val, "version": version}
