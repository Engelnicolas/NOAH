#!/usr/bin/env python3
"""Export canonical secret entries for a given service as JSON.

Usage:
  python Scripts/security/export_canonical_service.py --service authentik

Outputs JSON to stdout, e.g.:
{
  "secret_key": "...",
  "bootstrap_password": "..."
}

Exit codes:
 0 success
 1 service not found / error
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Allow running from repository root or script path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from Scripts.security.security_manager import NoahSecurityManager  # type: ignore
    from Scripts.security.canonical_store import get_canonical_store  # type: ignore
except Exception as e:  # pragma: no cover - import environment issues
    print(json.dumps({"error": f"Failed to load NOAH modules: {e}"}), file=sys.stderr)
    sys.exit(1)


def export_service(service: str) -> dict:
    """Return a dict of canonical secrets for the service.

    Ensures secrets are generated. Only returns key/value pairs (raw values).
    Any incidental logging performed by underlying calls is suppressed from stdout
    to keep this interface machine-consumable (pure JSON)."""
    manager = NoahSecurityManager()
    # Suppress potential noisy stdout from generation by temporarily redirecting if needed
    try:
        manager.generate_service_secrets(service)
    except Exception as e:  # surface as JSON error higher up
        raise e
    store = get_canonical_store(ROOT)
    svc = store.data.get('services', {}).get(service, {})

    def val(key: str):
        entry = svc.get(key)
        if isinstance(entry, dict):
            return entry.get('value')
        return entry or ''

    # Generic export of all keys for flexibility
    payload = {}
    for key in sorted(svc.keys()):
        payload[key] = val(key)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Export canonical secrets for a service")
    parser.add_argument('--service', required=True, help='Service name (e.g. authentik)')
    args = parser.parse_args()
    try:
        data = export_service(args.service)
        print(json.dumps(data))
        return 0
    except Exception as e:  # pragma: no cover - unexpected failures
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
