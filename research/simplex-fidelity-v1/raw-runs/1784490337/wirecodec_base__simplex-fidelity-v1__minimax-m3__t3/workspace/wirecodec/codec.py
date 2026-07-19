"""Core implementation of the wirecodec encode/decode functions.

Only the Python standard library is used; SHA-256 comes from :mod:`hashlib`.
"""

import copy
import hashlib
import json


CURRENT_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
KNOWN_FIELDS = ("id", "value", "version")


class CodecError(Exception):
    """Raised when decoding fails for any reason (malformed, unsupported, etc.)."""


def _validate_record(record):
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if "id" not in record:
        raise ValueError("record must contain a non-empty string 'id'")
    if "value" not in record:
        raise ValueError("record must contain a 'value'")
    id_value = record["id"]
    if not isinstance(id_value, str) or len(id_value) == 0:
        raise ValueError("'id' must be a non-empty string")
    value = record["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'value' must be an integer (non-boolean)")


def _canonical_payload(id_value, value, version):
    payload = {"id": id_value, "value": value, "version": version}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _checksum(id_value, value, version):
    canonical = _canonical_payload(id_value, value, version)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a compact version 2 JSON string with checksum.

    The input record must contain a non-empty string ``id`` and an integer
    (non-boolean) ``value``. The input is not mutated. Raises ``ValueError``
    for invalid input.
    """
    _validate_record(record)
    snapshot = {"id": record["id"], "value": record["value"]}
    checksum = _checksum(snapshot["id"], snapshot["value"], CURRENT_VERSION)
    out = {
        "version": CURRENT_VERSION,
        "id": snapshot["id"],
        "value": snapshot["value"],
        "checksum": checksum,
    }
    return json.dumps(out, sort_keys=True, separators=(",", ":"))


def _parse_object(text):
    try:
        obj = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise CodecError("malformed JSON: {}".format(exc)) from exc
    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")
    return obj


def _coerce_version(obj):
    if "version" not in obj:
        return 1
    version = obj["version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise CodecError("'version' must be an integer")
    return version


def _validate_known_fields(obj, version):
    if "id" not in obj:
        raise CodecError("missing required field 'id'")
    if "value" not in obj:
        raise CodecError("missing required field 'value'")
    id_value = obj["id"]
    if not isinstance(id_value, str) or len(id_value) == 0:
        raise CodecError("'id' must be a non-empty string")
    value = obj["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodecError("'value' must be an integer (non-boolean)")
    if version == 2 and "checksum" not in obj:
        raise CodecError("version 2 record missing 'checksum'")


def decode(text):
    """Decode a wire-format JSON string into a dict.

    Returns a new dict containing ``id``, ``value``, and ``version``. Absent
    version is treated as version 1. Version 2 records are validated against
    their checksum. Raises :class:`CodecError` for malformed JSON, unsupported
    versions, invalid fields, or checksum mismatch.
    """
    obj = _parse_object(text)
    version = _coerce_version(obj)
    if version not in SUPPORTED_VERSIONS:
        raise CodecError("unsupported version: {}".format(version))
    _validate_known_fields(obj, version)

    id_value = obj["id"]
    value = obj["value"]

    if version == 2:
        checksum = obj["checksum"]
        if not isinstance(checksum, str):
            raise CodecError("'checksum' must be a string")
        expected = _checksum(id_value, value, version)
        if checksum != expected:
            raise CodecError("checksum mismatch")

    return {"id": copy.deepcopy(id_value), "value": copy.deepcopy(value), "version": version}