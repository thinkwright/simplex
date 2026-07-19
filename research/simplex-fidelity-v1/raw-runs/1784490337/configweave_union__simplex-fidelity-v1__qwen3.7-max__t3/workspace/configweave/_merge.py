"""Internal merge logic for configweave."""

import copy


def _validate_dict(d):
    """Recursively validate that d is a dict with all string keys."""
    if not isinstance(d, dict):
        raise TypeError(f"Expected dict, got {type(d).__name__}")
    for key, value in d.items():
        if not isinstance(key, str):
            raise TypeError(
                f"All keys must be strings, got {type(key).__name__}"
            )
        _validate_value(value)


def _validate_value(value):
    """Validate nested values recursively."""
    if isinstance(value, dict):
        _validate_dict(value)
    elif isinstance(value, list):
        for item in value:
            _validate_value(item)


def _dedup_list(old_list, new_list):
    """Concatenate old then new, keeping only first occurrence of each
    equality-distinct value."""
    result = []
    for item in list(old_list) + list(new_list):
        found = False
        for existing in result:
            try:
                if existing == item:
                    found = True
                    break
            except Exception:
                # If comparison raises, treat as distinct
                pass
        if not found:
            result.append(item)
    return result


def _merge_dicts(old, new):
    """Merge new dict into old dict, returning a new dict."""
    result = {}
    for k, v in old.items():
        result[k] = v
    for key, new_val in new.items():
        if new_val is None:
            # R5: null deletes the key
            result.pop(key, None)
        elif key in result:
            old_val = result[key]
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                # R3: both mappings → recursive merge
                result[key] = _merge_dicts(old_val, new_val)
            elif isinstance(old_val, list) and isinstance(new_val, list):
                # R4: both lists → concat with dedup
                result[key] = _dedup_list(old_val, new_val)
            else:
                # R3/R4: otherwise later value replaces
                result[key] = new_val
        else:
            result[key] = new_val
    return result


def merge_layers(layers):
    """Merge layer dicts from first to last and return the result.

    Parameters
    ----------
    layers : list[dict]
        A list of layer dictionaries to merge in order.

    Returns
    -------
    dict
        The merged configuration dictionary.

    Raises
    ------
    TypeError
        If layers is not a list, any layer is not a dict, or any key
        at any nesting level is not a string.
    """
    # R7: layers must be a list
    if not isinstance(layers, list):
        raise TypeError(
            f"layers must be a list, got {type(layers).__name__}"
        )

    # R7/X1: validate all layers before any processing
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError(
                f"Each layer must be a dict, got {type(layer).__name__}"
            )
        _validate_dict(layer)

    # R2: empty layer list → empty dict
    if not layers:
        return {}

    # R6: deep copy all layers to never mutate inputs and ensure
    # no mutable container is shared with any input
    copied = [copy.deepcopy(layer) for layer in layers]

    result = copied[0]
    for layer in copied[1:]:
        result = _merge_dicts(result, layer)

    return result
