"""Implementation of the wirecodec encode/decode functions.

The codec produces deterministic, compact JSON records. Version 2 records
include a SHA-256 checksum over the canonical payload (id, value, version).
Version 1 records (the baseline) carry no checksum and are accepted on
decode for backward compatibility.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, Tuple

CURRENT_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
CHECKSUM_FIELDS = ("id", "value", "version")


class CodecError(Exception):
    """Raised for malformed, unsupported, or checksum-invalid wire input."""


def _canonical_payload(record: Dict[str, Any]) -> str:
    """Return compact JSON with sorted keys for the checksum-bearing fields."""
    payload = {field: record[field] for field in CHECKSUM_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_checksum(record: Dict[str, Any]) -> str:
    """Compute the lowercase SHA-256 hex digest over the canonical payload."""
    canonical = _canonical_payload(record)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_encode_record(record: Any) -> Tuple[str, int]:
    """Validate the user-supplied record and return (id, value).

    Raises ``ValueError`` for any invalid input. The original ``record`` is
    never mutated; we work on a shallow copy of the relevant fields.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Copy to avoid mutating the caller's dict while inspecting it.
    snapshot = dict(record)

    if "id" not in snapshot:
        raise ValueError("record must contain a non-empty string 'id'")
    raw_id = snapshot["id"]
    if not isinstance(raw_id, str):
        raise ValueError("record 'id' must be a string")
    if raw_id == "":
        raise ValueError("record 'id' must be a non-empty string")

    if "value" not in snapshot:
        raise ValueError("record must contain an integer 'value'")
    raw_value = snapshot["value"]
    # bool is a subclass of int in Python; explicitly reject booleans.
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ValueError("record 'value' must be an integer (not a boolean)")

    return raw_id, raw_value


def encode(record: Any) -> str:
    """Encode a record as a compact version 2 JSON string with a checksum.

    The input must be a dict containing a non-empty string ``id`` and an
    integer (non-boolean) ``value``. The original ``record`` is not mutated.
    Raises ``ValueError`` for invalid input.
    """
    record_id, record_value = _validate_encode_record(record)

    # Build the output record on a fresh dict so the caller's input is
    # never modified, even if it contained extra keys.
    output: Dict[str, Any] = {
        "version": CURRENT_VERSION,
        "id": record_id,
        "value": record_value,
    }
    output["checksum"] = _compute_checksum(output)

    return json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _coerce_version(raw_version: Any) -> int:
    """Validate and coerce a version field to an int.

    Booleans are rejected because ``bool`` is a subclass of ``int`` in
    Python and would otherwise be accepted as a version number.
    """
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise CodecError("version must be an integer")
    return raw_version


def _validate_id(raw_id: Any) -> str:
    if not isinstance(raw_id, str):
        raise CodecError("id must be a string")
    if raw_id == "":
        raise CodecError("id must be a non-empty string")
    return raw_id


def _validate_value(raw_value: Any) -> int:
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise CodecError("value must be an integer (not a boolean)")
    return raw_value


def _parse_json_object(text: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CodecError("wire input must be a JSON object")
    return parsed


def _decode_version1(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a version 1 record (no checksum)."""
    record_id = _validate_id(parsed.get("id"))
    record_value = _validate_value(parsed.get("value"))

    known = {"id", "value", "version"}
    extras = {k: v for k, v in parsed.items() if k not in known}

    result: Dict[str, Any] = {
        "id": record_id,
        "value": record_value,
        "version": 1,
    }
    if extras:
        result["extras"] = extras
    return result


def _decode_version2(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a version 2 record, validating its checksum first."""
    record_id = _validate_id(parsed.get("id"))
    record_value = _validate_value(parsed.get("value"))

    checksum = parsed.get("checksum")
    if not isinstance(checksum, str):
        raise CodecError("version 2 record must contain a string 'checksum'")

    # Recompute the checksum over the canonical payload and compare.
    canonical_record = {
        "id": record_id,
        "value": record_value,
        "version": CURRENT_VERSION,
    }
    expected = _compute_checksum(canonical_record)
    if checksum != expected:
        raise CodecError("checksum mismatch")

    known = {"id", "value", "version", "checksum"}
    extras = {k: v for k, v in parsed.items() if k not in known}

    result: Dict[str, Any] = {
        "id": record_id,
        "value": record_value,
        "version": 2,
    }
    if extras:
        result["extras"] = extras
    return result


def decode(text: str) -> Dict[str, Any]:
    """Decode a wirecodec JSON record.

    Accepts a JSON object string. An absent ``version`` field is treated as
    version 1. Version 2 records are validated against their SHA-256 checksum
    before being returned. Raises ``CodecError`` for malformed JSON,
    unsupported versions, invalid fields, or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("wire input must be a string")

    parsed = _parse_json_object(text)

    if "version" not in parsed:
        return _decode_version1(parsed)

    version = _coerce_version(parsed["version"])
    if version not in SUPPORTED_VERSIONS:
        raise CodecError(f"unsupported version: {version}")
    if version == 1:
        return _decode_version1(parsed)
    return _decode_version2(parsed)