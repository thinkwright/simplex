"""Public API for configweave."""

import copy
from collections.abc import Mapping


def _validate_keys_recursive(obj):
    """Recursively validate that every dict key in *obj* is a string.

    Raises TypeError on the first non-string key encountered.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"All keys must be strings, got {type(key).__name__!r}"
                )
            _validate_keys_recursive(value)
    elif isinstance(obj, list):
        for item in obj:
            _validate_keys_recursive(item)


def _validate_layers(layers):
    """Validate the *layers* argument before any merging begins.

    * layers must be a list
    * every element must be a dict
    * every dict key at every nesting level must be a string

    Raises TypeError on any violation.
    """
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__!r}"
        )
    for idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                f"Layer {idx} must be a dict, got {type(layer).__name__!r}"
            )
        _validate_keys_recursive(layer)


def _deep_merge(base, overlay):
    """Return a new dict that is the deep merge of *base* and *overlay*.

    Rules applied per key in *overlay*:
    * ``None`` value  → delete the key (no-op if absent).
    * Both values are Mappings → recurse.
    * Both values are lists   → concatenate deep-copied lists (old then new).
    * Otherwise               → overlay value (deep-copied) replaces base value.
    """
    result = copy.deepcopy(base)
    for key, new_val in overlay.items():
        if new_val is None:
            # R5: null deletes the key; no-op if absent
            result.pop(key, None)
            continue

        if key in result:
            old_val = result[key]
            if isinstance(old_val, Mapping) and isinstance(new_val, Mapping):
                # R3: recursive merge for mappings
                result[key] = _deep_merge(old_val, new_val)
            elif isinstance(old_val, list) and isinstance(new_val, list):
                # R4: concatenate deep copies, old-then-new
                result[key] = copy.deepcopy(old_val) + copy.deepcopy(new_val)
            else:
                # R3/R4: later non-list replaces earlier value;
                #         a list replaces a non-list
                result[key] = copy.deepcopy(new_val)
        else:
            result[key] = copy.deepcopy(new_val)

    return result


def merge_layers(layers):
    """Merge a list of layer dicts from first to last and return the result.

    Parameters
    ----------
    layers : list[dict]
        Configuration layers applied left-to-right.

    Returns
    -------
    dict
        The merged configuration.  An empty *layers* list yields ``{}``.

    Raises
    ------
    TypeError
        If *layers* is not a list, any element is not a dict, or any key
        at any nesting level is not a string.
    """
    # Validate everything before touching any data (X1: no mutation on error)
    _validate_layers(layers)

    # R2: empty layer list → empty dict
    result: dict = {}
    for layer in layers:
        result = _deep_merge(result, layer)

    return result
