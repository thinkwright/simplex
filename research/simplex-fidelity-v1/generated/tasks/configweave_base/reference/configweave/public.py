from __future__ import annotations

from copy import deepcopy


MODE = "replace"


def _validate_mapping(value: dict) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError("configuration keys must be strings")
        if isinstance(item, dict):
            _validate_mapping(item)


def _stable_union(old: list, new: list) -> list:
    result = []
    for item in [*old, *new]:
        if not any(item == existing for existing in result):
            result.append(deepcopy(item))
    return result


def _merge(old: dict, new: dict) -> dict:
    result = deepcopy(old)
    for key, value in new.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            if MODE == "replace":
                result[key] = deepcopy(value)
            elif MODE == "concat":
                result[key] = deepcopy(result[key]) + deepcopy(value)
            else:
                result[key] = _stable_union(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def merge_layers(layers: list[dict]) -> dict:
    if not isinstance(layers, list):
        raise TypeError("layers must be a list")
    for layer in layers:
        if not isinstance(layer, dict):
            raise TypeError("each layer must be a dict")
        _validate_mapping(layer)
    result: dict = {}
    for layer in layers:
        result = _merge(result, layer)
    return result
