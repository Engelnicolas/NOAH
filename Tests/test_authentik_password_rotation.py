#!/usr/bin/env python3
"""Test regeneration of Authentik admin password via canonical store.

Validates:
  1. Initial generation creates a bootstrap_password with version >=1.
  2. Regeneration increments version and changes value.
  3. Metadata (rotated_at) updates.
Run: python Tests/test_authentik_password_rotation.py
"""
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from Scripts.security_manager import NoahSecurityManager  # type: ignore
from Scripts.security.canonical_store import get_canonical_store  # type: ignore
from noah import regenerate_authentik_password  # type: ignore

SERVICE = 'authentik'

def main():
    store = get_canonical_store(ROOT)
    manager = NoahSecurityManager()

    print('[STEP] Ensuring initial service secrets exist...')
    manager.generate_service_secrets(SERVICE)
    svc = store.data.get('services', {}).get(SERVICE, {})
    entry = svc.get('bootstrap_password')
    assert entry, 'bootstrap_password missing after generation'
    if isinstance(entry, dict):
        initial_value = entry['value']
        initial_version = entry['version']
        initial_rotated_at = entry['rotated_at']
    else:
        # Legacy shape should not normally occur, but support in test
        initial_value = entry
        initial_version = 1
        initial_rotated_at = ''

    print('[STEP] Regenerating Authentik admin password...')
    result, error = regenerate_authentik_password()
    assert error is None, f'Regeneration error: {error}'
    assert result['new_password'] != result.get('old_password'), 'Password value did not change'

    store2 = get_canonical_store(ROOT)
    svc2 = store2.data.get('services', {}).get(SERVICE, {})
    new_entry = svc2.get('bootstrap_password')
    assert isinstance(new_entry, dict), 'New entry missing metadata wrapper'
    assert new_entry['value'] != initial_value, 'Canonical value not updated'
    assert new_entry['version'] == initial_version + 1 or (initial_version == 1 and new_entry['version'] >= 2), 'Version not incremented'
    assert new_entry['rotated_at'] != initial_rotated_at, 'rotated_at timestamp not updated'

    # Basic rotated_at ISO format sanity
    try:
        datetime.fromisoformat(new_entry['rotated_at'].rstrip('Z'))
    except Exception as e:
        raise AssertionError(f'rotated_at not ISO8601: {e}')

    print('✅ Authentik password rotation test passed')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
