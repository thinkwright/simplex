"""Public API for configweave."""

import copy


def _validate_mapping(obj, top_level=False):
    """Validate that *obj* is a dict with only string keys (recursively).

    Raises TypeError on any violation.  When *top_level* is True the error
    message is tailored for a layer argument.
    """
    if not isinstance(obj, dict):
        if top_level:
            raise TypeError(
                f"Each layer must be a dict, got {type(obj).__name__}"
            )
        raise TypeError(
            f"Expected a mapping, got {type(obj).__name__}"
        )
    for key, value in obj.items():
        if not isinstance(key, str):
            raise TypeError(
                f"All keys must be strings, got {type(key).__name__}: {key!r}"
            )
        if isinstance(value, dict):
            _validate_mapping(value)
        elif isinstance(value, list):
            _validate_list(value)


def _validate_list(lst):
    """Validate nested values inside a list."""
    for item in lst:
        if isinstance(item, dict):
            _validate_mapping(item)
        elif isinstance(item, list):
            _validate_list(item)


def _deep_merge(base, overlay):
    """Recursively merge *overlay* into *base* (both already deep-copied).

    Rules applied per key:
    - Both values are dicts  → recurse
    - Both values are lists  → concatenate (deep copies)
    - overlay value is None  → delete key from base (no-op if absent)
    - otherwise              → overlay value replaces base value
    """
    for key, new_val in overlay.items():
        if new_val is None:
            # R5: null deletes the key
            base.pop(key, None)
            continue

        if key in base:
            old_val = base[key]
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                # R3: recursive merge for mappings
                _deep_merge(old_val, new_val)
                continue
            if isinstance(old_val, list) and isinstance(new_val, list):
                # R4: concatenate deep copies
                base[key] = old_val + copy.deepcopy(new_val)
                continue

        # R3 (non-mapping) / R4 (list replaces non-list) / general replace
        base[key] = copy.deepcopy(new_val)


def merge_layers(layers):
    """Merge a sequence of configuration layer dicts.

    Parameters
    ----------
    layers : list[dict]
        Layer dicts applied from first to last.  Every key at every nesting
        level must be a string.

    Returns
    -------
    dict
        The merged result (a deep copy sharing no mutable containers with
        any input).

    Raises
    ------
    TypeError
        If *layers* is not a list, any layer is not a dict, or any key at
        any nesting level is not a string.
    """
    # --- input validation ---------------------------------------------------
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )

    for idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                f"Each layer must be a dict, got {type(layer).__name__} "
                f"at index {idx}"
            )
        _validate_mapping(layer)

    # --- merge --------------------------------------------------------------
    result: dict = {}
    for layer in layers:
        layer_copy = copy.deepcopy(layer)
        _deep_merge(result, layer_copy)

    return result
