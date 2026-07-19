"""Core encode/decode logic for wirecodec.

Version 1 records: {"id": str, "value": int} — no checksum.
Version 2 records: {"version": 2, "id": str, "value": int, "checksum": str}
    where checksum is lowercase SHA-256 hex over the compact sorted JSON
    of {"id", "value", "version"} only.
"""

import hashlib
import json


CURRENT_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
KNOWN_FIELDS_V1_BASE = ("id", "value")
KNOWN_FIELDS_V2 = ("id", "value", "version", "checksum")


class CodecError(Exception):
    """Raised for malformed, unsupported, or checksum-invalid wire input."""


def _canonical_payload(record):
    """Return the compact sorted-JSON bytes used as checksum input.

    Only the known fields id, value, and version are included.
    """
    payload = {
        "id": record["id"],
        "value": record["value"],
        "version": record["version"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum(record):
    """Compute the lowercase SHA-256 hex digest for a record."""
    return hashlib.sha256(_canonical_payload(record).encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a compact version 2 JSON string.

    Requires exactly a non-empty string id and an integer non-boolean value.
    Does not mutate record. Raises ValueError for invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Validate id: non-empty string.
    if "id" not in record:
        raise ValueError("record must contain an 'id' field")
    id_value = record["id"]
    if not isinstance(id_value, str):
        raise ValueError("'id' must be a string")
    if id_value == "":
        raise ValueError("'id' must be a non-empty string")

    # Validate value: integer, not boolean.
    if "value" not in record:
        raise ValueError("record must contain a 'value' field")
    value = record["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'value' must be an integer (not a boolean)")

    # No extra fields allowed in encode input.
    extra = set(record.keys()) - set(KNOWN_FIELDS_V1_BASE)
    if extra:
        raise ValueError(
            "record contains unsupported fields: {}".format(sorted(extra))
        )

    versioned = {
        "version": CURRENT_VERSION,
        "id": id_value,
        "value": value,
    }
    versioned["checksum"] = _checksum(versioned)

    return json.dumps(versioned, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a JSON wire record string into a dict.

    Absent version is treated as version 1. Returns a new dict with id,
    value, and version. Raises CodecError for malformed JSON, unsupported
    versions, invalid fields, unknown top-level fields, or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("wire input must be a string")

    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError("malformed JSON: {}".format(exc)) from exc

    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")

    # Determine version (absent => 1).
    version_present = "version" in obj
    if version_present:
        version = obj["version"]
        if isinstance(version, bool) or not isinstance(version, int):
            raise CodecError("'version' must be an integer")
        if version not in SUPPORTED_VERSIONS:
            raise CodecError("unsupported version: {}".format(version))
    else:
        version = 1

    # Validate id.
    if "id" not in obj:
        raise CodecError("missing required field 'id'")
    id_value = obj["id"]
    if not isinstance(id_value, str):
        raise CodecError("'id' must be a string")
    if id_value == "":
        raise CodecError("'id' must be a non-empty string")

    # Validate value.
    if "value" not in obj:
        raise CodecError("missing required field 'value'")
    value = obj["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodecError("'value' must be an integer (not a boolean)")

    # Reject unknown top-level fields.
    if version == 2:
        known = set(KNOWN_FIELDS_V2)
    else:
        known = set(KNOWN_FIELDS_V1_BASE)
        if version_present:
            known.add("version")
    unknown = set(obj.keys()) - known
    if unknown:
        raise CodecError(
            "unknown fields in version {} record: {}".format(
                version, sorted(unknown)
            )
        )

    if version == 2:
        checksum = obj.get("checksum")
        if not isinstance(checksum, str):
            raise CodecError("'checksum' must be a string")
        expected = _checksum(
            {"id": id_value, "value": value, "version": version}
        )
        if checksum != expected:
            raise CodecError("checksum mismatch")

    return {"id": id_value, "value": value, "version": version}