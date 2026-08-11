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
Authentik credential and password rotation utilities.
Extracted from noah.py to reduce main CLI size and improve reuse.
"""
from __future__ import annotations

from typing import Any

# Module-level so the `except InsecureStoreError: raise` clauses below always
# resolve the name. Importing it inside the try blocks would leave it unbound
# if the import itself failed, masking that error with an UnboundLocalError.
from Scripts.security.canonical_store import InsecureStoreError

# Services exposing an admin login: (service, canonical store key, ingress
# subdomain, admin username, admin email local-part). Usernames are pinned by
# the manifests rather than the store: 'akadmin' by the Authentik chart,
# 'admin' by the nextcloud-app Secret and by STALWART_RECOVERY_ADMIN on the
# StatefulSet. Only Authentik seeds an admin email (bootstrap_email, rewritten
# to admin@<domain> by gitops_init); None means the account has no address.
_ADMIN_SERVICES: tuple[tuple[str, str, str, str, str | None], ...] = (
    ('authentik', 'bootstrap_password', 'auth', 'akadmin', 'admin'),
    ('nextcloud', 'admin_password', 'nextcloud', 'admin', None),
    ('stalwart', 'admin_password', 'mail', 'admin', None),
)


def _resolve_node_ip() -> tuple[str | None, str]:
    """Resolve the node IP fronting the cluster, with a resolution status.

    nginx-ingress binds the node's :80/:443 via hostPort (service is ClusterIP),
    so the external entry point is the node's IP (the EC2 EIP), not a
    LoadBalancer status. Prefer ExternalIP, fall back to InternalIP.
    """
    import subprocess  # local import to avoid global dependency cost
    try:
        for addr_type in ('ExternalIP', 'InternalIP'):
            kubectl_result = subprocess.run([
                'kubectl', 'get', 'nodes',
                '-o', f'jsonpath={{.items[0].status.addresses[?(@.type=="{addr_type}")].address}}'
            ], capture_output=True, text=True, timeout=8)
            if kubectl_result.returncode == 0 and kubectl_result.stdout.strip():
                return kubectl_result.stdout.strip().split()[0], 'ip_assigned'
        return None, 'pending'
    except Exception:  # noqa: BLE001
        return None, 'lookup_error'


def get_admin_credentials(domain: str | None = None) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Get admin credentials for every service exposing an admin login.

    Behavior:
    - Falls back to the domain recorded by `setup gitops` when none is given;
      every ingress is host-based, so an IP alone cannot reach a service.
    - Skips services whose password is absent from the store (not deployed).
    """
    try:
        from Scripts.security.canonical_store import get_canonical_store  # type: ignore
        store = get_canonical_store()
        services = store.data.get('services', {})
        domain = domain or store.get_cluster_domain()
        external_ip, resolution_status = _resolve_node_ip()

        credentials: list[dict[str, Any]] = []
        for service, store_key, subdomain, admin_username, email_local in _ADMIN_SERVICES:
            entry = services.get(service, {}).get(store_key)
            password = entry.get('value') if isinstance(entry, dict) else entry
            if not password:
                continue
            host = f"{subdomain}.{domain}" if domain else None
            credentials.append({
                'service': service,
                'http_url': f"http://{host}" if host else "(domain not recorded)",
                'https_url': f"https://{host}" if host else "(domain not recorded)",
                'admin_username': admin_username,
                'admin_email': f"{email_local}@{domain}" if email_local and domain else '',
                'admin_password': password,
                'external_ip': external_ip,
                'resolution_status': resolution_status
            })

        if not credentials:
            return None, "No admin passwords present in canonical store"
        return credentials, None
    except InsecureStoreError:
        # A refusal to write secrets in the clear must reach the operator, not
        # be flattened into an error string the caller may ignore.
        raise
    except Exception as e:  # noqa: BLE001
        return None, f"Error retrieving canonical credentials: {e}"


def get_authentik_credentials(domain: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """Get Authentik admin credentials from canonical secrets store.

    Behavior:
    - Prefer domain-based URLs when domain provided.
    - Returns resolution status for external IP retrieval.
    - Avoids misleading placeholder IPs.
    """
    try:
        from Scripts.security.canonical_store import get_canonical_store  # type: ignore
        store = get_canonical_store()
        svc = store.data.get('services', {}).get('authentik', {})
        entry = svc.get('bootstrap_password')
        password = entry.get('value') if isinstance(entry, dict) else entry
        if not password:
            return None, "Bootstrap password not present in canonical store"

        admin_email = ''
        admin_username = 'akadmin'

        external_ip, resolution_status = _resolve_node_ip()

        if domain:
            http_url = f"http://auth.{domain}"
            https_url = f"https://auth.{domain}"
        elif external_ip:
            http_url = f"http://{external_ip}"
            https_url = f"https://{external_ip}"
        else:
            http_url = "(external IP pending)"
            https_url = "(external IP pending)"

        return ({
            'http_url': http_url,
            'https_url': https_url,
            'admin_username': admin_username,
            'admin_email': admin_email,
            'admin_password': password,
            'external_ip': external_ip,
            'resolution_status': resolution_status
        }, None)
    except InsecureStoreError:
        raise
    except Exception as e:  # noqa: BLE001
        return None, f"Error retrieving canonical credentials: {e}"


def regenerate_authentik_password():
    """Generate a new Authentik admin password and update canonical store (increments version)."""
    try:
        from Scripts.security.canonical_store import get_canonical_store  # type: ignore
        from Scripts.security.security_manager import (
            NoahSecurityManager,  # type: ignore
        )
        sm = NoahSecurityManager()
        store = get_canonical_store()
        sm.generate_service_secrets('authentik')  # ensure base entries exist
        svc = store.data.get('services', {}).get('authentik', {})
        old_entry = svc.get('bootstrap_password')
        old_password = old_entry.get('value') if isinstance(old_entry, dict) else old_entry
        new_password = sm.generate_secure_password(24)
        from datetime import datetime, timezone
        svc['bootstrap_password'] = {
            'value': new_password,
            'version': (old_entry.get('version') if isinstance(old_entry, dict) else 1) + 1 if old_entry else 1,
            'rotated_at': datetime.now(timezone.utc).isoformat()
        }
        store.save()
        return ({
            'old_password': old_password,
            'new_password': new_password,
            'updated_file': str(store._active_path())
        }, None)
    except InsecureStoreError:
        raise
    except Exception as e:  # noqa: BLE001
        return None, f"Error regenerating canonical password: {e}"