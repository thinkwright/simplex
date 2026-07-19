"""Core implementation of configweave merge_layers."""

from copy import deepcopy


def _is_mapping(value):
    return isinstance(value, dict)


def _validate_key(key, context):
    if not isinstance(key, str):
        raise TypeError(
            f"configweave: keys must be strings, got {type(key).__name__} "
            f"in {context}"
        )


def _validate_structure(value, context):
    """Recursively validate that every dict has only string keys.

    Raises TypeError on any violation. Does not mutate inputs.
    """
    if _is_mapping(value):
        for key in value:
            _validate_key(key, context)
            _validate_structure(value[key], f"{context}.{key}")


def _merge_into(target, source, context):
    """Merge source into target (mutates target). Returns target.

    `context` is used for error messages on invalid nested keys.
    """
    for key, new_value in source.items():
        _validate_key(key, context)

        if new_value is None:
            # R5: null deletes the key
            if key in target:
                del target[key]
            continue

        if key not in target:
            target[key] = deepcopy(new_value)
            continue

        old_value = target[key]

        if _is_mapping(old_value) and _is_mapping(new_value):
            # R3: both mappings -> recurse
            _merge_into(old_value, new_value, f"{context}.{key}")
            continue

        if isinstance(new_value, list):
            # R4: list replaces with deep copy
            target[key] = deepcopy(new_value)
            continue

        # R3: later non-list value replaces earlier
        target[key] = deepcopy(new_value)

    return target


def merge_layers(layers):
    """Merge a list of configuration layers from first to last.

    Returns a new dict that is a deep copy with no mutable container shared
    with any input. Inputs are never mutated.
    """
    if not isinstance(layers, list):
        raise TypeError(
            f"configweave: layers must be a list, got {type(layers).__name__}"
        )

    # Validate every layer and every nested key up front (X1: no mutation
    # before validation passes).
    for index, layer in enumerate(layers):
        if not _is_mapping(layer):
            raise TypeError(
                f"configweave: layers must be dicts, got "
                f"{type(layer).__name__} in layer index {index}"
            )
        _validate_structure(layer, f"layer index {index}")

    result = {}

    for index, layer in enumerate(layers):
        _merge_into(result, layer, f"layer index {index}")

    return result