"""Core implementation of configweave's layer merging.

Only the Python standard library is used (``copy``).
"""

import copy

__all__ = ["merge_layers"]

_MISSING = object()


def _validate_value(value):
    """Recursively validate that every dict key is a string.

    Dicts nested inside lists are also walked so that *every* key at *every*
    nesting level is checked.
    """
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise TypeError(
                    "configweave: every key must be a string, got "
                    "{!r} of type {}".format(key, type(key).__name__)
                )
            _validate_value(value[key])
    elif isinstance(value, list):
        for item in value:
            _validate_value(item)
    # Any other value (scalar or None) is structurally valid.


def _validate_layers(layers):
    """Validate that ``layers`` is a list of dicts with string keys."""
    if not isinstance(layers, list):
        raise TypeError(
            "configweave: layers must be a list of dicts, got "
            "{}".format(type(layers).__name__)
        )
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                "configweave: each layer must be a dict, got "
                "{} at index {}".format(type(layer).__name__, index)
            )
        _validate_value(layer)


def _merge_into(old, new):
    """Merge dict ``new`` into dict ``old`` in place.

    ``old`` is always a fresh container owned by the result, so mutating it
    never touches an input layer. Values taken from ``new`` are deep-copied so
    no mutable container is shared with any input.
    """
    for key, value in new.items():
        # A null value deletes the key at this nesting level (no-op if absent).
        if value is None:
            old.pop(key, None)
            continue

        existing = old.get(key, _MISSING)

        if isinstance(value, dict):
            if isinstance(existing, dict):
                # Both mappings: merge recursively.
                _merge_into(existing, value)
            else:
                # New/overriding mapping: build it fresh so nested nulls still
                # act as deletes rather than being stored verbatim.
                fresh = {}
                _merge_into(fresh, value)
                old[key] = fresh
        elif existing is not _MISSING and isinstance(existing, list) and isinstance(value, list):
            # Both lists: concatenate deep copies in old-then-new order.
            old[key] = copy.deepcopy(existing) + copy.deepcopy(value)
        else:
            # Otherwise the later value replaces the earlier one.
            old[key] = copy.deepcopy(value)


def merge_layers(layers):
    """Merge configuration ``layers`` (a list of dicts) from first to last.

    Returns a fresh dict with no mutable container shared with any input.
    Raises :class:`TypeError` if ``layers`` is not a list of dicts or if any
    key at any nesting level is not a string. Inputs are never mutated, even
    when validation fails.
    """
    _validate_layers(layers)
    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result