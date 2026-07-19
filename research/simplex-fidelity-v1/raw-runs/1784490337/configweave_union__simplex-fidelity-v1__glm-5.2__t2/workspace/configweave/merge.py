"""Merge implementation for the configweave package.

Only the Python standard library is used here (``copy``).  The public
entry point is re-exported from :mod:`configweave.public`.
"""

import copy

__all__ = ["merge_layers"]


def merge_layers(layers):
    """Merge configuration layers from first to last.

    ``layers`` must be a list of dicts whose keys are strings at every
    nesting level.  Layers are applied in order with the following rules:

    * nested mappings merge recursively;
    * two lists concatenate in old-then-new order keeping only the first
      occurrence of each equality-distinct value;
    * any other later value replaces the earlier one (a list replaces a
      non-list and vice-versa);
    * a ``None`` value deletes the corresponding key (a no-op when the
      key is absent).

    The returned mapping is a deep copy that shares no mutable container
    with any input, and no input layer is ever mutated.

    Raises:
        TypeError: if ``layers`` is not a list of dicts or if any key at
            any nesting level is not a string.
    """
    _validate_layers(layers)
    result = {}
    for layer in layers:
        result = _merge_dicts(result, layer)
    return result


def _validate_layers(layers):
    if not isinstance(layers, list):
        raise TypeError("layers must be a list of dicts")
    for layer in layers:
        _validate_mapping(layer)


def _validate_mapping(value):
    if not isinstance(value, dict):
        raise TypeError(
            "each layer must be a dict, got %s" % type(value).__name__
        )
    for key, val in value.items():
        if not isinstance(key, str):
            raise TypeError("all keys must be strings, got %r" % (key,))
        _validate_value(val)


def _validate_value(value):
    if isinstance(value, dict):
        for key, val in value.items():
            if not isinstance(key, str):
                raise TypeError("all keys must be strings, got %r" % (key,))
            _validate_value(val)
    elif isinstance(value, list):
        for item in value:
            _validate_value(item)


def _merge_dicts(result, new):
    """Merge ``new`` (a layer dict) into ``result`` (a fresh dict)."""
    for key, new_value in new.items():
        if new_value is None:
            # A null value deletes the key at this nesting level.
            result.pop(key, None)
        elif key in result:
            old_value = result[key]
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                result[key] = _merge_dicts(old_value, new_value)
            elif isinstance(old_value, list) and isinstance(new_value, list):
                result[key] = _merge_lists(old_value, new_value)
            else:
                result[key] = _copy_value(new_value)
        else:
            result[key] = _copy_value(new_value)
    return result


def _merge_lists(old, new):
    """Concatenate ``old`` then ``new`` keeping the first occurrence only."""
    result = []
    for item in old:
        if item not in result:
            result.append(item)
    for item in new:
        copied = _copy_value(item)
        if copied not in result:
            result.append(copied)
    return result


def _copy_value(value):
    """Return a fresh, input-independent copy of ``value``.

    Dicts are processed through :func:`_merge_dicts` so that ``None``
    deletion directives are honoured at every nesting level; lists are
    copied element by element; everything else is deep-copied.
    """
    if isinstance(value, dict):
        return _merge_dicts({}, value)
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    return copy.deepcopy(value)