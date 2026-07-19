"""wirecodec.public – encode / decode / CodecError"""

import json
import hashlib
import copy


class CodecError(Exception):
    """Raised when a wire-format record is malformed or fails validation."""


def _compute_checksum(id_val: str, value_val: int, version: int) -> str:
    """SHA-256 hex digest over compact sorted JSON of {id, value, version}."""
    payload = json.dumps(
        {"id": id_val, "value": value_val, "version": version},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_id(id_val) -> None:
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("id must be a non-empty string")


def _validate_value(value_val) -> None:
    # int but not bool (bool is subclass of int in Python)
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise ValueError("value must be an integer (non-boolean)")


def encode(record: dict) -> str:
    """Encode *record* as a compact version-2 JSON wire string.

    *record* must contain:
      - ``id``    – a non-empty string
      - ``value`` – an integer (not a bool)

    The input dict is **not** mutated.
    Raises ``ValueError`` on invalid input.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # --- validate required keys ---
    if "id" not in record:
        raise ValueError("record must contain 'id'")
    if "value" not in record:
        raise ValueError("record must contain 'value'")

    _validate_id(record["id"])
    _validate_value(record["value"])

    # Copy values out — never mutate the input
    id_val = record["id"]
    value_val = record["value"]
    version = 2

    checksum = _compute_checksum(id_val, value_val, version)

    out = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": version,
    }
    return json.dumps(out, sort_keys=True, separators=(",", ":"))


# Fields allowed at the top level for each supported version.
_V1_KNOWN = {"id", "value", "version"}
_V2_KNOWN = {"id", "value", "version", "checksum"}


def decode(text: str) -> dict:
    """Decode a JSON wire string and return ``{id, value, version}``.

    * Absent ``version`` is treated as version 1.
    * Version 2 records are checksum-validated.
    * Unknown top-level fields raise ``CodecError``.

    Raises ``CodecError`` on any problem.
    """
    if not isinstance(text, (str, bytes)):
        raise CodecError("input must be a string")

    # --- parse JSON ---
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise CodecError("top-level JSON value must be an object")

    # --- determine version ---
    version = obj.get("version", 1)

    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("version must be an integer")

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # --- check for unknown fields ---
    known = _V1_KNOWN if version == 1 else _V2_KNOWN
    unknown = set(obj.keys()) - known
    if unknown:
        raise CodecError(f"unknown top-level field(s): {sorted(unknown)}")

    # --- validate id ---
    if "id" not in obj:
        raise CodecError("missing 'id' field")
    id_val = obj["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise CodecError("id must be a non-empty string")

    # --- validate value ---
    if "value" not in obj:
        raise CodecError("missing 'value' field")
    value_val = obj["value"]
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("value must be an integer (non-boolean)")

    # --- version-2 checksum validation ---
    if version == 2:
        if "checksum" not in obj:
            raise CodecError("version 2 record missing 'checksum'")
        expected = _compute_checksum(id_val, value_val, version)
        if obj["checksum"] != expected:
            raise CodecError("checksum mismatch")

    return {"id": id_val, "value": value_val, "version": version}
