from __future__ import annotations

from copy import deepcopy
from threading import RLock


MODE = "__MODE__"


class InsufficientFunds(RuntimeError):
    pass


class CommandConflict(RuntimeError):
    pass


def _is_cents(value: object, *, positive: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value > 0 if positive else value >= 0


class Ledger:
    def __init__(self, initial=None):
        if initial is None:
            initial = {}
        if not isinstance(initial, dict):
            raise ValueError("initial balances must be a mapping")
        for account, balance in initial.items():
            if not isinstance(account, str) or not account or not _is_cents(balance):
                raise ValueError("invalid initial balance")
        self._balances = dict(initial)
        self._commands: dict[str, tuple[dict, dict]] = {}
        self._lock = RLock()

    @staticmethod
    def _validate(command: object) -> dict:
        if not isinstance(command, dict) or set(command) != {"id", "account", "kind", "amount"}:
            raise ValueError("command must contain exactly id, account, kind, and amount")
        if not isinstance(command["id"], str) or not command["id"]:
            raise ValueError("command id must be a non-empty string")
        if not isinstance(command["account"], str) or not command["account"]:
            raise ValueError("account must be a non-empty string")
        if command["kind"] not in {"credit", "debit"}:
            raise ValueError("kind must be credit or debit")
        if not _is_cents(command["amount"], positive=True):
            raise ValueError("amount must be a positive integer")
        return deepcopy(command)

    @staticmethod
    def _apply_to(balances: dict[str, int], command: dict) -> dict:
        account = command["account"]
        current = balances.get(account, 0)
        delta = command["amount"] if command["kind"] == "credit" else -command["amount"]
        updated = current + delta
        if updated < 0:
            raise InsufficientFunds("debit would make the balance negative")
        balances[account] = updated
        return {"id": command["id"], "account": account, "balance": updated}

    @staticmethod
    def _undo_from(balances: dict[str, int], command: dict) -> None:
        account = command["account"]
        delta = command["amount"] if command["kind"] == "credit" else -command["amount"]
        updated = balances.get(account, 0) - delta
        if updated < 0:
            raise InsufficientFunds("original command cannot be reversed safely")
        balances[account] = updated

    def apply(self, command) -> dict:
        normalized = self._validate(command)
        with self._lock:
            prior = self._commands.get(normalized["id"])
            if prior is not None:
                old_command, old_result = prior
                if normalized == old_command or MODE == "firstwins":
                    return deepcopy(old_result)
                if MODE == "conflict":
                    raise CommandConflict("command id was already used with different content")
                candidate = dict(self._balances)
                self._undo_from(candidate, old_command)
                result = self._apply_to(candidate, normalized)
                self._balances = candidate
                self._commands[normalized["id"]] = (deepcopy(normalized), deepcopy(result))
                return deepcopy(result)

            candidate = dict(self._balances)
            result = self._apply_to(candidate, normalized)
            self._balances = candidate
            self._commands[normalized["id"]] = (deepcopy(normalized), deepcopy(result))
            return deepcopy(result)

    def snapshot(self) -> dict:
        with self._lock:
            return {account: self._balances[account] for account in sorted(self._balances)}
