"""Core implementation of configweave merge_layers.

Uses only the Python standard library.
"""

import copy


def _is_mapping(value):
    """Return True if value is a dict (the mapping type used for layers)."""
    return isinstance(value, dict)


def _validate_keys(mapping, path=()):
    """Recursively validate that every key at every nesting level is a string.

    Raises TypeError on the first non-string key encountered.
    """
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                "configweave: non-string key {!r} at path {}".format(key, list(path))
            )
        if _is_mapping(value):
            _validate_keys(value, path + (key,))


def _validate_layers(layers):
    """Validate that layers is a list of dicts with string keys throughout."""
    if not isinstance(layers, list):
        raise TypeError(
            "configweave: layers must be a list of dicts, got {}".format(type(layers).__name__)
        )
    for index, layer in enumerate(layers):
        if not _is_mapping(layer):
            raise TypeError(
                "configweave: layer at index {} is not a dict (got {})".format(
                    index, type(layer).__name__
                )
            )
        _validate_keys(layer)


def _merge(into, source):
    """Merge source into into (mutating into) following the rules.

    Preconditions: into and source are dicts with string keys.
    """
    for key, new_value in source.items():
        if new_value is None:
            # R5: a later null value deletes that key at its current nesting level.
            if key in into:
                del into[key]
            # Deleting an absent key is a no-op.
            continue

        if key not in into:
            old_value = None
        else:
            old_value = into[key]

        if _is_mapping(old_value) and _is_mapping(new_value):
            # R3: both mappings -> merge recursively.
            _merge(old_value, new_value)
        elif isinstance(new_value, list):
            # R4: later list value replaces earlier with a deep copy.
            into[key] = copy.deepcopy(new_value)
        else:
            # R3: later non-list value replaces earlier value.
            into[key] = copy.deepcopy(new_value)


def merge_layers(layers):
    """Merge a list of layer dicts from first to last.

    - Returns an empty dict for an empty layer list.
    - When both old and new values are mappings, merges recursively.
    - Otherwise the later non-list value replaces the earlier value.
    - When a later value is a list, the earlier value is replaced with a
      deep copy of that list.
    - A later null value deletes that key from the result at its current
      nesting level; deleting an absent key is a no-op.
    - The returned dict is a deep copy: no mutable container is shared with
      any input, and inputs are never mutated.

    Raises TypeError if layers is not a list of dicts or any key at any
    nesting level is not a string.
    """
    _validate_layers(layers)

    result = {}
    for layer in layers:
        # Each layer is a dict (validated). Merge into result without
        # mutating the layer itself.
        _merge(result, layer)
    return result