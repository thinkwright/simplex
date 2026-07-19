"""Core encode/decode logic for wirecodec.

Uses only the Python standard library and SHA-256 from hashlib.
"""

import copy
import hashlib
import json


class CodecError(Exception):
    """Raised when decoding fails for any reason (malformed, unsupported,
    invalid fields, or checksum mismatch).
    """
    pass


# Fields that are part of the canonical payload (used for the checksum).
_CANONICAL_FIELDS = ("id", "value", "version")
# Fields that are part of the encoded record (excluding the checksum itself).
_RECORD_FIELDS = ("version", "id", "value", "checksum")


def _canonical_payload(record):
    """Return a compact JSON string of only id, value, and version with
    sorted keys, suitable for checksum computation.
    """
    payload = {
        "id": record["id"],
        "value": record["value"],
        "version": record["version"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _compute_checksum(record):
    """Compute the lowercase SHA-256 hex digest over the canonical payload."""
    canonical = _canonical_payload(record)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a compact version 2 JSON string with checksum.

    Requirements:
        - record must be a dict-like object
        - record must contain a non-empty string 'id'
        - record must contain an integer 'value' that is not a boolean
        - record is not mutated

    Returns a compact JSON string with sorted keys containing:
        version=2, id, value, checksum (lowercase SHA-256 hex over the
        canonical payload of id, value, and version).

    Raises ValueError for invalid input.
    """
    if record is None or not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Work on a shallow copy so we don't mutate the input.
    record_copy = dict(record)

    # Validate id: must be present, a non-empty string.
    if "id" not in record_copy:
        raise ValueError("record must contain 'id'")
    id_val = record_copy["id"]
    if not isinstance(id_val, str):
        raise ValueError("'id' must be a string")
    if id_val == "":
        raise ValueError("'id' must be non-empty")

    # Validate value: must be present, an integer, and not a boolean.
    if "value" not in record_copy:
        raise ValueError("record must contain 'value'")
    value_val = record_copy["value"]
    # bool is a subclass of int in Python, so exclude it explicitly.
    if isinstance(value_val, bool):
        raise ValueError("'value' must not be a boolean")
    if not isinstance(value_val, int):
        raise ValueError("'value' must be an integer")

    # Build the canonical record (version 2) and compute the checksum.
    canonical_record = {
        "id": id_val,
        "value": value_val,
        "version": 2,
    }
    checksum = _compute_checksum(canonical_record)

    encoded = {
        "version": 2,
        "id": id_val,
        "value": value_val,
        "checksum": checksum,
    }
    return json.dumps(encoded, sort_keys=True, separators=(",", ":"))


def _validate_known_fields(obj, version):
    """Ensure the decoded object contains only known top-level fields.

    For version 1: only 'id' and 'value' are allowed (and 'version' if present).
    For version 2: only 'version', 'id', 'value', and 'checksum' are allowed.
    """
    if version == 1:
        allowed = {"id", "value", "version"}
    elif version == 2:
        allowed = {"version", "id", "value", "checksum"}
    else:
        # Should not be reachable; callers guard the version.
        allowed = set()

    unknown = set(obj.keys()) - allowed
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise CodecError(
            "unknown field(s) in record: {0}".format(unknown_list)
        )


def decode(text):
    """Decode a JSON record string.

    Accepts:
        - version 1 records (version field absent or equal to 1) with no
          checksum; returns a new dict with id, value, and version=1.
        - version 2 records with a valid SHA-256 checksum; returns a new
          dict with id, value, and version=2.

    Raises CodecError for malformed JSON, unsupported versions, invalid
    fields, unknown top-level fields, or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("input must be a string")

    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError("malformed JSON: {0}".format(exc)) from exc

    if not isinstance(obj, dict):
        raise CodecError("decoded JSON must be an object")

    # Determine the version. Absent version is treated as version 1.
    if "version" not in obj:
        version = 1
    else:
        version_field = obj["version"]
        if isinstance(version_field, bool) or not isinstance(version_field, int):
            raise CodecError("'version' must be an integer")
        version = version_field

    if version not in (1, 2):
        raise CodecError("unsupported version: {0}".format(version))

    # Validate known fields for this version.
    _validate_known_fields(obj, version)

    # Validate id.
    if "id" not in obj:
        raise CodecError("record missing 'id'")
    id_val = obj["id"]
    if not isinstance(id_val, str):
        raise CodecError("'id' must be a string")
    if id_val == "":
        raise CodecError("'id' must be non-empty")

    # Validate value.
    if "value" not in obj:
        raise CodecError("record missing 'value'")
    value_val = obj["value"]
    if isinstance(value_val, bool):
        raise CodecError("'value' must not be a boolean")
    if not isinstance(value_val, int):
        raise CodecError("'value' must be an integer")

    if version == 2:
        # Validate checksum presence and type.
        if "checksum" not in obj:
            raise CodecError("version 2 record missing 'checksum'")
        checksum = obj["checksum"]
        if not isinstance(checksum, str):
            raise CodecError("'checksum' must be a string")

        # Recompute the expected checksum over the canonical payload.
        canonical_record = {
            "id": id_val,
            "value": value_val,
            "version": 2,
        }
        expected = _compute_checksum(canonical_record)
        if checksum != expected:
            raise CodecError("checksum mismatch")

    # Return a new dict (do not alias the parsed object).
    return {
        "id": id_val,
        "value": value_val,
        "version": version,
    }