"""Core layer-merging implementation for configweave.

This module depends only on the Python standard library.
"""

__all__ = ["merge_layers"]


def merge_layers(layers):
    """Merge configuration layers, applying them from first to last.

    ``layers`` must be a list of dicts. Each successive layer is applied on top
    of the accumulated result:

    * When both the existing and incoming values are mappings, they are merged
      recursively.
    * When both are lists, they are concatenated in old-then-new order keeping
      only the first occurrence of each equality-distinct value.
    * Otherwise the incoming value replaces the existing one (a list replaces a
      non-list, and a non-list replaces anything that is not merged).
    * An incoming ``None`` value deletes the key at its current nesting level;
      deleting an absent key is a no-op.

    The returned dict is a deep copy that shares no mutable container with any
    input layer, and no input layer is ever mutated.

    Args:
        layers: A list of dicts to merge.

    Returns:
        A new dict containing the merged configuration.

    Raises:
        TypeError: If ``layers`` is not a list, if any layer is not a dict, or
            if any key at any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            "layers must be a list of dicts, got %s" % type(layers).__name__
        )
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError(
                "each layer must be a dict, got %s" % type(layer).__name__
            )
    for layer in layers:
        _validate_keys(layer)

    result = {}
    for layer in layers:
        _apply_layer(result, layer)
    return result


def _validate_keys(value):
    """Recursively ensure every dict key at every nesting level is a string."""
    if isinstance(value, dict):
        for key, sub in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "every key must be a string, got %s" % type(key).__name__
                )
            _validate_keys(sub)
    elif isinstance(value, list):
        for item in value:
            _validate_keys(item)
    # Other types carry no keys and need no validation.


def _apply_layer(result, layer):
    """Apply a single layer onto ``result`` (which is owned by us)."""
    for key, new_value in layer.items():
        if new_value is None:
            # A later null deletes the key at this nesting level (no-op if absent).
            result.pop(key, None)
            continue
        if key in result:
            old_value = result[key]
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                _apply_layer(old_value, new_value)
                continue
            if isinstance(old_value, list) and isinstance(new_value, list):
                result[key] = _concat_dedupe(old_value, new_value)
                continue
        # Replacement: a list replaces a non-list; a non-list replaces anything
        # that is not merged. Always store a deep copy so inputs stay untouched.
        result[key] = _deep_copy(new_value)


def _concat_dedupe(old_list, new_list):
    """Concatenate two lists in old-then-new order, keeping first occurrences."""
    combined = []
    for item in list(old_list) + list(new_list):
        if item not in combined:
            combined.append(item)
    return [_deep_copy(item) for item in combined]


def _deep_copy(value):
    """Deep copy dicts and lists; return immutable scalars unchanged."""
    if isinstance(value, dict):
        return {k: _deep_copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    return value