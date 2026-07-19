EXPECTED = ["C1", "C2", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "D1", "X1", "X2"]
ROOT = project_root("idledger")

try:
    module = importlib.import_module("idledger.public")
    Ledger = module.Ledger
    InsufficientFunds = module.InsufficientFunds
    CommandConflict = module.CommandConflict
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


DEBIT = {"id": "c1", "account": "a", "kind": "debit", "amount": 40}


def basic_example():
    ledger = Ledger({"a": 100})
    expect_equal(ledger.apply(deepcopy(DEBIT)), {"id": "c1", "account": "a", "balance": 60})
    expect_equal(ledger.snapshot(), {"a": 60})


def duplicate_example():
    ledger = Ledger({"a": 100})
    first = ledger.apply(deepcopy(DEBIT))
    first["balance"] = -999
    second = ledger.apply(deepcopy(DEBIT))
    expect_equal(second, {"id": "c1", "account": "a", "balance": 60})
    expect_equal(ledger.snapshot(), {"a": 60})


def conflict_example():
    ledger = Ledger({"a": 100})
    original = ledger.apply(deepcopy(DEBIT))
    replacement = {"id": "c1", "account": "a", "kind": "credit", "amount": 20}
    if MODE == "conflict":
        expect_raises(CommandConflict, lambda: ledger.apply(replacement))
        expect_equal(ledger.snapshot(), {"a": 60})
    elif MODE == "firstwins":
        expect_equal(ledger.apply(replacement), original)
        expect_equal(ledger.snapshot(), {"a": 60})
    else:
        expect_equal(ledger.apply(replacement), {"id": "c1", "account": "a", "balance": 120})
        expect_equal(ledger.snapshot(), {"a": 120})


def insufficient_example():
    ledger = Ledger({"a": 100})
    bad = {"id": "x", "account": "a", "kind": "debit", "amount": 101}
    expect_raises(InsufficientFunds, lambda: ledger.apply(bad))
    expect_equal(ledger.snapshot(), {"a": 100})
    good = {"id": "x", "account": "a", "kind": "credit", "amount": 1}
    expect_equal(ledger.apply(good), {"id": "x", "account": "a", "balance": 101})


def invalid_example():
    ledger = Ledger({"a": 10})
    before = ledger.snapshot()
    invalid = [
        {"id": "x", "account": "a", "kind": "credit", "amount": True},
        {"id": "x", "account": "a", "kind": "credit", "amount": 0},
        {"id": "x", "account": "a", "kind": "credit", "amount": 1, "extra": 2},
    ]
    for command in invalid:
        expect_raises(ValueError, lambda command=command: ledger.apply(command))
        expect_equal(ledger.snapshot(), before)


def concurrent_example():
    ledger = Ledger({"a": 0})
    errors = []

    def worker(index):
        try:
            ledger.apply({"id": f"c{index}", "account": "a", "kind": "credit", "amount": 1})
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    expect_equal(errors, [])
    expect_equal(ledger.snapshot(), {"a": 50})


def initial_and_snapshot():
    ledger = Ledger({"z": 2, "a": 1})
    snapshot = ledger.snapshot()
    expect_equal(list(snapshot), ["a", "z"])
    snapshot["a"] = 99
    expect_equal(ledger.snapshot(), {"a": 1, "z": 2})
    for bad in [{"a": -1}, {"a": True}, {1: 2}, []]:
        expect_raises(ValueError, lambda bad=bad: Ledger(bad))


def exact_command_contract():
    ledger = Ledger()
    result = ledger.apply({"id": "n", "account": "new", "kind": "credit", "amount": 7})
    expect_equal(result, {"id": "n", "account": "new", "balance": 7})
    expect_equal(set(result), {"id", "account", "balance"})


def hidden_conflict():
    ledger = Ledger({"a": 100})
    original_command = {"id": "same", "account": "a", "kind": "credit", "amount": 50}
    original_result = ledger.apply(original_command)
    replacement = {"id": "same", "account": "a", "kind": "debit", "amount": 30}
    if MODE == "conflict":
        expect_raises(CommandConflict, lambda: ledger.apply(replacement))
        expect_equal(ledger.snapshot(), {"a": 150})
    elif MODE == "firstwins":
        expect_equal(ledger.apply(replacement), original_result)
        expect_equal(ledger.snapshot(), {"a": 150})
    else:
        expect_equal(ledger.apply(replacement), {"id": "same", "account": "a", "balance": 70})
        expect_equal(ledger.snapshot(), {"a": 70})


def replacement_rollback():
    if MODE != "lastwins":
        hidden_conflict()
        return
    ledger = Ledger({"a": 10})
    ledger.apply({"id": "same", "account": "a", "kind": "credit", "amount": 5})
    expect_raises(
        InsufficientFunds,
        lambda: ledger.apply({"id": "same", "account": "a", "kind": "debit", "amount": 20}),
    )
    expect_equal(ledger.snapshot(), {"a": 15})
    expect_equal(
        ledger.apply({"id": "same", "account": "a", "kind": "credit", "amount": 5}),
        {"id": "same", "account": "a", "balance": 15},
    )


record("E1_public_import", "R1", "visible", lambda: callable(Ledger), "E1")
record("E1_initial_and_snapshot", "R2", "visible", basic_example, "E1")
record("E1_apply_result", "R3", "visible", basic_example, "E1")
record("E1_nonnegative_integer_balance", "C1", "visible", basic_example, "E1")
record("E1_end_to_end", "D1", "visible", basic_example, "E1")
record("E2_identical_idempotency", "R4", "visible", duplicate_example, "E2")
record("E3_conflict_policy", "R5", "visible", conflict_example, "E3")
record("E4_insufficient_funds", "R6", "visible", insufficient_example, "E4")
record("E4_insufficient_error", "X1", "visible", insufficient_example, "E4")
record("E5_invalid_atomicity", "R7", "visible", invalid_example, "E5")
record("E5_invalid_error", "X2", "visible", invalid_example, "E5")
record("E6_concurrent_credits", "R8", "visible", concurrent_example, "E6")
record("E7_stdlib_dependencies", "C2", "visible", lambda: assert_stdlib_only(ROOT, "idledger"), "E7")

record("hidden_public_symbols", "R1", "hidden", lambda: all(callable(value) for value in [Ledger]))
record("hidden_initial_validation_copy", "R2", "hidden", initial_and_snapshot)
record("hidden_exact_command_result", "R3", "hidden", exact_command_contract)
record("hidden_duplicate_result_copy", "R4", "hidden", duplicate_example)
record("hidden_conflict_policy", "R5", "hidden", hidden_conflict)
record("hidden_lastwins_rollback", "R5", "hidden", replacement_rollback)
record("hidden_failed_id_reusable", "R6", "hidden", insufficient_example)
record("hidden_invalid_commands_atomic", "R7", "hidden", invalid_example)
record("hidden_concurrency", "R8", "hidden", concurrent_example)
record("hidden_full_smoke", "D1", "hidden", exact_command_contract)
record("hidden_no_negative_balance", "C1", "hidden", insufficient_example)
record("hidden_stdlib_only", "C2", "hidden", lambda: assert_stdlib_only(ROOT, "idledger"))
record("hidden_insufficient_type", "X1", "hidden", insufficient_example)
record("hidden_value_error_type", "X2", "hidden", invalid_example)

finish(EXPECTED)
