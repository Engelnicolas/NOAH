# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH - Network Operations & Automation Hub
# Copyright (C) 2026 Nicolas Engel <contact@nicolasengel.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Dictionary utility helpers for NOAH.

Currently provides:
    flatten_mapping(data, parent_key='', sep='_') -> dict

Used for converting nested configuration structures to flat environment style key maps.
"""
from __future__ import annotations

from typing import Any

__all__ = ["flatten_mapping"]

def flatten_mapping(data: dict[str, Any], parent_key: str = '', sep: str = '_') -> dict[str, str]:
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
