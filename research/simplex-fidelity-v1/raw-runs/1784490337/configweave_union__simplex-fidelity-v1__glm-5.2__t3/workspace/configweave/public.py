"""Public API for the configweave package.

This module depends only on the Python standard library.
"""

import copy

__all__ = ["merge_layers"]


def _validate(value):
    """Recursively ensure every mapping key is a string.

    Raises :class:`TypeError` if any dict key is not a string.  The check
    descends into nested mappings and lists so that keys at every nesting
    level are validated.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "configweave requires every key to be a string; "
                    "found key {!r} of type {}".format(key, type(key).__name__)
                )
            _validate(item)
    elif isinstance(value, list):
        for item in value:
            _validate(item)


def _concat_lists(old_list, new_list):
    """Concatenate two lists keeping only the first equality-distinct value.

    The returned list contains deep copies so that no mutable container is
    shared with either input list.
    """
    result = []
    seen = []
    for item in list(old_list) + list(new_list):
        if item not in seen:
            seen.append(item)
            result.append(copy.deepcopy(item))
    return result


def _merge_into(base, layer):
    """Merge ``layer`` into ``base``.

    ``base`` is a dict owned by the caller and may be mutated freely.
    ``layer`` is only ever read; it is never mutated.
    """
    for key, new_value in layer.items():
        if new_value is None:
            # A later null deletes the key (no-op if absent).
            base.pop(key, None)
        elif (
            key in base
            and isinstance(base[key], dict)
            and isinstance(new_value, dict)
        ):
            # Both are mappings: merge recursively.
            _merge_into(base[key], new_value)
        elif (
            key in base
            and isinstance(base[key], list)
            and isinstance(new_value, list)
        ):
            # Both are lists: concatenate with first-occurrence dedup.
            base[key] = _concat_lists(base[key], new_value)
        else:
            # Otherwise the later value replaces the earlier one.
            base[key] = copy.deepcopy(new_value)


def merge_layers(layers):
    """Merge configuration ``layers`` from first to last.

    ``layers`` must be a list of dicts whose keys are strings at every
    nesting level.  Mappings are merged recursively, lists are concatenated
    with first-occurrence deduplication, a ``None`` value deletes its key,
    and any other later value replaces the earlier one.

    The returned dict is a deep copy: no mutable container in the result is
    shared with any input layer, and no input layer is ever mutated.

    Raises :class:`TypeError` if ``layers`` is not a list of dicts or if any
    key at any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError("layers must be a list of dicts")

    # Validate everything up front so inputs are never mutated on error.
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError("each layer must be a dict")
        _validate(layer)

    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result