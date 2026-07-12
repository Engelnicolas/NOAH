#!/usr/bin/env python3
"""
Authentik credential and password rotation utilities.
Extracted from noah.py to reduce main CLI size and improve reuse.
"""
from __future__ import annotations

from typing import Optional, Any


def get_authentik_credentials(domain: str | None = None) -> tuple[Optional[dict[str, Any]], Optional[str]]:
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

        # nginx-ingress binds the node's :80/:443 via hostPort (service is ClusterIP),
        # so the external entry point is the node's IP (the EC2 EIP), not a
        # LoadBalancer status. Prefer ExternalIP, fall back to InternalIP.
        external_ip = None
        resolution_status = 'not_attempted'
        import subprocess  # local import to avoid global dependency cost
        try:
            for addr_type in ('ExternalIP', 'InternalIP'):
                kubectl_result = subprocess.run([
                    'kubectl', 'get', 'nodes',
                    '-o', f'jsonpath={{.items[0].status.addresses[?(@.type=="{addr_type}")].address}}'
                ], capture_output=True, text=True, timeout=8)
                if kubectl_result.returncode == 0 and kubectl_result.stdout.strip():
                    external_ip = kubectl_result.stdout.strip().split()[0]
                    resolution_status = 'ip_assigned'
                    break
            else:
                resolution_status = 'pending'
        except Exception:
            resolution_status = 'lookup_error'

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
    except Exception as e:  # noqa: BLE001
        return None, f"Error retrieving canonical credentials: {e}"


def regenerate_authentik_password():
    """Generate a new Authentik admin password and update canonical store (increments version)."""
    try:
        from Scripts.security.security_manager import NoahSecurityManager  # type: ignore
        from Scripts.security.canonical_store import get_canonical_store  # type: ignore
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
    except Exception as e:  # noqa: BLE001
        return None, f"Error regenerating canonical password: {e}"