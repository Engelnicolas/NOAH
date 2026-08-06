#!/usr/bin/env python3
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

"""
Shared pytest fixtures.

The canonical store refuses to write in plaintext unless NOAH_ENVIRONMENT names
an unlocked environment, and defaults to locked so that a forgotten setting
fails closed. The suite relies on NOAH_DISABLE_SOPS throughout (17 occurrences
across three modules), so without this file every one of those tests would hit
the lock.

Declaring the environment once here keeps the lock itself untouched -- the
guard is on NOAH_ENVIRONMENT, never on forbidding NOAH_DISABLE_SOPS -- and
needs no change to any existing test.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.security import canonical_store  # noqa: E402


@pytest.fixture(autouse=True)
def _unlocked_environment(monkeypatch):
    """Run every test in an unlocked environment, with a fresh store singleton.

    The singleton reset generalises what test_security_manager.py and
    test_canonical_store.py already do individually, so a store built by one
    test cannot leak into the next.
    """
    monkeypatch.setenv("NOAH_ENVIRONMENT", "test")
    monkeypatch.setattr(canonical_store, "_store_instance", None, raising=False)
