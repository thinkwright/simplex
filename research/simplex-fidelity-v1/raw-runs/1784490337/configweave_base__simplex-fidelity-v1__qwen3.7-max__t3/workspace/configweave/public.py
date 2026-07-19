"""Public API for configweave."""

import copy


def _validate_keys(obj):
    """Recursively validate that every dict key is a string."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"All keys must be strings, got {type(key).__name__}: {key!r}"
                )
            _validate_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            _validate_keys(item)


def _validate_layers(layers):
    """Validate layer structure: list of dicts, all keys strings."""
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                f"Each layer must be a dict, got {type(layer).__name__} "
                f"at index {i}"
            )
        _validate_keys(layer)


def _merge(base, overlay):
    """Merge *overlay* into *base*, returning a new dict.

    Rules applied per key in overlay:
      - None  → delete the key from the result (R5)
      - dict + dict → recurse (R3)
      - list  → deep-copy replace (R4)
      - else  → plain replace (R3)
    """
    result = dict(base)
    for key, new_val in overlay.items():
        if new_val is None:
            # R5: null deletes the key; absent key is a no-op
            result.pop(key, None)
        elif isinstance(new_val, dict) and isinstance(result.get(key), dict):
            # R3: both mappings → recursive merge
            result[key] = _merge(result[key], new_val)
        elif isinstance(new_val, list):
            # R4: list → deep copy
            result[key] = copy.deepcopy(new_val)
        else:
            # R3: later value replaces
            result[key] = new_val
    return result


def merge_layers(layers):
    """Merge a list of layer dicts from first to last.

    Parameters
    ----------
    layers : list[dict]
        Ordered configuration layers.

    Returns
    -------
    dict
        Merged configuration (deep copy, no shared mutable state).

    Raises
    ------
    TypeError
        If *layers* is not a list of dicts or any key is not a string.
    """
    # R7 / X1: validate everything before touching data
    _validate_layers(layers)

    # R2: empty list → empty dict
    if not layers:
        return {}

    # R2: apply layers first-to-last
    result = {}
    for layer in layers:
        result = _merge(result, layer)

    # R6: return a deep copy so no mutable container is shared
    return copy.deepcopy(result)
