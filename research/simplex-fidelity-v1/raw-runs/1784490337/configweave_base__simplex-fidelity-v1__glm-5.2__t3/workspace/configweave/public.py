"""Public API for the configweave package.

``merge_layers`` applies a list of configuration "layers" (dicts) from first to
last, producing a single merged dict.  The implementation relies solely on the
Python standard library.
"""

import copy

__all__ = ["merge_layers"]


def merge_layers(layers):
    """Merge configuration layers from first to last.

    ``layers`` must be a list of dicts whose keys are strings at every nesting
    level.  Each layer is applied in order onto a fresh result dict:

    * when both the existing and the incoming value are dicts, they are merged
      recursively;
    * when the incoming value is a list, it replaces the existing value with a
      deep copy of that list;
    * when the incoming value is ``None``, the key is deleted from the result at
      its current nesting level (deleting an absent key is a no-op);
    * otherwise the incoming value replaces the existing value.

    The returned dict shares no mutable container with any input layer, and no
    input layer is ever mutated.

    Raises:
        TypeError: if ``layers`` is not a list, if any layer is not a dict, or if
            any key at any nesting level is not a string.
    """
    if not isinstance(layers, list):
        raise TypeError("layers must be a list of dicts")
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError(
                "each layer must be a dict, got %s" % type(layer).__name__
            )
        _validate(layer)

    result = {}
    for layer in layers:
        _apply(result, layer)
    return result


def _validate(node):
    """Recursively ensure every dict key anywhere in ``node`` is a string."""
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                raise TypeError(
                    "all keys must be strings, got %s" % type(key).__name__
                )
            _validate(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _validate(item)


def _apply(result, layer):
    """Apply ``layer`` onto ``result`` (which is owned by the caller)."""
    for key, value in layer.items():
        if value is None:
            # A later null value deletes the key at this nesting level.
            result.pop(key, None)
        elif isinstance(value, dict):
            existing = result.get(key)
            if isinstance(existing, dict):
                _apply(existing, value)
            else:
                child = {}
                _apply(child, value)
                result[key] = child
        else:
            # Lists are replaced with a deep copy (R4); other non-list values
            # simply replace the earlier value (R3).  deepcopy keeps the result
            # independent of every input layer (R6).
            result[key] = copy.deepcopy(value)