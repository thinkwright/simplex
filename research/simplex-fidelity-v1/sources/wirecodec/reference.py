from __future__ import annotations

import hashlib
import json


MODE = "__MODE__"


class CodecError(ValueError):
    pass


def _compact(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _valid_known(record: dict) -> bool:
    return (
        isinstance(record.get("id"), str)
        and bool(record["id"])
        and isinstance(record.get("value"), int)
        and not isinstance(record["value"], bool)
    )


def _checksum(record: dict) -> str:
    payload = {"id": record["id"], "value": record["value"], "version": 2}
    return hashlib.sha256(_compact(payload).encode("utf-8")).hexdigest()


def encode(record: dict) -> str:
    if not isinstance(record, dict) or set(record) != {"id", "value"} or not _valid_known(record):
        raise ValueError("record must contain exactly a non-empty string id and integer value")
    result = {"id": record["id"], "value": record["value"], "version": 2}
    result["checksum"] = _checksum(result)
    return _compact(result)


def decode(text: str) -> dict:
    if not isinstance(text, str):
        raise CodecError("wire input must be a JSON string")
    try:
        raw = json.loads(text)
    except Exception as error:
        raise CodecError("malformed JSON") from error
    if not isinstance(raw, dict):
        raise CodecError("wire input must be a JSON object")
    version = raw.get("version", 1)
    if isinstance(version, bool) or version not in {1, 2}:
        raise CodecError("unsupported version")
    allowed = {"id", "value", "version"} | ({"checksum"} if version == 2 else set())
    unknown = {key: value for key, value in raw.items() if key not in allowed}
    if unknown and MODE == "reject":
        raise CodecError("unknown top-level field")
    if not _valid_known(raw):
        raise CodecError("invalid id or value")
    if version == 2:
        checksum = raw.get("checksum")
        if not isinstance(checksum, str) or checksum != _checksum(raw):
            raise CodecError("checksum mismatch")
    result = {"id": raw["id"], "value": raw["value"], "version": version}
    if unknown and MODE == "preserve":
        result["extras"] = unknown
    return result
