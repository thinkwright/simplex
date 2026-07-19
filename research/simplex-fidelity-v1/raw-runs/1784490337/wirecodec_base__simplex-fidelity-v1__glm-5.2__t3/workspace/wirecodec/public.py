"""Wire codec public API.

A compact, deterministic JSON wire format with SHA-256 integrity checksums.

Only the Python standard library is used: ``json`` for serialization and
``hashlib`` for SHA-256 digests. No third-party dependencies are required.
"""

import hashlib
import json

__all__ = ["encode", "decode", "CodecError"]

_CURRENT_VERSION = 2
_SUPPORTED_VERSIONS = (1, 2)


class CodecError(Exception):
    """Raised when a wire input cannot be decoded."""


def _is_valid_id(id_value):
    return isinstance(id_value, str) and id_value != ""


def _is_valid_value(value):
    # bool is a subclass of int in Python; reject it explicitly.
    return not isinstance(value, bool) and isinstance(value, int)


def _canonical_payload(id_value, value, version):
    """Compact, sorted-key JSON over only id, value, and version."""
    return json.dumps(
        {"id": id_value, "value": value, "version": version},
        sort_keys=True,
        separators=(",", ":"),
    )


def _checksum(id_value, value, version):
    """Lowercase SHA-256 hex digest over the canonical known-field payload."""
    payload = _canonical_payload(id_value, value, version)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a compact, deterministic version 2 wire string.

    ``record`` must provide a non-empty string ``id`` and an integer
    (non-boolean) ``value``. The input is never mutated. Invalid input raises
    ``ValueError``.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    id_value = record.get("id")
    value = record.get("value")

    if not _is_valid_id(id_value):
        raise ValueError("id must be a non-empty string")
    if not _is_valid_value(value):
        raise ValueError("value must be an integer and not a boolean")

    digest = _checksum(id_value, value, _CURRENT_VERSION)
    return json.dumps(
        {
            "checksum": digest,
            "id": id_value,
            "value": value,
            "version": _CURRENT_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def decode(text):
    """Decode a wire string into a new dict with id, value, and version.

    Absent ``version`` is treated as version 1. Version 2 records are
    checksum-validated before returning. Unknown top-level fields are
    discarded after the known fields are validated. Malformed JSON,
    unsupported versions, invalid fields, or checksum mismatches raise
    ``CodecError``.
    """
    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError("malformed JSON wire input") from exc

    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")

    version = obj.get("version", 1)
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version not in _SUPPORTED_VERSIONS
    ):
        raise CodecError("unsupported version: %r" % (version,))

    id_value = obj.get("id")
    value = obj.get("value")

    if not _is_valid_id(id_value):
        raise CodecError("invalid field: id")
    if not _is_valid_value(value):
        raise CodecError("invalid field: value")

    if version == 2:
        checksum = obj.get("checksum")
        if not isinstance(checksum, str):
            raise CodecError("invalid field: checksum")
        expected = _checksum(id_value, value, version)
        if checksum != expected:
            raise CodecError("checksum mismatch")

    return {"id": id_value, "value": value, "version": version}