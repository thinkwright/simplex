"""Public API for configweave."""

import copy
from collections.abc import Mapping


def _validate_layer(layer):
    """Validate that a layer is a dict with only string keys (recursively)."""
    if not isinstance(layer, dict):
        raise TypeError(
            f"Each layer must be a dict, got {type(layer).__name__}"
        )
    _validate_keys(layer)


def _validate_keys(mapping):
    """Recursively validate that all keys in a mapping are strings."""
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                f"All keys must be strings, got {type(key).__name__}: {key!r}"
            )
        if isinstance(value, dict):
            _validate_keys(value)


def _deep_merge(base, override):
    """Merge *override* into a **new** dict built from *base*.

    Rules applied per key in *override*:
      - value is None  → delete the key from the result
      - both old and new are Mappings → recurse
      - new value is a list → deep-copy the list and replace
      - otherwise → replace with the new value
    """
    result = {}
    # Start with a deep copy of every key in base so nothing is shared.
    for k, v in base.items():
        result[k] = copy.deepcopy(v)

    for key, new_val in override.items():
        if new_val is None:
            # R5: null deletes the key (no-op if absent)
            result.pop(key, None)
        elif isinstance(new_val, Mapping) and isinstance(result.get(key), Mapping):
            # R3: both mappings → recursive merge
            result[key] = _deep_merge(result[key], new_val)
        elif isinstance(new_val, list):
            # R4: list → deep copy replaces
            result[key] = copy.deepcopy(new_val)
        else:
            # R3: later non-list value replaces
            result[key] = copy.deepcopy(new_val)

    return result


def merge_layers(layers):
    """Merge a sequence of configuration layer dicts.

    Parameters
    ----------
    layers : list[dict]
        Layer dicts applied from first to last.

    Returns
    -------
    dict
        The merged configuration.  An empty *layers* list yields ``{}``.

    Raises
    ------
    TypeError
        If *layers* is not a list, any layer is not a dict, or any key
        at any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )

    # R2: empty list → empty dict
    if not layers:
        return {}

    # R7 / X1: validate every layer up-front before any merging
    for layer in layers:
        _validate_layer(layer)

    result = {}
    for layer in layers:
        result = _deep_merge(result, layer)

    return result
