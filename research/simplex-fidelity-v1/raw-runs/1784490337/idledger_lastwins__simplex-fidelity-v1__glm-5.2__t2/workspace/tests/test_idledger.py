"""Tests for the idledger package covering rules R1-R8 and examples E1-E7."""

import ast
import os
import sys
import threading
import unittest

from idledger.public import CommandConflict, InsufficientFunds, Ledger


class Examples(unittest.TestCase):
    # E1 -> R1, R2, R3, C1, D1
    def test_E1_basic_debit(self):
        result = Ledger({"a": 100}).apply(
            {"id": "c1", "account": "a", "kind": "debit", "amount": 40}
        )
        self.assertEqual(result, {"id": "c1", "account": "a", "balance": 60})

    # E2 -> R4
    def test_E2_idempotent_repeat(self):
        ledger = Ledger({"a": 100})
        cmd = {"id": "c1", "account": "a", "kind": "debit", "amount": 40}
        first = ledger.apply(cmd)
        second = ledger.apply(cmd)
        self.assertEqual(first, second)
        # balance changes only once
        self.assertEqual(ledger.snapshot(), {"a": 60})

    # E3 -> R5
    def test_E3_conflict_replace(self):
        ledger = Ledger({"a": 100})
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
        result = ledger.apply(
            {"id": "c1", "account": "a", "kind": "credit", "amount": 20}
        )
        self.assertEqual(result, {"id": "c1", "account": "a", "balance": 120})
        self.assertEqual(ledger.snapshot(), {"a": 120})

    # E4 -> R6, X1
    def test_E4_insufficient_funds_reusable(self):
        ledger = Ledger({"a": 100})
        with self.assertRaises(InsufficientFunds):
            ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 101})
        # the command id remains reusable
        result = ledger.apply(
            {"id": "c1", "account": "a", "kind": "debit", "amount": 40}
        )
        self.assertEqual(result, {"id": "c1", "account": "a", "balance": 60})

    # E5 -> R7, X2
    def test_E5_invalid_commands(self):
        ledger = Ledger({"a": 100})
        bad_commands = [
            {"id": "c1", "account": "a", "kind": "debit", "amount": True},
            {"id": "c1", "account": "a", "kind": "debit", "amount": 0},
            {"id": "c1", "account": "a", "kind": "debit", "amount": 40, "extra": 1},
            {"id": "c1", "account": "a", "kind": "transfer", "amount": 40},
            {"id": "c1", "account": "a", "kind": "debit"},  # missing amount
            {"account": "a", "kind": "debit", "amount": 40},  # missing id
            "not a mapping",
        ]
        for bad in bad_commands:
            with self.assertRaises(ValueError):
                ledger.apply(bad)
            # no state change after any invalid command
            self.assertEqual(ledger.snapshot(), {"a": 100})

    def test_E5_invalid_initial(self):
        for bad in [{"a": -1}, {"a": 1.5}, {"a": True}, [("a", 100)], "x", 5]:
            with self.assertRaises(ValueError):
                Ledger(bad)

    # E6 -> R8
    def test_E6_concurrent_credits(self):
        ledger = Ledger({"a": 0})
        n = 200
        amount = 7

        def worker(i):
            ledger.apply(
                {"id": "c%d" % i, "account": "a", "kind": "credit", "amount": amount}
            )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(ledger.snapshot(), {"a": n * amount})

    # E7 -> C2
    def test_E7_dependencies_stdlib_only(self):
        import idledger

        pkg_dir = os.path.dirname(os.path.abspath(idledger.__file__))
        names = set()
        for root, _dirs, files in os.walk(pkg_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                with open(os.path.join(root, fname), encoding="utf-8") as handle:
                    tree = ast.parse(handle.read(), filename=fname)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            names.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.level and node.level > 0:
                            continue  # relative import -> within idledger
                        if node.module:
                            names.add(node.module.split(".")[0])
        for name in names:
            self.assertTrue(
                name == "idledger" or name in sys.stdlib_module_names,
                "non-stdlib dependency: %s" % name,
            )


class Rules(unittest.TestCase):
    def test_R1_public_api_exports(self):
        from idledger.public import CommandConflict, InsufficientFunds, Ledger

        self.assertTrue(issubclass(InsufficientFunds, Exception))
        self.assertTrue(issubclass(CommandConflict, Exception))
        self.assertTrue(callable(Ledger))

    def test_R2_snapshot_sorted_and_isolated(self):
        ledger = Ledger({"b": 1, "a": 2, "c": 3})
        snap = ledger.snapshot()
        self.assertEqual(list(snap.keys()), ["a", "b", "c"])
        # mutating the snapshot does not affect the ledger
        snap["a"] = 999
        self.assertEqual(ledger.snapshot(), {"a": 2, "b": 1, "c": 3})

    def test_R3_result_shape(self):
        result = Ledger({"a": 100}).apply(
            {"id": "c1", "account": "a", "kind": "credit", "amount": 10}
        )
        self.assertEqual(set(result.keys()), {"id", "account", "balance"})

    def test_R6_failed_debit_no_state_change(self):
        ledger = Ledger({"a": 100})
        with self.assertRaises(InsufficientFunds):
            ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 101})
        self.assertEqual(ledger.snapshot(), {"a": 100})

    def test_R7_invalid_command_preserves_history(self):
        ledger = Ledger({"a": 100})
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
        with self.assertRaises(ValueError):
            ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 0})
        # history unchanged: repeating the original is still idempotent
        self.assertEqual(
            ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40}),
            {"id": "c1", "account": "a", "balance": 60},
        )
        self.assertEqual(ledger.snapshot(), {"a": 60})

    def test_R7_invalid_new_id_not_consumed(self):
        ledger = Ledger({"a": 100})
        with self.assertRaises(ValueError):
            ledger.apply({"id": "c2", "account": "a", "kind": "debit", "amount": 0})
        result = ledger.apply(
            {"id": "c2", "account": "a", "kind": "credit", "amount": 5}
        )
        self.assertEqual(result, {"id": "c2", "account": "a", "balance": 105})

    def test_R5_conflict_failure_preserves_original(self):
        ledger = Ledger({"a": 100})
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
        # balance is 60; replacing with a debit of 200 would go negative
        with self.assertRaises(InsufficientFunds):
            ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 200})
        self.assertEqual(ledger.snapshot(), {"a": 60})
        self.assertEqual(
            ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40}),
            {"id": "c1", "account": "a", "balance": 60},
        )

    def test_R5_conflict_different_account(self):
        ledger = Ledger({"a": 100, "b": 0})
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
        result = ledger.apply(
            {"id": "c1", "account": "b", "kind": "credit", "amount": 10}
        )
        self.assertEqual(result, {"id": "c1", "account": "b", "balance": 10})
        self.assertEqual(ledger.snapshot(), {"a": 100, "b": 10})

    def test_credit_creates_new_account(self):
        ledger = Ledger()
        result = ledger.apply(
            {"id": "c1", "account": "a", "kind": "credit", "amount": 50}
        )
        self.assertEqual(result, {"id": "c1", "account": "a", "balance": 50})
        self.assertEqual(ledger.snapshot(), {"a": 50})

    def test_debit_to_zero_keeps_account(self):
        ledger = Ledger({"a": 100})
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 100})
        self.assertEqual(ledger.snapshot(), {"a": 0})

    def test_R8_concurrent_snapshot_consistency(self):
        ledger = Ledger({"a": 0})
        stop = threading.Event()

        def crediter():
            i = 0
            while not stop.is_set():
                ledger.apply(
                    {"id": "t%d" % i, "account": "a", "kind": "credit", "amount": 1}
                )
                i += 1

        thread = threading.Thread(target=crediter)
        thread.start()
        for _ in range(100):
            snap = ledger.snapshot()
            self.assertGreaterEqual(snap.get("a", 0), 0)
        stop.set()
        thread.join()
        self.assertGreaterEqual(ledger.snapshot()["a"], 0)


if __name__ == "__main__":
    unittest.main()