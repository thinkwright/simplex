"""Core implementation of configweave merge_layers.

Only the Python standard library is used.
"""

from copy import deepcopy


# Sentinel used to represent a "delete this key" marker. We use a unique
# object so it cannot collide with any user value (including None).
class _Delete:
    __slots__ = ()

    def __repr__(self):
        return "<DELETE>"


_DELETE = _Delete()


def merge_layers(layers):
    """Merge a list of configuration layers into a single dict.

    See the package docstring / contract for the full semantics. In short:
      - layers are applied from first to last
      - mappings merge recursively
      - lists concatenate with first-occurrence deduplication
      - a later None deletes the key at its current nesting level
      - the result is a deep copy; inputs are never mutated
      - all keys at every nesting level must be strings; layers must be a
        list of dicts; otherwise TypeError is raised
    """
    if not isinstance(layers, list):
        raise TypeError(
            "merge_layers expected a list of dicts, got {!r}".format(
                type(layers).__name__
            )
        )

    # Validate every layer up front so we fail before mutating anything.
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise TypeError(
                "layer at index {} is not a dict (got {!r})".format(
                    index, type(layer).__name__
                )
            )
        _validate_keys(layer, "layers[{}]".format(index))

    # Deep copy the first layer so we never share mutable containers with
    # any input, then merge subsequent layers into the copy.
    result = deepcopy(layers[0]) if layers else {}

    for layer in layers[1:]:
        # Deep copy the incoming layer so we never mutate it.
        _merge_into(result, deepcopy(layer))

    return result


def _validate_keys(value, path):
    """Recursively ensure every dict key at this node is a string."""
    if isinstance(value, dict):
        for key, sub in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "key at {} is not a string (got {!r})".format(
                        path, type(key).__name__
                    )
                )
            _validate_keys(sub, "{}[{!r}]".format(path, key))


def _merge_into(target, source):
    """Merge ``source`` into ``target`` in place.

    ``target`` and ``source`` are dicts. ``source`` may be freely mutated
    by this function (callers pass a deep copy).
    """
    for key, new_value in list(source.items()):
        if new_value is None:
            # R5: a later null deletes the key at its current nesting level.
            target.pop(key, None)
            continue

        if key not in target:
            target[key] = new_value
            continue

        old_value = target[key]

        if isinstance(old_value, dict) and isinstance(new_value, dict):
            # R3: both mappings -> recurse.
            _merge_into(old_value, new_value)
            continue

        if isinstance(old_value, list) and isinstance(new_value, list):
            # R4: both lists -> concatenate, first occurrence wins.
            target[key] = _merge_lists(old_value, new_value)
            continue

        # Otherwise the later non-list value replaces the earlier value.
        # Lists still replace non-lists (R4 last clause).
        target[key] = new_value


def _merge_lists(old_list, new_list):
    """Concatenate two lists keeping the first occurrence of each distinct
    value. Equality is determined by ``==`` (deep equality)."""
    seen = []
    seen_ids = set()  # track ids of items already kept, to avoid hashing
    result = []

    for item in list(old_list) + list(new_list):
        # Fast path: identity match means we've already kept this exact object.
        item_id = id(item)
        if item_id in seen_ids:
            continue
        # Slow path: deep equality against everything we've kept so far.
        already = False
        for kept in seen:
            if _equal(item, kept):
                already = True
                break
        if already:
            continue
        seen.append(item)
        seen_ids.add(item_id)
        result.append(item)

    return result


def _equal(a, b):
    """Deep equality that handles dicts, lists, and scalars without
    relying on ``hash`` (which would require items to be hashable)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        for key in a:
            if not _equal(a[key], b[key]):
                return False
        return True
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        for x, y in zip(a, b):
            if not _equal(x, y):
                return False
        return True
    # Scalars / other types: == works.
    return a == b