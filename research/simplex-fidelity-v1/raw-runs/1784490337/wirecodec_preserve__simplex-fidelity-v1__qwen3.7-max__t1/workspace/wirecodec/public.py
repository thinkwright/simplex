"""wirecodec.public – deterministic versioned JSON wire codec."""

import json
import hashlib


class CodecError(Exception):
    """Raised when a wire-format record cannot be decoded."""


def _compute_checksum(id_val, value, version):
    """SHA-256 hex digest over compact sorted JSON of {id, value, version}."""
    payload = {"id": id_val, "value": value, "version": version}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode *record* into a compact version-2 JSON wire string.

    *record* must contain a non-empty string ``id`` and an integer
    (non-boolean) ``value``.  Returns a ``str`` of compact JSON with
    sorted keys containing *version*, *id*, *value*, and *checksum*.

    Raises ``ValueError`` on invalid input.  Never mutates *record*.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # --- validate id ---------------------------------------------------
    if "id" not in record:
        raise ValueError("record is missing required field 'id'")
    id_val = record["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("'id' must be a non-empty string")

    # --- validate value ------------------------------------------------
    if "value" not in record:
        raise ValueError("record is missing required field 'value'")
    value = record["value"]
    # bool is a subclass of int in Python – reject booleans explicitly
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'value' must be an integer (non-boolean)")

    # --- build wire record ---------------------------------------------
    version = 2
    checksum = _compute_checksum(id_val, value, version)
    wire = {
        "checksum": checksum,
        "id": id_val,
        "value": value,
        "version": version,
    }
    return json.dumps(wire, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a JSON wire string into a plain ``dict``.

    * Absent ``version`` is treated as version 1.
    * Version 2 records are checksum-validated.
    * Unknown top-level fields are collected under ``extras`` (omitted
      when empty).

    Raises ``CodecError`` on any problem.
    """
    # --- parse JSON ----------------------------------------------------
    if not isinstance(text, (str, bytes)):
        raise CodecError("input must be a string")
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise CodecError("top-level JSON value must be an object")

    # --- version -------------------------------------------------------
    version = obj.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("'version' must be an integer")
    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # --- required fields -----------------------------------------------
    if "id" not in obj:
        raise CodecError("missing required field 'id'")
    id_val = obj["id"]
    if not isinstance(id_val, str):
        raise CodecError("'id' must be a string")

    if "value" not in obj:
        raise CodecError("missing required field 'value'")
    value = obj["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodecError("'value' must be an integer (non-boolean)")

    # --- checksum validation (version 2 only) --------------------------
    if version == 2:
        if "checksum" not in obj:
            raise CodecError("version 2 record missing checksum")
        expected = _compute_checksum(id_val, value, version)
        if obj["checksum"] != expected:
            raise CodecError("checksum mismatch")

    # --- collect extras ------------------------------------------------
    known_keys = {"id", "value", "version"}
    if version == 2:
        known_keys.add("checksum")

    extras = {k: v for k, v in obj.items() if k not in known_keys}

    result = {"id": id_val, "value": value, "version": version}
    if extras:
        result["extras"] = extras

    return result
