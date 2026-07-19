EXPECTED = ["C1", "P1", "P2", "V1", "V2", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "D1", "X1", "X2"]
ROOT = project_root("wirecodec")

try:
    module = importlib.import_module("wirecodec.public")
    encode = module.encode
    decode = module.decode
    CodecError = module.CodecError
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checksum(record):
    import hashlib

    payload = {"id": record["id"], "value": record["value"], "version": 2}
    return hashlib.sha256(compact(payload).encode("utf-8")).hexdigest()


def encode_example():
    source = {"id": "a", "value": 2}
    before = deepcopy(source)
    text = encode(source)
    expect_equal(source, before)
    raw = json.loads(text)
    expect_equal(set(raw), {"checksum", "id", "value", "version"})
    expect_equal(raw["version"], 2)
    expect_equal(raw["checksum"], checksum(raw))
    expect_equal(text, compact(raw))


def decode_v1_example():
    expect_equal(decode('{"id":"a","value":2}'), {"id": "a", "value": 2, "version": 1})


def valid_v2_text(identifier="a", value=2):
    raw = {"id": identifier, "value": value, "version": 2}
    raw["checksum"] = checksum(raw)
    return compact(raw)


def decode_v2_example():
    expect_equal(decode(valid_v2_text()), {"id": "a", "value": 2, "version": 2})


def unknown_example(version=2):
    if version == 2:
        raw = json.loads(valid_v2_text())
    else:
        raw = {"id": "a", "value": 2, "version": 1}
    raw["note"] = "ok"
    text = compact(raw)
    if MODE == "reject":
        expect_raises(CodecError, lambda: decode(text))
    else:
        expected = {"id": "a", "value": 2, "version": version}
        if MODE == "preserve":
            expected["extras"] = {"note": "ok"}
        expect_equal(decode(text), expected)


def checksum_error():
    raw = json.loads(valid_v2_text())
    raw["value"] = 3
    expect_raises(CodecError, lambda: decode(compact(raw)))


def deterministic_no_mutation():
    source = {"id": "café", "value": -4}
    before = deepcopy(source)
    first = encode(source)
    second = encode(source)
    expect_equal(first, second)
    expect_equal(source, before)
    if "café" not in first:
        raise AssertionError("Unicode was escaped")


def invalid_encode():
    invalid = [
        {"value": 1},
        {"id": "", "value": 1},
        {"id": "a", "value": True},
        {"id": "a", "value": 1, "extra": 2},
    ]
    for record in invalid:
        before = deepcopy(record)
        expect_raises(ValueError, lambda record=record: encode(record))
        expect_equal(record, before)


def canonical_exactness():
    raw = json.loads(encode({"id": "z", "value": 10}))
    expect_equal(raw["checksum"], checksum(raw))
    expect_equal(encode({"id": "z", "value": 10}), compact(raw))


def v1_compatibility():
    expect_equal(decode('{"value":3,"id":"b"}'), {"id": "b", "value": 3, "version": 1})
    expect_equal(decode('{"version":1,"id":"b","value":3}'), {"id": "b", "value": 3, "version": 1})


def decode_errors():
    for text in ["not-json", "[]", '{"version":3,"id":"a","value":1}', '{"id":"a","value":true}']:
        expect_raises(CodecError, lambda text=text: decode(text))
    expect_raises(CodecError, lambda: decode(3))


def extras_absent_when_empty():
    result = decode(valid_v2_text("x", 1))
    if "extras" in result:
        raise AssertionError("extras must be omitted when no unknown fields exist")


record("E1_public_import", "R1", "visible", lambda: callable(encode) and callable(decode), "E1")
record("E1_encode_validation", "R2", "visible", encode_example, "E1")
record("E1_canonical_v2", "R3", "visible", encode_example, "E1")
record("E1_evolved_encoding", "V1", "visible", encode_example, "E1")
record("E1_preserved_imports", "P2", "visible", lambda: callable(encode) and callable(decode), "E1")
record("E1_end_to_end", "D1", "visible", encode_example, "E1")
record("E2_decode_v1", "R4", "visible", decode_v1_example, "E2")
record("E2_preserve_v1", "P1", "visible", decode_v1_example, "E2")
record("E3_v2_canonical", "R3", "visible", decode_v2_example, "E3")
record("E3_decode_v2", "R4", "visible", decode_v2_example, "E3")
record("E3_validate_checksum", "R5", "visible", decode_v2_example, "E3")
record("E3_evolved_decode", "V2", "visible", decode_v2_example, "E3")
record("E4_unknown_fields", "R6", "visible", unknown_example, "E4")
record("E5_checksum_mismatch", "R5", "visible", checksum_error, "E5")
record("E5_codec_error", "X2", "visible", checksum_error, "E5")
record("E6_encode_repeatability", "R2", "visible", deterministic_no_mutation, "E6")
record("E6_deterministic_bytes", "R7", "visible", deterministic_no_mutation, "E6")
record("E7_invalid_encode", "R2", "visible", invalid_encode, "E7")
record("E7_value_error", "X1", "visible", invalid_encode, "E7")
record("E8_stdlib_sha256", "C1", "visible", lambda: (encode_example(), assert_stdlib_only(ROOT, "wirecodec")), "E8")

record("hidden_public_symbols", "R1", "hidden", lambda: callable(encode) and callable(decode) and issubclass(CodecError, ValueError))
record("hidden_encode_input_contract", "R2", "hidden", invalid_encode)
record("hidden_canonical_checksum", "R3", "hidden", canonical_exactness)
record("hidden_explicit_v1", "R4", "hidden", v1_compatibility)
record("hidden_v2_checksum_rejection", "R5", "hidden", checksum_error)
record("hidden_unknown_v1", "R6", "hidden", lambda: unknown_example(1))
record("hidden_unknown_v2", "R6", "hidden", lambda: unknown_example(2))
record("hidden_empty_extras_omitted", "R6", "hidden", extras_absent_when_empty)
record("hidden_unicode_repeatability", "R7", "hidden", deterministic_no_mutation)
record("hidden_full_smoke", "D1", "hidden", decode_v2_example)
record("hidden_stdlib_and_sha256", "C1", "hidden", lambda: (canonical_exactness(), assert_stdlib_only(ROOT, "wirecodec")))
record("hidden_v1_compatibility", "P1", "hidden", v1_compatibility)
record("hidden_import_stability", "P2", "hidden", lambda: callable(encode) and callable(decode))
record("hidden_v2_encode", "V1", "hidden", canonical_exactness)
record("hidden_v2_decode", "V2", "hidden", decode_v2_example)
record("hidden_value_error", "X1", "hidden", invalid_encode)
record("hidden_codec_errors", "X2", "hidden", decode_errors)

finish(EXPECTED)
