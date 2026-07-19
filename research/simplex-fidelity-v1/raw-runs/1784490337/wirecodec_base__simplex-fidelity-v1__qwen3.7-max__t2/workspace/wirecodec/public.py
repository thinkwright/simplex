import json
import hashlib


class CodecError(Exception):
    """Raised for malformed JSON, unsupported versions, invalid fields, or checksum mismatch."""
    pass


def _compute_checksum(id_val, value_val, version_val):
    """SHA-256 lowercase hex over compact sorted JSON of {id, value, version}."""
    payload = json.dumps(
        {"id": id_val, "value": value_val, "version": version_val},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode(record):
    """Encode a record into compact version-2 JSON with a SHA-256 checksum.

    Parameters
    ----------
    record : dict
        Must contain exactly a non-empty string ``id`` and an integer
        (non-boolean) ``value``.

    Returns
    -------
    str
        Compact JSON with sorted keys: checksum, id, value, version.

    Raises
    ------
    ValueError
        If the record is invalid.  The input is never mutated.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    if "id" not in record or "value" not in record:
        raise ValueError("record must contain 'id' and 'value'")

    id_val = record["id"]
    value_val = record["value"]

    if not isinstance(id_val, str) or len(id_val) == 0:
        raise ValueError("id must be a non-empty string")

    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise ValueError("value must be an integer (not boolean)")

    version = 2
    checksum = _compute_checksum(id_val, value_val, version)

    result = {
        "checksum": checksum,
        "id": id_val,
        "value": value_val,
        "version": version,
    }

    return json.dumps(result, separators=(",", ":"), sort_keys=True)


def decode(text):
    """Decode a JSON object string into a record dict.

    Absent ``version`` is treated as version 1.  Version 2 records are
    checksum-validated.  Unknown top-level fields are discarded.

    Returns
    -------
    dict
        New dict with keys ``id``, ``value``, ``version``.

    Raises
    ------
    CodecError
        For malformed JSON, unsupported versions, invalid fields, or
        checksum mismatch.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CodecError(f"malformed JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise CodecError("JSON value must be an object")

    # Determine version (absent → 1)
    version = data.get("version", 1)

    if not isinstance(version, int) or isinstance(version, bool):
        raise CodecError(f"invalid version field: {version!r}")

    if version not in (1, 2):
        raise CodecError(f"unsupported version: {version}")

    # Validate id
    if "id" not in data:
        raise CodecError("missing 'id' field")
    id_val = data["id"]
    if not isinstance(id_val, str) or len(id_val) == 0:
        raise CodecError("invalid 'id' field: must be a non-empty string")

    # Validate value
    if "value" not in data:
        raise CodecError("missing 'value' field")
    value_val = data["value"]
    if isinstance(value_val, bool) or not isinstance(value_val, int):
        raise CodecError("invalid 'value' field: must be an integer (not boolean)")

    # Version 2 checksum validation
    if version == 2:
        if "checksum" not in data:
            raise CodecError("missing 'checksum' field for version 2")
        expected = _compute_checksum(id_val, value_val, version)
        if data["checksum"] != expected:
            raise CodecError("checksum mismatch")

    # Return only known fields (R6: discard unknown top-level fields)
    return {"id": id_val, "value": value_val, "version": version}
