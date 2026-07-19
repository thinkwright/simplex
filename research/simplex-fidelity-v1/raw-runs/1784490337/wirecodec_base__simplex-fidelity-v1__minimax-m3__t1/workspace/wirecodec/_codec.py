"""Implementation of the wirecodec encode/decode functions.

Uses only the Python standard library. Checksums are SHA-256 (hashlib).
"""

import hashlib
import json


CURRENT_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)


class CodecError(Exception):
    """Raised for malformed, unsupported, or checksum-invalid wire input."""


def _canonical_payload(record):
    """Return the compact JSON bytes of the canonical known-field payload.

    The canonical payload for checksum purposes contains only id, value,
    and version, with keys sorted and no extra whitespace.
    """
    canonical = {
        "id": record["id"],
        "value": record["value"],
        "version": record["version"],
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def _checksum(record):
    """Compute the lowercase SHA-256 hex digest over the canonical payload."""
    payload = _canonical_payload(record).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def encode(record):
    """Encode a record into a compact version 2 JSON string with a checksum.

    The record must be a dict-like mapping containing a non-empty string
    ``id`` and an integer ``value`` that is not a boolean. The input is
    not mutated.

    Returns a compact JSON string with sorted keys containing ``version``,
    ``id``, ``value``, and ``checksum``.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Snapshot the fields we care about so we can validate without mutating.
    id_value = record.get("id")
    value = record.get("value")

    if not isinstance(id_value, str) or id_value == "":
        raise ValueError("id must be a non-empty string")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer (not a boolean)")

    payload = {
        "version": CURRENT_VERSION,
        "id": id_value,
        "value": value,
    }
    payload["checksum"] = _checksum(payload)

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a wirecodec JSON string into a new dict.

    Accepts a JSON object string. If ``version`` is absent it is treated as
    version 1. For version 2 the checksum is validated before returning.

    Returns a new dict containing ``id``, ``value``, and ``version``.
    Unknown top-level fields are discarded after validation.

    Raises ``CodecError`` for malformed JSON, unsupported versions, invalid
    fields, or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("wire input must be a string")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CodecError(f"malformed JSON: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise CodecError("wire input must be a JSON object")

    version = data.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("version must be an integer")
    if version not in SUPPORTED_VERSIONS:
        raise CodecError(f"unsupported version: {version}")

    id_value = data.get("id")
    value = data.get("value")

    if not isinstance(id_value, str) or id_value == "":
        raise CodecError("id must be a non-empty string")
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodecError("value must be an integer (not a boolean)")

    if version == 2:
        checksum = data.get("checksum")
        if not isinstance(checksum, str):
            raise CodecError("checksum must be a string")
        expected = _checksum(
            {"version": version, "id": id_value, "value": value}
        )
        if checksum != expected:
            raise CodecError("checksum mismatch")

    return {"id": id_value, "value": value, "version": version}