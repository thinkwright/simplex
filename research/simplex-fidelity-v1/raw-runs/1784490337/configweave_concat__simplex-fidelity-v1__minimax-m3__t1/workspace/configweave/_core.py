"""Core implementation of configweave merging.

Only the Python standard library is used.
"""

import copy


def _is_mapping(value):
    return isinstance(value, dict)


def _is_list(value):
    return isinstance(value, list)


def _validate_keys(value, path):
    """Recursively validate that every key at every nesting level is a string."""
    if _is_mapping(value):
        for key, sub in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "configweave: non-string key {!r} at path {!r}".format(key, path)
                )
            _validate_keys(sub, path + [key])
    elif _is_list(value):
        for index, item in enumerate(value):
            _validate_keys(item, path + ["[{}]".format(index)])


def _validate_layers(layers):
    if not isinstance(layers, list):
        raise TypeError(
            "configweave: layers must be a list of dicts, got {!r}".format(
                type(layers).__name__
            )
        )
    for index, layer in enumerate(layers):
        if not _is_mapping(layer):
            raise TypeError(
                "configweave: layer at index {} is not a dict (got {!r})".format(
                    index, type(layer).__name__
                )
            )
        _validate_keys(layer, ["layers[{}]".format(index)])


def _merge(old, new):
    """Merge two values according to the configweave rules.

    Returns a deep-copied result. Inputs are never mutated.
    """
    if new is None:
        # R5: a later null deletes the key at the current level.
        # Returning a sentinel via a wrapper is not possible here; the caller
        # handles deletion. We signal deletion with a unique object.
        return _DELETED

    if _is_mapping(old) and _is_mapping(new):
        result = {}
        # Start with a deep copy of old's keys.
        for key, value in old.items():
            result[key] = copy.deepcopy(value)
        for key, value in new.items():
            if value is None:
                # Delete the key if present.
                if key in result:
                    del result[key]
                continue
            if key in result:
                merged = _merge(result[key], value)
                if merged is _DELETED:
                    del result[key]
                else:
                    result[key] = merged
            else:
                # New key not in old.
                if _is_mapping(value):
                    result[key] = _merge({}, value)
                elif _is_list(value):
                    result[key] = copy.deepcopy(value)
                else:
                    result[key] = copy.deepcopy(value)
        return result

    if _is_list(old) and _is_list(new):
        # R4: concatenate deep copies in old-then-new order.
        return copy.deepcopy(old) + copy.deepcopy(new)

    # R3: later non-list value replaces earlier value.
    # R4: a list still replaces a non-list (handled by falling through here).
    return copy.deepcopy(new)


class _DeletedSentinel:
    def __repr__(self):
        return "<DELETED>"


_DELETED = _DeletedSentinel()


def merge_layers(layers):
    """Merge a list of layer dicts from first to last.

    Returns a new dict that is a deep copy of the merged result. Inputs are
    never mutated. See the package docstring / contract for full rules.
    """
    _validate_layers(layers)

    result = {}
    for layer in layers:
        # Deep copy the layer so we never share mutable containers with input.
        layer_copy = copy.deepcopy(layer)
        # Validate keys again on the copy to be safe (already validated above).
        for key, value in layer_copy.items():
            if value is None:
                if key in result:
                    del result[key]
                continue
            if key in result:
                merged = _merge(result[key], value)
                if merged is _DELETED:
                    del result[key]
                else:
                    result[key] = merged
            else:
                if _is_mapping(value):
                    result[key] = _merge({}, value)
                elif _is_list(value):
                    result[key] = copy.deepcopy(value)
                else:
                    result[key] = copy.deepcopy(value)
    return result