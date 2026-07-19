"""Core implementation of configweave's merge semantics.

Only the Python standard library is used.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


_MISSING = object()


def _is_mapping(value: Any) -> bool:
    """Return True if *value* is a dict (the only mapping type we accept)."""
    return isinstance(value, dict)


def _is_list(value: Any) -> bool:
    return isinstance(value, list)


def _is_null(value: Any) -> bool:
    """A "null" value is Python's ``None``."""
    return value is None


def _validate_keys(mapping: Dict[str, Any], path: str) -> None:
    """Ensure every key in *mapping* (recursively) is a string.

    Raises :class:`TypeError` with a descriptive message on the first
    non-string key encountered.
    """
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                f"configweave: non-string key {key!r} at path {path!r}; "
                "all keys must be strings"
            )
        if _is_mapping(value):
            _validate_keys(value, f"{path}.{key}" if path else key)
        elif _is_list(value):
            _validate_list_items(value, f"{path}.{key}" if path else key)


def _validate_list_items(items: List[Any], path: str) -> None:
    """Recursively validate dicts nested inside lists."""
    for index, item in enumerate(items):
        if _is_mapping(item):
            _validate_keys(item, f"{path}[{index}]")
        elif _is_list(item):
            _validate_list_items(item, f"{path}[{index}]")


def _validate_layer(layer: Any) -> None:
    """Ensure *layer* is a dict with string keys at every nesting level."""
    if not _is_mapping(layer):
        raise TypeError(
            f"configweave: each layer must be a dict, got {type(layer).__name__}"
        )
    _validate_keys(layer, "")


def _dedupe_concat(old_list: List[Any], new_list: List[Any]) -> List[Any]:
    """Concatenate *old_list* and *new_list*, keeping the first occurrence
    of each equality-distinct value (old-then-new order)."""
    result: List[Any] = []
    seen = set()
    for value in list(old_list) + list(new_list):
        # Use a key that works for the common case of hashable items.
        # For unhashable items (dicts/lists), fall back to linear search.
        try:
            key = ("h", hash(value))
        except TypeError:
            key = ("id", id(value))
            if key in seen:
                # Still need to check equality for unhashable items.
                if any(_shallow_equal(value, existing) for existing in result):
                    continue
            else:
                # Check if an equivalent item already exists in result.
                if any(_shallow_equal(value, existing) for existing in result):
                    seen.add(key)
                    continue
                seen.add(key)
            result.append(value)
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _shallow_equal(a: Any, b: Any) -> bool:
    """Equality check that works for both hashable and unhashable values."""
    if type(a) is not type(b):
        return False
    if _is_mapping(a) and _is_mapping(b):
        if a.keys() != b.keys():
            return False
        return all(_shallow_equal(a[k], b[k]) for k in a)
    if _is_list(a) and _is_list(b):
        if len(a) != len(b):
            return False
        return all(_shallow_equal(x, y) for x, y in zip(a, b))
    try:
        return a == b
    except Exception:
        return False


def _merge(old: Any, new: Any) -> Any:
    """Merge two values according to configweave's rules.

    Rules (R3, R4, R5):
    * If both are mappings → recursive merge.
    * If both are lists → concatenate with first-occurrence dedupe.
    * If *new* is None → delete (handled by caller; here we treat None as a
      plain replacement value, but the caller strips it before reaching us
      for the "delete" semantics).
    * Otherwise → *new* replaces *old*.
    """
    if _is_mapping(old) and _is_mapping(new):
        return _merge_mappings(old, new)
    if _is_list(old) and _is_list(new):
        return _dedupe_concat(old, new)
    # A list still replaces a non-list (R4 second clause).
    # Otherwise the later value replaces the earlier one (R3).
    return deepcopy(new)


def _merge_mappings(
    old: Dict[str, Any], new: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge two dicts, applying null-deletion semantics from *new*."""
    result: Dict[str, Any] = {}
    # Start with a deep copy of old so we never share mutable containers.
    for key, value in old.items():
        result[key] = deepcopy(value)

    for key, new_value in new.items():
        if _is_null(new_value):
            # R5: a later null deletes the key at its current level.
            result.pop(key, None)
            continue
        if key in result:
            result[key] = _merge(result[key], new_value)
        else:
            result[key] = deepcopy(new_value)

    return result


def merge_layers(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge a sequence of configuration layers from first to last.

    See the package docstring and the contract for full semantics.

    Raises :class:`TypeError` if *layers* is not a list of dicts or if any
    key at any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            f"configweave: layers must be a list, got {type(layers).__name__}"
        )

    for index, layer in enumerate(layers):
        if not _is_mapping(layer):
            raise TypeError(
                f"configweave: layer at index {index} must be a dict, "
                f"got {type(layer).__name__}"
            )
        _validate_keys(layer, f"layers[{index}]")

    result: Dict[str, Any] = {}
    for layer in layers:
        # Deep-copy the layer so we never mutate the input.
        layer_copy = deepcopy(layer)
        result = _merge_mappings(result, layer_copy)

    return result