"""Public API for the wirecodec package."""

import json
import hashlib


class CodecError(Exception):
    """Raised when a wire-format record cannot be decoded."""


def _validate_record_fields(record):
    """Validate that *record* has exactly the required id/value fields.

    Raises ValueError on any problem.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # Must contain exactly 'id' and 'value' (no extra, no missing).
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value' keys")

    id_val = record["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("id must be a non-empty string")

    value_val = record["value"]
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise ValueError("value must be an integer (not a boolean)")


def _compute_checksum(id_val, value_val, version):
    """Return the lowercase SHA-256 hex digest for the canonical payload."""
    payload = {"id": id_val, "value": value_val, "version": version}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode(record):
    """Encode *record* into a compact version-2 JSON wire string.

    Parameters
    ----------
    record : dict
        Must contain exactly ``id`` (non-empty str) and ``value`` (int, not bool).

    Returns
    -------
    str
        Compact JSON with sorted keys: ``{checksum, id, value, version}``.

    Raises
    ------
    ValueError
        If *record* is invalid.  The original *record* is never mutated.
    """
    _validate_record_fields(record)

    id_val = record["id"]
    value_val = record["value"]
    version = 2

    checksum = _compute_checksum(id_val, value_val, version)

    output = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": version,
    }
    return json.dumps(output, sort_keys=True, separators=(",", ":"))


def decode(text):
    """Decode a JSON wire string into a plain dict.

    Parameters
    ----------
    text : str
        A JSON object string produced by :func:`encode` or a legacy version-1
        record (no ``version`` key, no ``checksum``).

    Returns
    -------
    dict
        ``{id, value, version}`` – unknown top-level fields are discarded.

    Raises
    ------
    CodecError
        On malformed JSON, unsupported version, invalid fields, or checksum
        mismatch.
    """
    # --- parse JSON --------------------------------------------------------
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise CodecError("wire payload must be a JSON object")

    # --- determine version -------------------------------------------------
    version = obj.get("version", 1)

    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError("version must be an integer")

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # --- validate known fields ---------------------------------------------
    if "id" not in obj:
        raise CodecError("missing required field: id")
    id_val = obj["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise CodecError("id must be a non-empty string")

    if "value" not in obj:
        raise CodecError("missing required field: value")
    value_val = obj["value"]
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("value must be an integer (not a boolean)")

    # --- version-specific checks -------------------------------------------
    if version == 2:
        if "checksum" not in obj:
            raise CodecError("version 2 record missing checksum")
        expected = _compute_checksum(id_val, value_val, version)
        if obj["checksum"] != expected:
            raise CodecError("checksum mismatch")

    # --- return only known fields (R6) -------------------------------------
    return {"id": id_val, "value": value_val, "version": version}
