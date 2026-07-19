import json
import hashlib


class CodecError(Exception):
    """Raised when decoding fails due to malformed, unsupported, or invalid wire data."""
    pass


def _validate_id(id_val):
    """Validate that id is a non-empty string."""
    if not isinstance(id_val, str) or len(id_val) == 0:
        return False
    return True


def _validate_value(value_val):
    """Validate that value is an integer but not a boolean."""
    if isinstance(value_val, bool):
        return False
    if not isinstance(value_val, int):
        return False
    return True


def _compute_checksum(id_val, value_val, version):
    """Compute SHA-256 hex checksum over compact sorted JSON of id, value, version."""
    canonical = {"id": id_val, "value": value_val, "version": version}
    canonical_json = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a version 2 wire format JSON string.

    Args:
        record: A dict with exactly 'id' (non-empty string) and 'value' (integer, not boolean).

    Returns:
        Compact JSON string with sorted keys containing version, id, value, and checksum.

    Raises:
        ValueError: If the record is invalid.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Check that record has exactly 'id' and 'value' keys
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value' keys")

    id_val = record["id"]
    value_val = record["value"]

    if not _validate_id(id_val):
        raise ValueError("id must be a non-empty string")

    if not _validate_value(value_val):
        raise ValueError("value must be an integer (not a boolean)")

    version = 2
    checksum = _compute_checksum(id_val, value_val, version)

    output = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": version,
    }

    return json.dumps(output, separators=(",", ":"), sort_keys=True)


def decode(text):
    """Decode a wire format JSON string into a record dict.

    Args:
        text: A JSON object string.

    Returns:
        A new dict containing id, value, and version.

    Raises:
        CodecError: If the input is malformed, unsupported, or invalid.
    """
    if not isinstance(text, str):
        raise CodecError("input must be a string")

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise CodecError(f"malformed JSON: {e}")

    if not isinstance(parsed, dict):
        raise CodecError("JSON must be an object")

    # Determine version
    version = parsed.get("version", 1)

    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("version must be an integer")

    if version == 1:
        # Known fields for version 1
        if "version" in parsed:
            known_fields = {"id", "value", "version"}
        else:
            known_fields = {"id", "value"}

        unknown = set(parsed.keys()) - known_fields
        if unknown:
            raise CodecError(f"unknown fields: {unknown}")

        # Validate required fields
        if "id" not in parsed:
            raise CodecError("missing 'id' field")
        if "value" not in parsed:
            raise CodecError("missing 'value' field")

        id_val = parsed["id"]
        value_val = parsed["value"]

        if not _validate_id(id_val):
            raise CodecError("id must be a non-empty string")
        if not _validate_value(value_val):
            raise CodecError("value must be an integer (not a boolean)")

        return {"id": id_val, "value": value_val, "version": 1}

    elif version == 2:
        known_fields = {"id", "value", "version", "checksum"}

        unknown = set(parsed.keys()) - known_fields
        if unknown:
            raise CodecError(f"unknown fields: {unknown}")

        # Validate required fields
        if "id" not in parsed:
            raise CodecError("missing 'id' field")
        if "value" not in parsed:
            raise CodecError("missing 'value' field")
        if "checksum" not in parsed:
            raise CodecError("missing 'checksum' field")

        id_val = parsed["id"]
        value_val = parsed["value"]
        checksum = parsed["checksum"]

        if not _validate_id(id_val):
            raise CodecError("id must be a non-empty string")
        if not _validate_value(value_val):
            raise CodecError("value must be an integer (not a boolean)")
        if not isinstance(checksum, str):
            raise CodecError("checksum must be a string")

        # Validate checksum
        expected_checksum = _compute_checksum(id_val, value_val, 2)
        if checksum != expected_checksum:
            raise CodecError("checksum mismatch")

        return {"id": id_val, "value": value_val, "version": 2}

    else:
        raise CodecError(f"unsupported version: {version}")
