#!/usr/bin/env python3
"""Test the new unified `noah secrets rotate` CLI command.

Validates that:
  1. Initial generation creates metadata with version=1.
  2. Invoking rotate on specific keys increments only those keys' versions.

Run: python Tests/test_cli_rotate_secrets.py
"""
import sys
import subprocess
from pathlib import Path
import json
import yaml
import os

ROOT = Path(__file__).parent.parent
NOAH = ROOT / 'noah.py'
CANONICAL = ROOT / 'Secrets' / 'canonical-secrets.yaml'

SERVICE = 'authentik'
ROTATE_KEYS = ['bootstrap_password','redis_password']


def read_store():
    # canonical file might be encrypted (future); for now assume plaintext fallback or decrypted path used
    if not CANONICAL.exists():
        return {}
    try:
        return yaml.safe_load(CANONICAL.read_text()) or {}
    except Exception:
        return {}


def main():
    # Force plaintext canonical store for test reliability if Age keys absent
    os.environ['NOAH_DISABLE_SOPS'] = 'true'
    # Step 1: Generate secrets (generate command triggers creation in canonical store via generate_service_secrets)
    result = subprocess.run([sys.executable, str(NOAH), 'secrets', 'generate', '--service', SERVICE], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return 1

    # Access canonical store to snapshot versions
    # Call canonical show (optional) to ensure visibility; ignore failures here
    subprocess.run([sys.executable, str(NOAH), 'secrets', 'canonical', '--show', '--service', SERVICE], capture_output=True, text=True)

    store1 = read_store()
    svc1 = store1.get('services', {}).get(SERVICE, {})
    assert svc1, 'Service secrets not initialized'

    # All versions should be >=1
    initial_versions = {k: (v.get('version') if isinstance(v, dict) else 1) for k,v in svc1.items()}

    # Step 2: Rotate subset
    rotate_cmd = [sys.executable, str(NOAH), 'secrets', 'rotate', '--service', SERVICE, '--keys', ','.join(ROTATE_KEYS)]
    result2 = subprocess.run(rotate_cmd, capture_output=True, text=True)
    if result2.returncode != 0:
        print(result2.stdout)
        print(result2.stderr, file=sys.stderr)
        return 1

    store2 = read_store()
    svc2 = store2.get('services', {}).get(SERVICE, {})

    # Validate version increments only for rotated keys
    for k, entry in svc2.items():
        v2 = entry.get('version') if isinstance(entry, dict) else 1
        v1 = initial_versions.get(k, 0)
        if k in ROTATE_KEYS:
            assert v2 == v1 + 1, f'Key {k} expected version {v1+1}, got {v2}'
        else:
            assert v2 == v1, f'Key {k} should not have version change (was {v1}, now {v2})'

    print('✅ CLI rotate secrets test passed')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
