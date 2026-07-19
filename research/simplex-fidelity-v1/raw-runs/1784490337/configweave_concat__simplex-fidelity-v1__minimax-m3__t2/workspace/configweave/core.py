"""Core implementation of configweave merging."""

import copy


def _is_mapping(value):
    return isinstance(value, dict)


def _is_list(value):
    return isinstance(value, list)


def _validate_key(key, context):
    if not isinstance(key, str):
        raise TypeError(
            "configweave: keys must be strings at {0!r} (got {1!r})".format(
                context, type(key).__name__
            )
        )


def _validate_layer(layer, context="<layer>"):
    if not isinstance(layer, dict):
        raise TypeError(
            "configweave: layers must be dicts at {0!r} (got {1!r})".format(
                context, type(layer).__name__
            )
        )
    for key in layer:
        _validate_key(key, context)
        _validate_nested(layer[key], "{0}[{1!r}]".format(context, key))


def _validate_nested(value, context):
    if _is_mapping(value):
        for key in value:
            _validate_key(key, context)
            _validate_nested(value[key], "{0}[{1!r}]".format(context, key))
    elif _is_list(value):
        for index, item in enumerate(value):
            _validate_nested(item, "{0}[{1}]".format(context, index))


def _merge_into(result, new_layer, context="<layer>"):
    for key, new_value in new_layer.items():
        _validate_key(key, context)
        if new_value is None:
            # R5: null deletes the key if present; no-op if absent.
            if key in result:
                del result[key]
            continue

        if key not in result:
            # Insert a deep copy so the result never shares mutable refs.
            result[key] = copy.deepcopy(new_value)
            continue

        old_value = result[key]
        if _is_mapping(old_value) and _is_mapping(new_value):
            _merge_into(old_value, new_value, "{0}[{1!r}]".format(context, key))
        elif _is_list(old_value) and _is_list(new_value):
            # R4: concatenate deep copies in old-then-new order.
            result[key] = copy.deepcopy(old_value) + copy.deepcopy(new_value)
        else:
            # R3: later non-list value replaces the earlier value.
            result[key] = copy.deepcopy(new_value)


def merge_layers(layers):
    """Merge a sequence of layer dicts from first to last.

    Returns an empty dict for an empty layer list. The returned mapping is a
    deep copy: mutating it cannot affect any input layer, and input layers are
    never mutated.
    """
    if not isinstance(layers, list):
        raise TypeError(
            "configweave: layers must be a list (got {0!r})".format(
                type(layers).__name__
            )
        )

    for index, layer in enumerate(layers):
        _validate_layer(layer, "layers[{0}]".format(index))

    result = {}
    for index, layer in enumerate(layers):
        _merge_into(result, layer, "layers[{0}]".format(index))
    return result