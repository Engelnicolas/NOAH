"""Dictionary utility helpers for NOAH.

Currently provides:
    flatten_mapping(data, parent_key='', sep='_') -> dict

Used for converting nested configuration structures to flat environment style key maps.
"""
from __future__ import annotations
from typing import Any, Dict

__all__ = ["flatten_mapping"]

def flatten_mapping(data: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, str]:
    """Flatten a nested mapping into a single-level dict.

    Nested keys are concatenated using the provided separator and uppercased.
    Non-dict leaf values are coerced to strings.
    """
    items: list[tuple[str, str]] = []
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_mapping(value, new_key.upper(), sep).items())
        else:
            items.append((new_key.upper(), str(value)))
    return dict(items)
