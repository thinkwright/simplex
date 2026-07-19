"""Public API for the configweave package."""

import copy

# Sentinel used to signal key deletion during merging.
_SENTINEL_DELETE = object()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_mapping(mapping):
    """Recursively check that every key in *mapping* (and nested dicts/lists) is a str."""
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                f"All keys must be strings, got {type(key).__name__!r} ({key!r})"
            )
        _validate_value(value)


def _validate_value(value):
    """Validate nested structures inside a value."""
    if isinstance(value, dict):
        _validate_mapping(value)
    elif isinstance(value, list):
        for item in value:
            _validate_value(item)


def _validate_layer(layer):
    """A layer must be a dict; all keys at every depth must be strings."""
    if not isinstance(layer, dict):
        raise TypeError(
            f"Each layer must be a dict, got {type(layer).__name__!r}"
        )
    _validate_mapping(layer)


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _dedup_list(old_list, new_list):
    """Concatenate *old_list* then *new_list*, keeping only the first occurrence
    of each equality-distinct value.  All items are deep-copied."""
    result = []
    seen = []  # original references used for equality checks
    for item in old_list:
        result.append(copy.deepcopy(item))
        seen.append(item)
    for item in new_list:
        found = False
        for s in seen:
            try:
                eq = (s == item)
            except Exception:
                eq = False
            if eq:
                found = True
                break
        if not found:
            result.append(copy.deepcopy(item))
            seen.append(item)
    return result


def _merge_values(old, new):
    """Merge a single old value with a new value.

    Returns the merged value, or ``_SENTINEL_DELETE`` when the key should be
    removed.
    """
    # R5 – null deletes
    if new is None:
        return _SENTINEL_DELETE

    # R3 – both mappings → recursive merge
    if isinstance(old, dict) and isinstance(new, dict):
        return _merge_dicts(old, new)

    # R4 – both lists → concatenate with dedup
    if isinstance(old, list) and isinstance(new, list):
        return _dedup_list(old, new)

    # R3 / R4 – otherwise new replaces old (a list still replaces a non-list)
    return copy.deepcopy(new)


def _merge_dicts(old, new):
    """Return a new dict that is the recursive merge of *old* and *new*."""
    result = {}

    # Keys present in old
    for key in old:
        if key in new:
            merged = _merge_values(old[key], new[key])
            if merged is not _SENTINEL_DELETE:
                result[key] = merged
            # else: deleted – omit from result
        else:
            result[key] = copy.deepcopy(old[key])

    # Keys only in new
    for key in new:
        if key not in old:
            if new[key] is not None:
                result[key] = copy.deepcopy(new[key])
            # else: deleting an absent key is a no-op (R5)

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_layers(layers):
    """Merge a list of layer dicts from first to last and return the result.

    Parameters
    ----------
    layers : list[dict]
        An ordered sequence of configuration layers.  Every key at every
        nesting level must be a string.

    Returns
    -------
    dict
        The merged configuration.  An empty *layers* list yields ``{}``.

    Raises
    ------
    TypeError
        If *layers* is not a list, any layer is not a dict, or any key at
        any nesting level is not a string.
    """
    # --- validation (before any mutation / result construction) -----------
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__!r}"
        )
    for layer in layers:
        _validate_layer(layer)

    # --- merging ----------------------------------------------------------
    result = {}
    for layer in layers:
        result = _merge_dicts(result, layer)
    return result
