#!/usr/bin/env python3
"""Canonical Secrets Store

Purpose:
  Provide a single, canonical source-of-truth for NOAH service secrets.
  This eliminates drift between:
    - Generated plaintext Kubernetes secret YAML
    - SOPS encrypted Helm secrets files
    - Post-deployment synchronization patches

Design:
  * One encrypted file: Secrets/canonical-secrets.enc.yaml (SOPS Age encrypted)
  * Structure:
      version: 1
      generated_at: <iso timestamp>
      services:
        authentik:
          secret_key: <>
          bootstrap_password: <>
          ...
        cilium:
          hubble_tls_key: <>
  * Access pattern:
      - load_canonical_store(): returns dict (may be empty if file missing)
      - ensure_service_entries(service, required_keys, generator_fn)
          * Fills missing keys using generator_fn(key_name) and persists
      - save_canonical_store()

  * If SOPS/Age not available OR NOAH_DISABLE_SOPS=true -> store plaintext at Secrets/canonical-secrets.yaml
    (still canonical but unencrypted; user warned)

Responsibilities:
  This module ONLY concerns loading/saving canonical secret data.
  It does NOT perform password policy logic (delegated to NoahSecurityManager)
  It does NOT format data into Helm or Kubernetes resource structures.

Extensibility:
  - Future: add per-key metadata (rotated_at, hash, source)
  - Future: add integrity hash over entire document

"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Callable, Optional, Any
import os
import subprocess
import yaml
import hashlib
from datetime import datetime, timezone

CANONICAL_FILENAME_ENCRYPTED = "canonical-secrets.enc.yaml"
CANONICAL_FILENAME_PLAINTEXT = "canonical-secrets.yaml"

# Schema versions:
# v1: { version:1, services: { svc: { key: raw_value } } }
# v2: { version:2, services: { svc: { key: { value: str, version: int, rotated_at: iso } } } }
CURRENT_SCHEMA_VERSION = 2

@dataclass
class CanonicalSecretsStore:
    project_root: Path = field(default_factory=lambda: Path.cwd())
    secrets_dir: Path = field(init=False)
    age_key_file: Path = field(init=False)
    encrypted: bool = field(init=False)
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.secrets_dir = self.project_root / "Secrets"
        self.secrets_dir.mkdir(exist_ok=True)
        self.age_key_file = self.project_root / "Age" / "keys.txt"
        self.encrypted = self._should_encrypt()
        self._load()

    # ---------------- Internal Helpers ----------------
    def _should_encrypt(self) -> bool:
        if os.environ.get("NOAH_DISABLE_SOPS", "false").lower() in ("1", "true", "yes"):  # explicit opt-out
            return False
        if not self.age_key_file.exists():
            return False
        # Check sops availability
        try:
            result = subprocess.run(["sops", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _encrypted_path(self) -> Path:
        return self.secrets_dir / CANONICAL_FILENAME_ENCRYPTED

    def _plaintext_path(self) -> Path:
        return self.secrets_dir / CANONICAL_FILENAME_PLAINTEXT

    def _active_path(self) -> Path:
        return self._encrypted_path() if self.encrypted else self._plaintext_path()

    def _decrypt_file(self, path: Path) -> Optional[str]:
        if not path.exists():
            return None
        if not self.encrypted:
            return path.read_text(encoding="utf-8")
        env = {**os.environ, "SOPS_AGE_KEY_FILE": str(self.age_key_file)}
        result = subprocess.run(["sops", "-d", str(path)], capture_output=True, text=True, env=env, check=False)
        if result.returncode != 0:
            # Stale recipient or corrupt file — remove it so the next save recreates it with the current key
            print(f"[WARNING] Canonical secrets unreadable (stale key or corrupt), resetting: {path.name}")
            path.unlink(missing_ok=True)
            return None
        return result.stdout

    def _compute_integrity(self) -> str:
        """Compute SHA256 integrity hash over sorted service secrets.

        Format: For each service (sorted), for each key (sorted), append
          f"{service}:{key}={value}\n" then hash the full concatenated string.
        """
        services = self.data.get("services", {}) if isinstance(self.data, dict) else {}
        lines = []
        for service in sorted(services.keys()):
            secrets_map = services.get(service, {}) or {}
            for key in sorted(secrets_map.keys()):
                entry = secrets_map[key]
                # Support both legacy string and v2 dict
                if isinstance(entry, dict):
                    val = entry.get('value')
                else:
                    val = entry
                if val is None:
                    continue
                lines.append(f"{service}:{key}={val}")
        payload = "\n".join(lines).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _verify_integrity(self):
        expected = self.data.get("integrity")
        if not expected:
            # First time or legacy file; compute and set
            self.data["integrity"] = self._compute_integrity()
            return True
        actual = self._compute_integrity()
        if expected != actual:
            print("[ERROR] Canonical secrets integrity mismatch! Recomputing and continuing (possible external modification).")
            self.data["integrity"] = actual
            return False
        return True

    def _load(self):
        raw = self._decrypt_file(self._active_path())
        if raw:
            try:
                self.data = yaml.safe_load(raw) or {}
            except Exception as e:
                print(f"[WARNING] Failed to parse canonical secrets: {e}")
                self.data = {}
        if not self.data:
            self.data = {"version": CURRENT_SCHEMA_VERSION, "services": {}, "generated_at": datetime.now(timezone.utc).isoformat()}
        # Upgrade schema if needed
        self._upgrade_schema_if_needed()
        # Integrity check / initialization
        self._verify_integrity()

    def _encrypt_in_place(self, path: Path) -> bool:
        if not self.encrypted:
            return True
        env = {**os.environ, "SOPS_AGE_KEY_FILE": str(self.age_key_file)}
        result = subprocess.run(["sops", "-e", "--in-place", str(path)], capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(f"[ERROR] Failed to encrypt canonical secrets: {result.stderr.strip()}")
            return False
        return True

    # ---------------- Public API ----------------
    def save(self) -> bool:
        path = self._active_path()
        # If switching encryption mode, remove previous variant to prevent confusion
        try:
            other = self._plaintext_path() if self.encrypted else self._encrypted_path()
            if other.exists():
                other.unlink()
        except Exception:
            pass

        # Refresh integrity before persisting
        self.data["integrity"] = self._compute_integrity()
        yaml_str = yaml.dump(self.data, default_flow_style=False, sort_keys=False)
        path.write_text(yaml_str, encoding="utf-8")
        if self.encrypted:
            if not self._encrypt_in_place(path):
                return False
        return True

    def ensure_service(self, service: str):
        if "services" not in self.data:
            self.data["services"] = {}
        self.data["services"].setdefault(service, {})

    def ensure_service_entries(self, service: str, required_keys: Dict[str, Callable[[], str]]) -> Dict[str, str]:
        """Ensure required secret keys for a service exist.

        Args:
          service: service name (e.g., 'authentik')
          required_keys: mapping key_name -> generator function returning new secret value
        Returns:
          dict of the service's secrets after ensuring
        """
        self.ensure_service(service)
        svc = self.data["services"][service]
        changed = False
        for key, gen in required_keys.items():
            if key not in svc or not svc[key]:
                # Create metadata entry
                value = gen()
                svc[key] = {
                    'value': value,
                    'version': 1,
                    'rotated_at': datetime.now(timezone.utc).isoformat()
                }
                changed = True
            elif isinstance(svc[key], str):
                # Legacy raw string → wrap into metadata
                raw_val = svc[key]
                svc[key] = {
                    'value': raw_val,
                    'version': 1,
                    'rotated_at': datetime.now(timezone.utc).isoformat()
                }
                changed = True
        if changed:
            self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save()
        # Return simplified dict {key: value}
        return {k: (v.get('value') if isinstance(v, dict) else v) for k, v in svc.items()}

    def get_service_secrets(self, service: str) -> Dict[str, str]:
        svc = self.data.get("services", {}).get(service, {})
        result = {}
        for k, v in svc.items():
            if isinstance(v, dict):
                result[k] = v.get('value')
            else:
                result[k] = v
        return result

    # ---------------- Schema Upgrade ----------------
    def _upgrade_schema_if_needed(self):
        cur = self.data.get('version', 1)
        if cur == CURRENT_SCHEMA_VERSION:
            return
        services = self.data.get('services', {})
        # Upgrade v1 -> v2
        if cur == 1:
            for svc_name, secrets_map in services.items():
                for key, value in list(secrets_map.items()):
                    if isinstance(value, dict) and 'value' in value:
                        continue  # already wrapped
                    secrets_map[key] = {
                        'value': value,
                        'version': 1,
                        'rotated_at': datetime.now(timezone.utc).isoformat()
                    }
            self.data['version'] = CURRENT_SCHEMA_VERSION
            self.data['schema_upgraded_at'] = datetime.now(timezone.utc).isoformat()
            # Recompute integrity post-upgrade
            self.data['integrity'] = self._compute_integrity()
            try:
                self.save()
            except Exception:
                pass

# Convenience accessor (lazy singleton pattern if desired)
_store_instance: Optional[CanonicalSecretsStore] = None

def get_canonical_store(project_root: Optional[Path] = None) -> CanonicalSecretsStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = CanonicalSecretsStore(project_root or Path.cwd())
    return _store_instance

if __name__ == "__main__":
    store = get_canonical_store()
    print(f"Encrypted: {store.encrypted}")
    print(yaml.dump(store.data, sort_keys=False))
