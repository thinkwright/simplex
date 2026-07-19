"""Public API for the configweave package."""

import copy


def _validate_mapping(mapping, _path=""):
    """Recursively validate that *mapping* is a dict with only string keys
    and that every nested value that is a dict also satisfies the same
    constraint.  Raises ``TypeError`` on any violation.
    """
    if not isinstance(mapping, dict):
        raise TypeError(
            f"Expected a dict at {_path or 'top level'}, got {type(mapping).__name__}"
        )
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                f"Expected string key at {_path or 'top level'}, "
                f"got {type(key).__name__!r}: {key!r}"
            )
        child_path = f"{_path}.{key}" if _path else key
        if isinstance(value, dict):
            _validate_mapping(value, child_path)
        elif isinstance(value, list):
            _validate_list(value, child_path)


def _validate_list(lst, path):
    """Validate items inside a list that appears in a layer value."""
    for idx, item in enumerate(lst):
        item_path = f"{path}[{idx}]"
        if isinstance(item, dict):
            _validate_mapping(item, item_path)
        elif isinstance(item, list):
            _validate_list(item, item_path)


def _deep_merge(base, overlay):
    """Merge *overlay* into *base* following the configweave rules.

    Both *base* and *overlay* are already deep-copied so we may mutate *base*
    freely.
    """
    for key, new_val in overlay.items():
        # R5 – null deletes the key
        if new_val is None:
            base.pop(key, None)
            continue

        if key in base:
            old_val = base[key]

            # R3 – both mappings → recursive merge
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                _deep_merge(old_val, new_val)
                continue

            # R4 – both lists → concatenate (deep copies already made)
            if isinstance(old_val, list) and isinstance(new_val, list):
                base[key] = old_val + new_val
                continue

            # R3/R4 – otherwise later value replaces
            base[key] = new_val
        else:
            base[key] = new_val

    return base


def merge_layers(layers):
    """Merge a sequence of layer dicts from first to last.

    Parameters
    ----------
    layers : list[dict]
        An ordered list of configuration layers.  Every layer must be a
        ``dict`` and every key at every nesting level must be a string.

    Returns
    -------
    dict
        The merged configuration.  The result is a deep copy that shares
        no mutable container with any input layer.

    Raises
    ------
    TypeError
        If *layers* is not a list, if any layer is not a dict, or if any
        key at any nesting level is not a string.
    """
    # --- basic type check on the outer container ---
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )

    # R2 – empty list → empty dict
    if not layers:
        return {}

    # R7 / X1 – validate every layer before doing any work so that we
    # never mutate inputs on a validation failure.
    for idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                f"Layer {idx} must be a dict, got {type(layer).__name__}"
            )
        _validate_mapping(layer, f"layer[{idx}]")

    # R6 – deep-copy every layer so we never touch the originals.
    copied = [copy.deepcopy(layer) for layer in layers]

    result = copied[0]
    for overlay in copied[1:]:
        _deep_merge(result, overlay)

    return result
