"""Core encode/decode implementation for wirecodec.

Uses only the Python standard library. SHA-256 is provided by ``hashlib``.
"""

import hashlib
import json


class CodecError(Exception):
    """Raised for malformed, unsupported, or checksum-invalid wire input."""


_VERSION = 2


def _validate_record(record):
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if "id" not in record or "value" not in record:
        raise ValueError("record must contain 'id' and 'value'")
    id_value = record["id"]
    if not isinstance(id_value, str) or id_value == "":
        raise ValueError("'id' must be a non-empty string")
    value = record["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'value' must be an integer (non-boolean)")


def _canonical_payload(id_value, value, version):
    payload = {"id": id_value, "value": value, "version": version}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _checksum(id_value, value, version):
    canonical = _canonical_payload(id_value, value, version)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into a deterministic version 2 JSON string.

    The input record is not mutated. Raises ``ValueError`` for invalid input.
    """
    _validate_record(record)
    id_value = record["id"]
    value = record["value"]
    checksum = _checksum(id_value, value, _VERSION)
    out = {
        "version": _VERSION,
        "id": id_value,
        "value": value,
        "checksum": checksum,
    }
    return json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_object(text):
    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError("malformed JSON: {}".format(exc)) from exc
    if not isinstance(obj, dict):
        raise CodecError("wire input must be a JSON object")
    return obj


def _coerce_version(obj):
    if "version" not in obj:
        return 1
    version = obj["version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise CodecError("invalid 'version' field")
    return version


def _extract_known(obj):
    known = {"id", "value", "version", "checksum"}
    extras = {k: v for k, v in obj.items() if k not in known}
    return extras


def decode(text):
    """Decode a JSON record string.

    Absent ``version`` is treated as version 1. Version 2 records are
    checksum-validated. Returns a new dict with ``id``, ``value``, ``version``,
    and ``extras`` (when non-empty). Raises ``CodecError`` for malformed JSON,
    unsupported versions, invalid fields, or checksum mismatch.
    """
    obj = _parse_object(text)
    version = _coerce_version(obj)

    if version == 1:
        if "id" not in obj or "value" not in obj:
            raise CodecError("version 1 record missing 'id' or 'value'")
        id_value = obj["id"]
        value = obj["value"]
        if not isinstance(id_value, str) or id_value == "":
            raise CodecError("invalid 'id' in version 1 record")
        if isinstance(value, bool) or not isinstance(value, int):
            raise CodecError("invalid 'value' in version 1 record")
        extras = _extract_known(obj)
        result = {"id": id_value, "value": value, "version": 1}
        if extras:
            result["extras"] = extras
        return result

    if version == 2:
        if "id" not in obj or "value" not in obj or "checksum" not in obj:
            raise CodecError("version 2 record missing required fields")
        id_value = obj["id"]
        value = obj["value"]
        checksum = obj["checksum"]
        if not isinstance(id_value, str) or id_value == "":
            raise CodecError("invalid 'id' in version 2 record")
        if isinstance(value, bool) or not isinstance(value, int):
            raise CodecError("invalid 'value' in version 2 record")
        if not isinstance(checksum, str):
            raise CodecError("invalid 'checksum' in version 2 record")
        expected = _checksum(id_value, value, 2)
        if checksum.lower() != expected:
            raise CodecError("checksum mismatch")
        extras = _extract_known(obj)
        result = {"id": id_value, "value": value, "version": 2}
        if extras:
            result["extras"] = extras
        return result

    raise CodecError("unsupported version: {}".format(version))