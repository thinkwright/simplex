"""Public API for the wirecodec package.

Exposes :func:`encode`, :func:`decode`, and :class:`CodecError`.
"""

import hashlib
import json

__all__ = ["encode", "decode", "CodecError"]

_CURRENT_VERSION = 2
_SUPPORTED_VERSIONS = (1, 2)


class CodecError(Exception):
    """Raised when wire-format input is malformed, unsupported, or invalid."""


def _is_nonempty_str(value):
    return isinstance(value, str) and value != ""


def _is_int_not_bool(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_payload(record_id, value, version):
    """Compact, sorted-key JSON text over exactly id, value, and version."""
    payload = {"id": record_id, "value": value, "version": version}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a deterministic version 2 wire-format string.

    ``record`` must be a mapping containing exactly a non-empty string ``id``
    and an integer, non-boolean ``value``. The input is never mutated.

    Raises :class:`ValueError` for invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value'")

    record_id = record["id"]
    value = record["value"]

    if not _is_nonempty_str(record_id):
        raise ValueError("id must be a non-empty string")
    if not _is_int_not_bool(value):
        raise ValueError("value must be an integer and not a boolean")

    payload_text = _canonical_payload(record_id, value, _CURRENT_VERSION)
    checksum = _sha256_hex(payload_text)

    envelope = {
        "checksum": checksum,
        "id": record_id,
        "value": value,
        "version": _CURRENT_VERSION,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a wire-format JSON object string into a record dict.

    Absent ``version`` is treated as version 1. Version 2 records are only
    accepted when their checksum is valid. Unknown top-level fields are
    preserved under an ``extras`` key (omitted when empty).

    Raises :class:`CodecError` for malformed JSON, unsupported versions,
    invalid fields, or checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("decode input must be a string")

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CodecError("malformed JSON: %s" % exc) from exc

    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")

    if "version" in obj:
        version = obj["version"]
        if isinstance(version, bool):
            raise CodecError("unsupported version: %r" % (version,))
        if version == 1:
            version = 1
        elif version == 2:
            version = 2
        else:
            raise CodecError("unsupported version: %r" % (version,))
    else:
        version = 1

    if "id" not in obj:
        raise CodecError("missing field: id")
    if "value" not in obj:
        raise CodecError("missing field: value")

    record_id = obj["id"]
    value = obj["value"]

    if not _is_nonempty_str(record_id):
        raise CodecError("invalid field: id")
    if not _is_int_not_bool(value):
        raise CodecError("invalid field: value")

    if version == 2:
        checksum = obj.get("checksum")
        expected = _sha256_hex(_canonical_payload(record_id, value, version))
        if not isinstance(checksum, str) or checksum != expected:
            raise CodecError("checksum mismatch")

    result = {"id": record_id, "value": value, "version": version}

    known_fields = {"id", "value", "version"}
    if version == 2:
        known_fields = known_fields | {"checksum"}

    extras = {
        key: val for key, val in obj.items() if key not in known_fields
    }
    if extras:
        result["extras"] = extras

    return result