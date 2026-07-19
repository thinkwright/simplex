"""Core implementation of layered configuration merging.

This module depends only on the Python standard library.
"""

import copy


def merge_layers(layers):
    """Merge a list of configuration layer dicts into a single dict.

    Layers are applied from first to last. Later layers override, merge into,
    concatenate with, or delete values from earlier layers according to the
    rules of configweave.

    Args:
        layers: A list of dicts. Every key at every nesting level must be a
            string.

    Returns:
        A new dict that shares no mutable container with any input layer.

    Raises:
        TypeError: If ``layers`` is not a list, if any layer is not a dict, or
            if any key at any nesting level is not a string.
    """
    _validate_layers(layers)
    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result


def _merge_into(base, layer):
    """Apply ``layer`` onto ``base`` (the in-progress result).

    ``base`` is mutated freely because it is owned by the result; ``layer`` is
    only ever read, so input layers are never mutated.
    """
    for key, new_value in layer.items():
        if new_value is None:
            # A later null value deletes the key at its current nesting level.
            # Deleting an absent key is a no-op.
            base.pop(key, None)
        elif key in base:
            old_value = base[key]
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                # Both mappings: merge recursively.
                _merge_into(old_value, new_value)
            elif isinstance(old_value, list) and isinstance(new_value, list):
                # Both lists: concatenate deep copies in old-then-new order.
                base[key] = copy.deepcopy(old_value) + copy.deepcopy(new_value)
            else:
                # Otherwise the later value replaces the earlier one. A list
                # still replaces a non-list (and vice versa).
                base[key] = copy.deepcopy(new_value)
        else:
            base[key] = copy.deepcopy(new_value)


def _validate_layers(layers):
    """Validate that ``layers`` is a list of dicts with only string keys.

    Validation is performed fully before any merging happens, so an invalid
    input never results in a partially built result or a mutated input.
    """
    if not isinstance(layers, list):
        raise TypeError(
            "layers must be a list of dicts, got %s" % type(layers).__name__
        )
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                "each layer must be a dict, but layer %d is %s"
                % (index, type(layer).__name__)
            )
        _validate_value(layer)


def _validate_value(value):
    """Recursively validate that every dict key within ``value`` is a string."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "all keys must be strings, got a key of type %s"
                    % type(key).__name__
                )
            _validate_value(item)
    elif isinstance(value, list):
        for item in value:
            _validate_value(item)