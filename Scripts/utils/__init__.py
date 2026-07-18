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
NOAH Scripts Utilities
Utility functions and helpers for NOAH configuration management
"""

from .config_utils import (
    show_configuration,
    show_domains,
    generate_helm_values,
    validate_service_configuration,
    get_service_fqdn,
    get_all_service_fqdns,
    override_service_configuration,
    export_all_helm_values,
    get_ingress_configuration,
    list_available_services,
    # Click command decorators
    config_show_command,
    config_domains_command,
    config_override_command
)

# Import modules for direct access
from . import config_loader
from . import ansible_runner

__all__ = [
    # Core utility functions
    'show_configuration',
    'show_domains',
    'generate_helm_values',
    'validate_service_configuration',
    'get_service_fqdn',
    'get_all_service_fqdns',
    'override_service_configuration',
    'export_all_helm_values',
    'get_ingress_configuration',
    'list_available_services',
    # Click command decorators
    'config_show_command',
    'config_domains_command',
    'config_override_command',
    # Modules
    'config_loader',
    'ansible_runner',
]