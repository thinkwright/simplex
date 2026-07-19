"""Core implementation of configweave merge_layers."""

import copy


def _is_mapping(value):
    """Return True if value is a dict (mapping)."""
    return isinstance(value, dict)


def _validate_key(key, context):
    """Validate that a key is a string."""
    if not isinstance(key, str):
        raise TypeError(
            f"configweave: keys must be strings, got {type(key).__name__} "
            f"at {context}"
        )


def _validate_layer(layer, context="layer"):
    """Validate that a layer is a dict with string keys."""
    if not isinstance(layer, dict):
        raise TypeError(
            f"configweave: {context} must be a dict, got {type(layer).__name__}"
        )
    for key in layer:
        _validate_key(key, context)
        value = layer[key]
        if _is_mapping(value):
            _validate_layer(value, context=f"{context}[{key!r}]")


def merge_layers(layers):
    """Merge a list of configuration layers into a single dict.

    Layers are applied from first to last. Mappings are merged recursively;
    later non-list values replace earlier values; later list values replace
    earlier values with a deep copy; a later None deletes the key.

    Returns a deep copy with no mutable container shared with any input.
    Inputs are never mutated.
    """
    if not isinstance(layers, list):
        raise TypeError(
            f"configweave: layers must be a list, got {type(layers).__name__}"
        )

    for index, layer in enumerate(layers):
        _validate_layer(layer, context=f"layers[{index}]")

    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result


def _merge_into(result, layer):
    """Merge a single layer into result (in place on result copy)."""
    for key, new_value in layer.items():
        if new_value is None:
            # R5: later null deletes the key at current nesting level
            if key in result:
                del result[key]
            continue

        if key not in result:
            # No existing value: deep copy the new value
            result[key] = copy.deepcopy(new_value)
            continue

        old_value = result[key]
        old_is_mapping = _is_mapping(old_value)
        new_is_mapping = _is_mapping(new_value)

        if old_is_mapping and new_is_mapping:
            # R3: both mappings -> recursive merge
            _merge_into(old_value, new_value)
        elif isinstance(new_value, list):
            # R4: later list replaces earlier with deep copy
            result[key] = copy.deepcopy(new_value)
        else:
            # R3: later non-list value replaces earlier
            result[key] = copy.deepcopy(new_value)