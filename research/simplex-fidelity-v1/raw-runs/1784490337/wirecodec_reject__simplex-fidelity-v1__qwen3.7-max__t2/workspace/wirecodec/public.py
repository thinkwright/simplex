"""wirecodec public API: encode, decode, CodecError."""

import json
import hashlib


class CodecError(Exception):
    """Raised when a wire-format record is malformed, unsupported, or fails checksum."""
    pass


def encode(record):
    """Encode a record dict into compact version-2 JSON with a SHA-256 checksum.

    The record must contain:
      - id:    a non-empty string
      - value: an integer (not a bool)

    Returns a compact JSON string (sorted keys, no whitespace).
    Does NOT mutate the input record.
    Raises ValueError on invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # --- validate id ---
    if "id" not in record:
        raise ValueError("record is missing required field 'id'")
    id_val = record["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("'id' must be a non-empty string")

    # --- validate value ---
    if "value" not in record:
        raise ValueError("record is missing required field 'value'")
    value_val = record["value"]
    # bool is a subclass of int in Python, so check bool first
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise ValueError("'value' must be an integer (not a boolean)")

    # --- build checksum payload (id, value, version only) ---
    checksum_payload = json.dumps(
        {"id": id_val, "value": value_val, "version": 2},
        sort_keys=True,
        separators=(",", ":"),
    )
    checksum = hashlib.sha256(checksum_payload.encode("utf-8")).hexdigest()

    # --- build final record ---
    result = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": 2,
    }
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a JSON wire-format record string.

    - Absent version is treated as version 1.
    - Version 2 records are checksum-validated.
    - Unknown top-level fields raise CodecError.

    Returns a new dict with keys: id, value, version.
    Raises CodecError on any problem.
    """
    # --- parse JSON ---
    if not isinstance(text, (str, bytes)):
        raise CodecError("input must be a string or bytes")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise CodecError("JSON value must be an object")

    # --- determine version ---
    if "version" not in data:
        version = 1
    else:
        version = data["version"]
        if isinstance(version, bool) or not isinstance(version, int):
            raise CodecError("'version' must be an integer")

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # --- check for unknown top-level fields ---
    if version == 1:
        known_fields = {"id", "value", "version"}
    else:  # version == 2
        known_fields = {"id", "value", "version", "checksum"}

    for key in data:
        if key not in known_fields:
            raise CodecError(f"unknown top-level field: {key!r}")

    # --- validate required fields ---
    if "id" not in data:
        raise CodecError("missing required field 'id'")
    if "value" not in data:
        raise CodecError("missing required field 'value'")

    id_val = data["id"]
    value_val = data["value"]

    if not isinstance(id_val, str) or len(id_val) == 0:
        raise CodecError("'id' must be a non-empty string")

    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("'value' must be an integer (not a boolean)")

    # --- version 2 checksum validation ---
    if version == 2:
        if "checksum" not in data:
            raise CodecError("version 2 record is missing 'checksum'")

        received_checksum = data["checksum"]
        if not isinstance(received_checksum, str):
            raise CodecError("'checksum' must be a string")

        checksum_payload = json.dumps(
            {"id": id_val, "value": value_val, "version": 2},
            sort_keys=True,
            separators=(",", ":"),
        )
        expected_checksum = hashlib.sha256(
            checksum_payload.encode("utf-8")
        ).hexdigest()

        if received_checksum != expected_checksum:
            raise CodecError("checksum mismatch")

    # --- return new dict ---
    return {"id": id_val, "value": value_val, "version": version}
