"""Implementation of configweave.merge_layers.

Only the Python standard library is used.
"""

from __future__ import annotations

import copy
from typing import Any, List


__all__ = ["merge_layers"]


def _is_mapping(value: Any) -> bool:
    """Return True if value behaves like a mapping (dict)."""
    return isinstance(value, dict)


def _check_keys(value: Any, path: str) -> None:
    """Recursively verify that every key at every nesting level is a string.

    Raises TypeError on the first violation.
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"non-string key {k!r} at {path}"
                )
            _check_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _check_keys(item, f"{path}[{i}]")


def _check_layer(layer: Any) -> None:
    """Validate a single layer is a dict with string keys throughout."""
    if not isinstance(layer, dict):
        raise TypeError(
            f"layer must be a dict, got {type(layer).__name__}"
        )
    _check_keys(layer, "")


def _equality_distinct(value: Any, seen: List[Any]) -> bool:
    """Return True if value is not equality-equal to any item in seen."""
    for existing in seen:
        if existing == value:
            return False
    return True


def _merge_lists(old: List[Any], new: List[Any]) -> List[Any]:
    """Concatenate old then new, keeping only the first occurrence of each
    equality-distinct value."""
    result: List[Any] = []
    for item in old:
        if _equality_distinct(item, result):
            result.append(item)
    for item in new:
        if _equality_distinct(item, result):
            result.append(item)
    return result


def _merge(old: Any, new: Any) -> Any:
    """Merge two values according to the configweave rules.

    - Both mappings -> recursive merge.
    - Both lists -> concatenate with first-occurrence dedup.
    - Otherwise -> later non-list value replaces earlier (None deletes).
    """
    # new is None -> delete key (handled by caller via sentinel; here we
    # simply return None and the caller drops the key).
    if new is None:
        return None

    if _is_mapping(old) and _is_mapping(new):
        return _merge_mappings(old, new)

    if isinstance(old, list) and isinstance(new, list):
        return _merge_lists(old, new)

    # A list still replaces a non-list (and vice versa) per R3/R4 wording:
    # "later non-list value replaces the earlier value" and
    # "a list still replaces a non-list". The combined effect is that the
    # later value wins unless both are mappings or both are lists.
    return copy.deepcopy(new)


def _merge_mappings(old: dict, new: dict) -> dict:
    """Merge two mappings recursively, returning a new dict."""
    result: dict = {}
    # Start with deep copies of old's entries.
    for k, v in old.items():
        result[k] = copy.deepcopy(v)

    for k, v in new.items():
        if v is None:
            # Delete the key at this level.
            if k in result:
                del result[k]
            continue

        if k in result:
            result[k] = _merge(result[k], v)
        else:
            # New key: deep copy the value so the result doesn't share
            # mutable containers with the input.
            result[k] = copy.deepcopy(v)

    return result


def merge_layers(layers: List[dict]) -> dict:
    """Merge a list of layer dicts from first to last.

    Returns an empty dict for an empty layer list. The result is a deep
    copy: mutating it cannot mutate any input layer, and input layers
    are never mutated.

    Raises TypeError if any layer is not a dict or any key at any
    nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )

    for layer in layers:
        _check_layer(layer)

    result: dict = {}
    for layer in layers:
        result = _merge_mappings(result, layer)

    return result