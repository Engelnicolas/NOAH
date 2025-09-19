#!/usr/bin/env python3
"""Test canonical secrets store persistence and stability.

This is a lightweight test (no pytest dependency) to validate that:
  1. First generation of service secrets creates the canonical store.
  2. Subsequent generation returns identical values.
  3. Rotation API updates only targeted keys.

Run: python Tests/test_canonical_secrets.py
"""
import os
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from Scripts.security_manager import NoahSecurityManager  # type: ignore
from Scripts.security.canonical_store import get_canonical_store  # type: ignore

SERVICE = "authentik"

def main():
    store = get_canonical_store(ROOT)
    manager = NoahSecurityManager()

    print("[STEP] Generating initial secrets...")
    first = manager.generate_service_secrets(SERVICE)
    assert first, "Initial secret generation failed"

    print("[STEP] Regenerating secrets (should be identical)...")
    second = manager.generate_service_secrets(SERVICE)
    assert first == second, "Secrets changed between generations – canonical store not working"

    print("[STEP] Rotating a subset of secrets (bootstrap_password, redis_password)...")
    pre_rotate = second.copy()
    rotated = manager.rotate_service_secrets_canonical(SERVICE, ["bootstrap_password", "redis_password"])
    assert rotated["bootstrap_password"] != pre_rotate["bootstrap_password"], "bootstrap_password did not rotate"
    assert rotated["redis_password"] != pre_rotate["redis_password"], "redis_password did not rotate"
    # Unchanged key sanity check
    assert rotated["secret_key"] == pre_rotate["secret_key"], "secret_key should not have rotated"

    print("[STEP] Loading again to confirm persistence...")
    third = manager.generate_service_secrets(SERVICE)
    assert third == rotated, "Post-rotation retrieval mismatch"

    print("[STEP] Validating metadata (version, rotated_at)...")
    raw_store = store.data
    svc = raw_store.get('services', {}).get(SERVICE, {})
    # Ensure metadata objects exist
    for key, entry in svc.items():
        assert isinstance(entry, dict) and 'value' in entry, f"Secret {key} not wrapped with metadata"
        assert 'version' in entry and isinstance(entry['version'], int), f"Secret {key} missing integer version"
        assert 'rotated_at' in entry, f"Secret {key} missing rotated_at"
    # Rotated keys should have higher version than (at least) 1
    assert svc['bootstrap_password']['version'] > 1, "bootstrap_password version not incremented"
    assert svc['redis_password']['version'] > 1, "redis_password version not incremented"
    # Unchanged key remains at initial version (likely 1)
    assert svc['secret_key']['version'] == 1, "secret_key version should remain 1"

    print("✅ Canonical secrets store test passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
