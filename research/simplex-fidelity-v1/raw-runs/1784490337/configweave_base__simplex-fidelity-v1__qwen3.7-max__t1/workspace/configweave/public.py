"""Public API for the configweave package."""

import copy
from collections.abc import Mapping


def _validate_keys(obj):
    """Recursively validate that all mapping keys are strings."""
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"All keys must be strings, got {type(key).__name__}"
                )
            _validate_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            _validate_keys(item)


def _deep_merge(base, overlay):
    """Merge overlay into a new dict built from base.

    - Both mappings  → recurse
    - Overlay list   → replace (deep-copied later)
    - Overlay None   → delete key
    - Otherwise      → replace
    """
    result = dict(base)
    for key, value in overlay.items():
        if value is None:
            result.pop(key, None)
        elif (
            isinstance(value, Mapping)
            and key in result
            and isinstance(result[key], Mapping)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def merge_layers(layers):
    """Merge layer dicts from first to last and return a deep-copied result.

    Parameters
    ----------
    layers : list[dict]
        Ordered layer dictionaries.  Every key at every nesting level
        must be a string.

    Returns
    -------
    dict
        Merged configuration dictionary.  No mutable container is shared
        with any input layer.

    Raises
    ------
    TypeError
        If *layers* is not a list, any layer is not a dict, or any key
        is not a string.
    """
    # --- validation (before any merging so inputs are never mutated) ---
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )

    if not layers:
        return {}

    for idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                f"Layer {idx} must be a dict, got {type(layer).__name__}"
            )
        _validate_keys(layer)

    # --- merge first → last ---
    result = {}
    for layer in layers:
        result = _deep_merge(result, layer)

    # Deep-copy so no mutable container is shared with any input.
    return copy.deepcopy(result)
