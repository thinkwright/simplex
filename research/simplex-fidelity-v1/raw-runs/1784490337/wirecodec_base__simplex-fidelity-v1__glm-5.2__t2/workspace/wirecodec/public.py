"""Public API for the wirecodec wire codec.

This module exposes :func:`encode`, :func:`decode` and :class:`CodecError`.

Contract notes
---------------
* Only the Python standard library is used; the integrity digest is SHA-256
  from :mod:`hashlib` (see constraint ``C1``).
* :func:`encode` produces a deterministic, compact JSON string for version 2
  records. The ``checksum`` is the lowercase SHA-256 hex digest of the compact,
  sorted-keys JSON of just ``id``, ``value`` and ``version``.
* :func:`decode` accepts version 1 (no checksum) and version 2 (checksum
  validated) records, treats an absent ``version`` as ``1`` and discards any
  unknown top-level fields after validating the known ones.
"""

import hashlib
import json

__all__ = ["CodecError", "decode", "encode"]

# Wire format versions supported on decode.
_SUPPORTED_VERSIONS = (1, 2)
# Version produced by :func:`encode`.
_CURRENT_VERSION = 2


class CodecError(Exception):
    """Raised when a wire string cannot be decoded.

    This covers malformed JSON, non-object JSON, unsupported versions,
    invalid known fields and checksum mismatches.
    """


def _canonical_json(obj):
    """Return compact JSON for ``obj`` with object keys sorted.

    Compact means no insignificant whitespace; object keys are emitted in
    sorted order so the result is deterministic for equal inputs.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(text):
    """Return the lowercase SHA-256 hex digest of the UTF-8 ``text``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_real_int(value):
    """True when ``value`` is an :class:`int` but not a :class:`bool`."""
    return isinstance(value, int) and not isinstance(value, bool)


def encode(record):
    """Encode ``record`` into a compact, deterministic version 2 wire string.

    ``record`` must be a mapping containing exactly the fields ``id`` and
    ``value`` where ``id`` is a non-empty :class:`str` and ``value`` is an
    :class:`int` that is not a :class:`bool`. The input mapping is never
    mutated.

    Raises:
        ValueError: if ``record`` is not a dict, lacks either required field,
            contains extra fields, or has an invalid ``id``/``value``.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    # The record must carry exactly the two known fields.
    if set(record.keys()) != {"id", "value"}:
        raise ValueError("record must contain exactly 'id' and 'value' fields")

    ident = record["id"]
    if not isinstance(ident, str) or ident == "":
        raise ValueError("field 'id' must be a non-empty string")

    value = record["value"]
    if not _is_real_int(value):
        raise ValueError("field 'value' must be an integer and not a boolean")

    # Build the checksummed payload from only the known fields + version.
    payload = _canonical_json(
        {"id": ident, "value": value, "version": _CURRENT_VERSION}
    )
    checksum = _sha256_hex(payload)

    envelope = {
        "checksum": checksum,
        "id": ident,
        "value": value,
        "version": _CURRENT_VERSION,
    }
    return _canonical_json(envelope)


def decode(text):
    """Decode a wire JSON ``text`` into a fresh ``{id, value, version}`` dict.

    An absent ``version`` is treated as ``1``. Version 2 records have their
    ``checksum`` validated against the canonical known-field payload. Unknown
    top-level fields are discarded after the known fields are validated.

    Raises:
        CodecError: for malformed JSON, non-object JSON, unsupported
            versions, invalid known fields, or a checksum mismatch.
    """
    if not isinstance(text, str):
        raise CodecError("input must be a string")

    try:
        record = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CodecError("malformed JSON input") from exc

    if not isinstance(record, dict):
        raise CodecError("wire input must be a JSON object")

    # Resolve the version: absent version is version 1.
    if "version" in record:
        version = record["version"]
        if isinstance(version, bool) or not isinstance(version, int):
            raise CodecError("field 'version' must be an integer")
        if version not in _SUPPORTED_VERSIONS:
            raise CodecError("unsupported version: %r" % (version,))
    else:
        version = 1

    # Validate the known data fields for either version.
    if "id" not in record:
        raise CodecError("missing required field 'id'")
    ident = record["id"]
    if not isinstance(ident, str) or ident == "":
        raise CodecError("field 'id' must be a non-empty string")

    if "value" not in record:
        raise CodecError("missing required field 'value'")
    value = record["value"]
    if not _is_real_int(value):
        raise CodecError("field 'value' must be an integer and not a boolean")

    # Version 2 carries an integrity checksum that must be verified.
    if version == 2:
        if "checksum" not in record:
            raise CodecError("missing required field 'checksum'")
        checksum = record["checksum"]
        if not isinstance(checksum, str):
            raise CodecError("field 'checksum' must be a string")
        payload = _canonical_json({"id": ident, "value": value, "version": version})
        if checksum != _sha256_hex(payload):
            raise CodecError("checksum mismatch")

    # Discard unknown top-level fields; return a brand-new dict.
    return {"id": ident, "value": value, "version": version}