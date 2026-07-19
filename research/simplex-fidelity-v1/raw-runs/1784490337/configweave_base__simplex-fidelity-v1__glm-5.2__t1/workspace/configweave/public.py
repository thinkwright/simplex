"""Public API for the :mod:`configweave` package.

This module exposes :func:`merge_layers`, which merges a list of
configuration "layers" (dicts) from first to last into a single
configuration dict. Only the Python standard library is used.
"""

import copy


def merge_layers(layers):
    """Merge configuration layers from first to last.

    Each layer is a dict. Layers are applied in order: later layers take
    precedence over earlier ones according to the following rules:

    * When both the existing and the incoming value are mappings, they are
      merged recursively.
    * When the incoming value is a list, it replaces the existing value with
      a deep copy of that list.
    * When the incoming value is ``None``, the key is deleted from the result
      at its current nesting level (deleting an absent key is a no-op).
    * Otherwise the incoming (non-list) value replaces the existing value.

    The returned dict (and every mutable container within it) is independent
    of the inputs: no mutable container is shared with any input layer, and no
    input layer is ever mutated.

    Args:
        layers: A list of dicts. Every key at every nesting level must be a
            string.

    Returns:
        A new dict containing the merged configuration. An empty list of
        layers yields an empty dict.

    Raises:
        TypeError: If ``layers`` is not a list, if any layer is not a dict,
            or if any key at any nesting level is not a string.
    """
    _validate_layers(layers)
    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result


def _validate_layers(layers):
    """Validate that ``layers`` is a list of dicts with string-only keys."""
    if not isinstance(layers, list):
        raise TypeError("layers must be a list of dicts")
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError("each layer must be a dict")
        _validate_keys(layer)


def _validate_keys(value):
    """Recursively ensure every dict key is a string."""
    if isinstance(value, dict):
        for key, subvalue in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "every key at every nesting level must be a string"
                )
            _validate_keys(subvalue)
    elif isinstance(value, list):
        for item in value:
            _validate_keys(item)


def _merge_into(result, new_layer):
    """Merge ``new_layer`` into ``result`` in place (``result`` is owned)."""
    for key, new_value in new_layer.items():
        if new_value is None:
            # A later null value deletes the key at this nesting level.
            result.pop(key, None)
        elif isinstance(new_value, list):
            # A later list replaces the earlier value with a deep copy.
            result[key] = copy.deepcopy(new_value)
        elif isinstance(new_value, dict):
            existing = result.get(key)
            if isinstance(existing, dict):
                # Both old and new are mappings: merge recursively.
                _merge_into(existing, new_value)
            else:
                # Replace with a deep copy of the incoming mapping.
                result[key] = copy.deepcopy(new_value)
        else:
            # A later non-list value replaces the earlier value.
            result[key] = copy.deepcopy(new_value)