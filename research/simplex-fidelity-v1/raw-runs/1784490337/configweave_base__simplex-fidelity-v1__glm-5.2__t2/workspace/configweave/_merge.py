"""Core merge implementation for :mod:`configweave`.

Only the Python standard library is used (``copy``).  This module is part of
the ``configweave`` package itself, so importing from it counts as an internal
dependency.
"""

import copy


def _validate(value):
    """Recursively ensure every mapping key is a string.

    Descends into mappings and lists so that keys nested at any depth are
    checked.  This function only reads ``value``; it never mutates it.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "configweave: mapping keys must be str, got "
                    f"{type(key).__name__}: {key!r}"
                )
            _validate(child)
    elif isinstance(value, list):
        for child in value:
            _validate(child)


def _merge_into(target, layer):
    """Merge mapping ``layer`` into owned mapping ``target``.

    ``target`` is owned by the caller and may be mutated freely; ``layer`` is
    an input and is only ever read, never mutated.  Every value placed into
    ``target`` is a deep copy, so no mutable container is shared with any
    input.
    """
    for key, new_value in layer.items():
        if new_value is None:
            # R5: a later null value deletes the key (no-op if absent).
            target.pop(key, None)
        elif isinstance(new_value, list):
            # R4: a later list replaces the earlier value with a deep copy.
            target[key] = copy.deepcopy(new_value)
        elif isinstance(new_value, dict):
            old_value = target.get(key)
            if isinstance(old_value, dict):
                # R3: both old and new are mappings -> merge recursively.
                _merge_into(old_value, new_value)
            else:
                # R3: otherwise the later non-list value replaces the earlier.
                target[key] = copy.deepcopy(new_value)
        else:
            # R3: otherwise the later non-list value replaces the earlier.
            target[key] = copy.deepcopy(new_value)


def merge_layers(layers):
    """Merge configuration layers from first to last.

    ``layers`` must be a list of dicts whose keys (at every nesting level) are
    strings.  Layers are applied in order: each layer is merged on top of the
    accumulated result.

    Rules:

    * An empty layer list yields an empty dict.
    * When both the existing and incoming values are mappings, they are merged
      recursively.
    * When the incoming value is a list, it replaces the existing value with a
      deep copy of that list.
    * When the incoming value is ``None``, the key is deleted from the result
      at its current nesting level (deleting an absent key is a no-op).
    * Otherwise the incoming value replaces the existing value.
    * The returned dict shares no mutable container with any input, and no
      input layer is ever mutated.

    :param layers: list of dict layers to merge.
    :returns: a new dict containing the merged configuration.
    :raises TypeError: if ``layers`` is not a list of dicts or if any key at
        any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError(
            "configweave: layers must be a list of dicts, got "
            f"{type(layers).__name__}"
        )

    # Validate every layer up front so a TypeError is raised before any
    # merging work is performed (and therefore before any state changes).
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError(
                "configweave: each layer must be a dict, got "
                f"{type(layer).__name__}"
            )
        _validate(layer)

    result = {}
    for layer in layers:
        _merge_into(result, layer)
    return result