"""Public API for the configweave package."""

import copy


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_value(value):
    """Recursively ensure every dict key at every nesting level is a string."""
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"Non-string key {k!r} (type {type(k).__name__}) found in layer"
                )
            _validate_value(v)
    elif isinstance(value, list):
        for item in value:
            _validate_value(item)


def _validate_layers(layers):
    """Validate the top-level *layers* argument before any merging."""
    if not isinstance(layers, list):
        raise TypeError("layers must be a list")
    for idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                f"Layer at index {idx} is {type(layer).__name__}, expected dict"
            )
        _validate_value(layer)


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _merge_lists(old, new):
    """Concatenate *old* then *new*, keeping only the first occurrence of each
    equality-distinct value.  Items from *new* are deep-copied so the result
    shares no mutable container with the input layer."""
    result = []
    seen = []

    for item in old:
        if not any(item == s for s in seen):
            result.append(item)
            seen.append(item)

    for item in new:
        if not any(item == s for s in seen):
            item_copy = copy.deepcopy(item)
            result.append(item_copy)
            seen.append(item_copy)

    return result


def _merge_into(base, layer):
    """Merge *layer* into *base* (mutating *base*).  Values taken from *layer*
    are deep-copied so that the result is independent of the input."""
    for key, value in layer.items():
        if value is None:
            # R5 – null deletes the key (no-op if absent)
            base.pop(key, None)
        elif key in base:
            old_val = base[key]
            if isinstance(old_val, dict) and isinstance(value, dict):
                # R3 – both mappings → recursive merge
                _merge_into(old_val, value)
            elif isinstance(old_val, list) and isinstance(value, list):
                # R4 – both lists → concatenate with dedup
                base[key] = _merge_lists(old_val, value)
            else:
                # R3 / R4 – later value replaces earlier
                base[key] = copy.deepcopy(value)
        else:
            base[key] = copy.deepcopy(value)
    return base


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_layers(layers):
    """Merge a list of layer dicts from first to last and return the result.

    See the configweave specification for the full set of merge rules.
    """
    _validate_layers(layers)          # R7 / X1 – validate before touching anything

    result = {}                       # R2 – empty dict for empty list
    for layer in layers:
        _merge_into(result, layer)    # R2 – apply first to last

    return result
