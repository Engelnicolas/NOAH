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

"""Centralized path resolution utilities for NOAH.

Provides:
    get_noah_paths() -> dict[str, Path]
    NOAH_PATHS: cached dictionary of resolved paths

Environment Variables (with defaults):
    NOAH_ROOT_DIR
    NOAH_SCRIPTS_DIR (default: ./Scripts)
    NOAH_CERTIFICATES_DIR (default: ./Certificates)
    NOAH_AGE_DIR (default: ./Age)
    NOAH_VENV_DIR (default: ./.venv)
    ANSIBLE_PLAYBOOK_DIR (default: ./Ansible)
    HELM_CHART_DIR (default: ./Helm)
    SOPS_CONFIG_FILE (default: .sops.yaml)
    AGE_KEY_FILE (default: ./Age/keys.txt)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

__all__ = [
    'get_noah_paths',
    'NOAH_PATHS'
]

def get_noah_paths() -> Dict[str, Path]:
    """Resolve and return NOAH directory paths from environment variables.

    Each path falls back to a sane default relative to current working directory
    if the corresponding environment variable is not set.
    """
    return {
        'root_dir': Path(os.getenv('NOAH_ROOT_DIR', os.getcwd())),
        'scripts_dir': Path(os.getenv('NOAH_SCRIPTS_DIR', './Scripts')),
        'certificates_dir': Path(os.getenv('NOAH_CERTIFICATES_DIR', './Certificates')),
        'age_dir': Path(os.getenv('NOAH_AGE_DIR', './Age')),
        'venv_dir': Path(os.getenv('NOAH_VENV_DIR', './.venv')),
        'ansible_dir': Path(os.getenv('ANSIBLE_PLAYBOOK_DIR', './Ansible')),
        'helm_dir': Path(os.getenv('HELM_CHART_DIR', './Helm')),
        'sops_config': Path(os.getenv('SOPS_CONFIG_FILE', '.sops.yaml')),
        'age_key_file': Path(os.getenv('AGE_KEY_FILE', './Age/keys.txt'))
    }

# Cached paths dictionary used by callers that want a snapshot at import time.
NOAH_PATHS = get_noah_paths()
