"""Internal codec implementation for wirecodec.

Uses only the Python standard library. SHA-256 from hashlib is used for
version 2 record checksums.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict


class CodecError(Exception):
    """Raised when decoding fails for any reason (malformed JSON,
    unsupported version, invalid fields, or checksum mismatch)."""


_CURRENT_VERSION = 2
_SUPPORTED_VERSIONS = (1, 2)
_KNOWN_FIELDS = ("id", "value", "version")


def _validate_record(record: Any) -> None:
    """Validate that record is a dict with a non-empty string id and an
    integer non-boolean value. Raises ValueError on invalid input."""
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if "id" not in record:
        raise ValueError("record must contain an 'id' field")
    rid = record["id"]
    if not isinstance(rid, str) or rid == "":
        raise ValueError("record 'id' must be a non-empty string")
    if "value" not in record:
        raise ValueError("record must contain a 'value' field")
    val = record["value"]
    # bool is a subclass of int; reject booleans explicitly.
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError("record 'value' must be an integer (non-boolean)")


def _canonical_payload(record: Dict[str, Any]) -> str:
    """Return compact JSON with sorted keys for the known fields
    id, value, version."""
    payload = {
        "id": record["id"],
        "value": record["value"],
        "version": record["version"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _checksum(canonical: str) -> str:
    """Return the lowercase SHA-256 hex digest of the given string."""
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record: Dict[str, Any]) -> str:
    """Encode a record as a compact version 2 JSON string with a SHA-256
    checksum over the canonical known-field payload.

    The input record is not mutated. Raises ValueError for invalid input.
    """
    # Validate a deep copy so we never observe or return mutated input.
    validated = copy.deepcopy(record)
    _validate_record(validated)

    validated["version"] = _CURRENT_VERSION
    canonical = _canonical_payload(validated)
    digest = _checksum(canonical)

    out = {
        "id": validated["id"],
        "value": validated["value"],
        "version": validated["version"],
        "checksum": digest,
    }
    return json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        obj = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")
    return obj


def _coerce_version(obj: Dict[str, Any]) -> int:
    if "version" not in obj:
        return 1
    raw = obj["version"]
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise CodecError("invalid 'version' field")
    return raw


def _validate_known_fields(obj: Dict[str, Any]) -> None:
    if "id" not in obj:
        raise CodecError("missing 'id' field")
    rid = obj["id"]
    if not isinstance(rid, str) or rid == "":
        raise CodecError("invalid 'id' field")
    if "value" not in obj:
        raise CodecError("missing 'value' field")
    val = obj["value"]
    if isinstance(val, bool) or not isinstance(val, int):
        raise CodecError("invalid 'value' field")


def _split_extras(obj: Dict[str, Any]) -> Dict[str, Any]:
    extras = {k: v for k, v in obj.items() if k not in _KNOWN_FIELDS and k != "checksum"}
    return extras


def decode(text: str) -> Dict[str, Any]:
    """Decode a wirecodec JSON string into a record dict.

    Absent version is treated as version 1. Version 2 records are only
    returned when their checksum is valid. Unknown top-level fields are
    preserved in an 'extras' dict (omitted when empty).
    """
    if not isinstance(text, str):
        raise CodecError("wire input must be a string")

    obj = _parse_json(text)
    version = _coerce_version(obj)

    if version not in _SUPPORTED_VERSIONS:
        raise CodecError(f"unsupported version: {version}")

    _validate_known_fields(obj)

    extras = _split_extras(obj)

    if version == 2:
        if "checksum" not in obj:
            raise CodecError("missing checksum for version 2 record")
        provided = obj["checksum"]
        if not isinstance(provided, str):
            raise CodecError("invalid checksum field")
        canonical_obj = {
            "id": obj["id"],
            "value": obj["value"],
            "version": 2,
        }
        canonical = json.dumps(
            canonical_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        expected = _checksum(canonical)
        if provided != expected:
            raise CodecError("checksum mismatch")

    result: Dict[str, Any] = {
        "id": obj["id"],
        "value": obj["value"],
        "version": version,
    }
    if extras:
        result["extras"] = extras
    return result