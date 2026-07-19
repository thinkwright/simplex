"""Layer-merging implementation for configweave.

Only the Python standard library is used.
"""

from copy import deepcopy


def _is_mapping(value):
    """Return True if value is a dict (a mapping)."""
    return isinstance(value, dict)


def _is_list(value):
    """Return True if value is a list."""
    return isinstance(value, list)


def _validate_keys(mapping, path):
    """Recursively validate that every key in mapping is a string.

    Raises TypeError on the first non-string key found.
    """
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                "configweave: non-string key {!r} at path {!r}".format(key, path)
            )
        if _is_mapping(value):
            _validate_keys(value, path + [key])
        elif _is_list(value):
            _validate_list_keys(value, path + [key])


def _validate_list_keys(lst, path):
    """Validate keys inside any nested mappings within a list."""
    for item in lst:
        if _is_mapping(item):
            _validate_keys(item, path)
        elif _is_list(item):
            _validate_list_keys(item, path)


def _merge(old, new):
    """Merge two values according to configweave rules.

    Rules:
      - If both are mappings, merge recursively.
      - If both are lists, concatenate deep copies in old-then-new order.
      - If new is None, return the sentinel _DELETE to signal deletion.
      - Otherwise, the new value replaces the old value.
    """
    if new is None:
        return _DELETE

    if _is_mapping(old) and _is_mapping(new):
        return _merge_mappings(old, new)

    if _is_list(old) and _is_list(new):
        return deepcopy(old) + deepcopy(new)

    # Otherwise, the later value replaces the earlier value.
    return deepcopy(new)


def _merge_mappings(old, new):
    """Merge two mappings recursively, honoring deletion via None values."""
    result = {}
    # Start with deep copies of old keys.
    for key, value in old.items():
        result[key] = deepcopy(value)

    for key, value in new.items():
        if value is None:
            # Delete the key if present; no-op if absent.
            result.pop(key, None)
            continue
        if key in result:
            result[key] = _merge(result[key], value)
        else:
            # New key: deep copy so we don't share with the input.
            if _is_mapping(value):
                result[key] = _merge_mappings({}, value)
            elif _is_list(value):
                result[key] = deepcopy(value)
            else:
                result[key] = deepcopy(value)
    return result


# Sentinel used to signal "delete this key" during recursive merging.
_DELETE = object()


def merge_layers(layers):
    """Merge a list of configuration layers into a single dict.

    Layers are applied in order from first to last. An empty list returns
    an empty dict. The returned dict is a deep copy: mutating it cannot
    affect any input layer, and input layers are never mutated.

    Raises TypeError if `layers` is not a list of dicts or if any key at
    any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            "configweave: layers must be a list, got {!r}".format(type(layers).__name__)
        )

    for index, layer in enumerate(layers):
        if not _is_mapping(layer):
            raise TypeError(
                "configweave: layer at index {} is not a dict (got {!r})".format(
                    index, type(layer).__name__
                )
            )
        _validate_keys(layer, [])

    result = {}
    for layer in layers:
        result = _merge_mappings(result, layer)
    return result