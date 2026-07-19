"""Public API for the configweave package.

This module exposes :func:`merge_layers`, which combines a list of
configuration "layers" (plain ``dict`` objects) into a single merged
dictionary according to the configweave contract.

Only the Python standard library is used.
"""
from __future__ import annotations

import copy

__all__ = ["merge_layers"]


def _validate(value, path):
    """Recursively ensure every dict key within ``value`` is a string.

    ``value`` may be a dict, a list, or a scalar.  Dicts are checked for
    string keys and recursed into; lists are recursed into so that dicts
    nested at any depth are validated too.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "non-string key {0!r} found at {1}".format(key, path)
                )
            _validate(item, "{0}[{1!r}]".format(path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate(item, "{0}[{1}]".format(path, index))


def _merge_into(acc, layer):
    """Merge a single input ``layer`` into the owned result dict ``acc``.

    ``acc`` is mutated freely (it belongs to us); ``layer`` is only read
    from and is never mutated.  Every value placed into ``acc`` is a deep
    copy, so no mutable container in ``acc`` is shared with any input.
    """
    for key, new_value in layer.items():
        if new_value is None:
            # A null value deletes the key at this nesting level.  Deleting
            # a key that is absent is a no-op.
            acc.pop(key, None)
        elif (
            key in acc
            and isinstance(acc[key], dict)
            and isinstance(new_value, dict)
        ):
            # Both old and new values are mappings: merge recursively.
            _merge_into(acc[key], new_value)
        elif (
            key in acc
            and isinstance(acc[key], list)
            and isinstance(new_value, list)
        ):
            # Both old and new values are lists: concatenate deep copies in
            # old-then-new order.
            acc[key] = copy.deepcopy(acc[key]) + copy.deepcopy(new_value)
        else:
            # Otherwise the later value replaces the earlier one.  This
            # also covers "a list replaces a non-list".
            acc[key] = copy.deepcopy(new_value)


def merge_layers(layers):
    """Merge configuration layers from first to last.

    Parameters
    ----------
    layers:
        A list of ``dict`` layers applied in order (first to last).

    Returns
    -------
    dict
        A freshly built dictionary containing deep copies of the merged
        values.  No mutable container in the result is shared with any
        input layer, and no input layer is ever mutated.

    Raises
    ------
    TypeError
        If ``layers`` is not a list, if any layer is not a dict, or if any
        key at any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            "layers must be a list of dicts, got {0}".format(
                type(layers).__name__
            )
        )

    # Validate every layer up front so that an invalid structure raises
    # TypeError before any merging (and therefore without mutating inputs).
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                "layer at index {0} must be a dict, got {1}".format(
                    index, type(layer).__name__
                )
            )
        _validate(layer, "layers[{0}]".format(index))

    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result