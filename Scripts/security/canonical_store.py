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

import hashlib
import logging
import os
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from Scripts.security.sops_client import (
    SopsClient,
    SopsDecryptionError,
    SopsEncryptionError,
    SopsError,
    SopsKeyError,
)

logger = logging.getLogger(__name__)

CANONICAL_FILENAME_ENCRYPTED = "canonical-secrets.enc.yaml"
CANONICAL_FILENAME_PLAINTEXT = "canonical-secrets.yaml"

# Schema versions:
# v1: { version:1, services: { svc: { key: raw_value } } }
# v2: { version:2, services: { svc: { key: { value: str, version: int, rotated_at: iso } } } }
CURRENT_SCHEMA_VERSION = 2

# Environments where a plaintext store is tolerated. Any other value -- unset,
# empty or unrecognised -- locks it: a forgotten setting must refuse to write,
# not silently write secrets in the clear.
_UNLOCKED_ENVIRONMENTS = frozenset({"development", "dev", "test", "ci"})


# --- Secret domain separation (Specs/To-do/Garage.md §3.1) -----------------
#
# The cluster's Age private key is handed to the compute node as the `sops-age`
# Secret, so everything this store holds is readable from the compute node by
# design. Garage administration credentials must therefore never land here:
# they live in Secrets/garage-admin.enc.yaml, encrypted to a second Age
# identity that no node ever receives (Scripts/garage/admin_store.py).
#
# Enforced rather than documented, because the failure is invisible: a Garage
# deployed with its rpc_secret in this store still works, and only the
# isolation guarantee (D6) is silently gone.
ADMIN_ONLY_SERVICES = frozenset({"garage-admin"})
ADMIN_ONLY_KEYS = frozenset({
    "rpc_secret",
    "admin_token",
    "ssh_private_key",
    "ssh_public_key",
    "owner_access_key_id",
    "owner_secret_key",
    "cloud_access_key_id",
    "cloud_secret_access_key",
    "tofu_state_passphrase",
})


class AdminSecretLeakError(RuntimeError):
    """A domain-3 (Garage administration) secret was about to enter this store.

    Like InsecureStoreError, a policy refusal rather than a SOPS failure, and
    deliberately not a SopsError so the existing handlers do not swallow it.
    """


class InsecureStoreError(RuntimeError):
    """The store would be written in plaintext in an environment that forbids it.

    Deliberately NOT derived from SopsError: this is a policy refusal, not a SOPS
    failure, and inheriting would expose it to the existing `except SopsError`
    handlers.
    """


class PlaintextReason(Enum):
    """Why encryption is off.

    A boolean cannot carry three causes, and the three call for three different
    remedies -- revoke an opt-out, restore a key, install a binary. Collapsing
    them into one message forces a manual diagnosis at every incident.
    """

    OPT_OUT = "NOAH_DISABLE_SOPS is set"
    KEY_MISSING = "Age key file not found"
    SOPS_MISSING = "sops binary not available"


def _environment_is_locked() -> bool:
    """Whether plaintext writes are refused. Defaults to locked.

    Reads os.environ directly rather than ConfigLoader: ConfigLoader.get() lets
    the cached config take precedence over the environment, so a
    `NOAH_ENVIRONMENT: development` sitting in a config file -- possibly
    committed or shipped -- would unlock production. A security lock must not be
    defeatable by a file.
    """
    env = os.environ.get("NOAH_ENVIRONMENT", "production").strip().lower()
    return env not in _UNLOCKED_ENVIRONMENTS


def resolve_age_key_file(project_root: Path) -> Path:
    """AGE_KEY_FILE when set, else <project_root>/Age/keys.txt.

    Honouring AGE_KEY_FILE is what lets the key live outside the repository
    without silently downgrading the store to plaintext.

    Not reusing paths.py's 'age_key_file': its './Age/keys.txt' default is
    relative to the current working directory, which would break every test
    building a store on a tmp_path project root.
    """
    env_key = os.environ.get("AGE_KEY_FILE")
    return Path(env_key) if env_key else project_root / "Age" / "keys.txt"


def plaintext_reason(age_key_file: Path) -> PlaintextReason | None:
    """None if encryption is active, otherwise the cause of the plaintext fallback.

    A module-level function rather than a method because `setup doctor` must
    report the effective mode WITHOUT constructing a store: in a locked
    environment the constructor raises in precisely the case doctor needs to
    report, so an instance method would make the diagnosis impossible.
    """
    if os.environ.get("NOAH_DISABLE_SOPS", "false").lower() in ("1", "true", "yes"):
        return PlaintextReason.OPT_OUT
    if not age_key_file.exists():
        return PlaintextReason.KEY_MISSING
    if not SopsClient.is_available():
        return PlaintextReason.SOPS_MISSING
    return None


def _remediation_message(reason: PlaintextReason, age_key_file: Path) -> str:
    """One actionable remedy per cause -- see PlaintextReason."""
    remedy = {
        PlaintextReason.OPT_OUT: (
            "Unset NOAH_DISABLE_SOPS to restore encryption, or set "
            "NOAH_ENVIRONMENT=development if plaintext is genuinely intended."
        ),
        PlaintextReason.KEY_MISSING: (
            f"Restore the Age key at {age_key_file}, or point AGE_KEY_FILE at "
            "wherever it lives. 'python3 noah.py setup initialize' creates one."
        ),
        PlaintextReason.SOPS_MISSING: (
            "Install the sops binary ('python3 noah.py setup update-sops') and "
            "make sure it is on PATH."
        ),
    }[reason]
    declared = os.environ.get("NOAH_ENVIRONMENT") or "(unset -- treated as production)"
    return (
        "Refusing to write the canonical secrets store in plaintext: "
        f"{reason.value}.\n"
        f"  NOAH_ENVIRONMENT={declared}\n"
        f"  {remedy}"
    )


@dataclass
class CanonicalSecretsStore:
    project_root: Path = field(default_factory=lambda: Path.cwd())
    secrets_dir: Path = field(init=False)
    age_key_file: Path = field(init=False)
    encrypted: bool = field(init=False)
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.secrets_dir = self.project_root / "Secrets"
        # 0o700 for the same reason the Age key is 0o600: nothing here is fit
        # for other local users. Only applied when this call creates the dir.
        self.secrets_dir.mkdir(mode=0o700, exist_ok=True)
        self.age_key_file = self._resolve_age_key_file()

        reason = self._plaintext_reason()
        # Raise BEFORE _load(), and therefore before anything can be written: a
        # file written in the clear stays on disk -- and probably in a backup --
        # long after the setting is fixed. Warning after the fact undoes nothing.
        if reason is not None and _environment_is_locked():
            raise InsecureStoreError(_remediation_message(reason, self.age_key_file))

        self.encrypted = reason is None
        if reason is not None:
            self._warn_plaintext(reason)
        self._load()

    # ---------------- Internal Helpers ----------------
    # Which secrets this store refuses to hold. Overridden to the empty set by
    # the domain-3 store, which is precisely where they belong.
    # Deliberately unannotated: an annotation here would make @dataclass treat
    # them as fields and hand them to __init__, where a subclass override would
    # be silently overwritten by the parent's default.
    _forbidden_services = ADMIN_ONLY_SERVICES
    _forbidden_keys = ADMIN_ONLY_KEYS

    def _resolve_age_key_file(self) -> Path:
        return resolve_age_key_file(self.project_root)

    def _check_domain_separation(self) -> None:
        """Refuse to hold a Garage administration secret -- see §3.1.

        Called from ensure_service() so the refusal lands before a generator
        runs, and again from save() so a caller writing straight into .data
        cannot get round it.
        """
        for service, secrets_map in (self.data.get("services") or {}).items():
            if service in self._forbidden_services:
                raise AdminSecretLeakError(
                    f"Service {service!r} belongs to the Garage administration "
                    "secret domain and must not enter the canonical store: it "
                    "would be readable from the compute node via the sops-age "
                    "Secret. Use Scripts/garage/admin_store.py "
                    "(Secrets/garage-admin.enc.yaml)."
                )
            offending = sorted(set(secrets_map or {}) & self._forbidden_keys)
            if offending:
                raise AdminSecretLeakError(
                    f"Key(s) {', '.join(offending)} under service {service!r} "
                    "belong to the Garage administration secret domain and must "
                    "not enter the canonical store. Use "
                    "Scripts/garage/admin_store.py (Secrets/garage-admin.enc.yaml)."
                )

    def _plaintext_reason(self) -> PlaintextReason | None:
        return plaintext_reason(self.age_key_file)

    def _warn_plaintext(self, reason: PlaintextReason) -> None:
        """Outside a locked environment plaintext stays allowed, but must be
        visible: a logger.warning alone drowns in the CLI output stream.

        No click import here -- a security module must not depend on the
        presentation layer, and must stay usable outside the CLI. Formatting
        belongs to noah.py and doctor_utils.py, which already import click.
        """
        message = (
            f"canonical secrets store is UNENCRYPTED ({reason.value}); "
            f"secrets are written in plaintext to {self._plaintext_path()}"
        )
        logger.warning(message)
        print(f"[WARNING] {message}", file=sys.stderr)

    def _encrypted_path(self) -> Path:
        return self.secrets_dir / CANONICAL_FILENAME_ENCRYPTED

    def _plaintext_path(self) -> Path:
        return self.secrets_dir / CANONICAL_FILENAME_PLAINTEXT

    def _active_path(self) -> Path:
        return self._encrypted_path() if self.encrypted else self._plaintext_path()

    def _decrypt_file(self, path: Path) -> str | None:
        if not path.exists():
            return None
        if not self.encrypted:
            return path.read_text(encoding="utf-8")
        try:
            with SopsClient(self.age_key_file) as sops:
                return sops.decrypt_to_string(path)
        except SopsKeyError as e:
            logger.error("Age key unavailable for decryption: %s", e)
            raise  # blocking -- cannot continue without secrets
        except SopsDecryptionError as e:
            # Stale recipient or corrupt file — remove it so the next save
            # recreates it with the current key.
            logger.warning(
                "Canonical secrets corrupted (%s): %s -- resetting file",
                path.name,
                e.detail,
            )
            path.unlink(missing_ok=True)
            return None
        except SopsError as e:
            # Covers SopsConfigError, SopsTimeoutError, SopsBinaryNotFoundError,
            # and the base-class catch-all (e.g. "File has no SOPS metadata" when
            # a previous save left a plaintext file with an .enc.yaml name).
            # Treat every such case as a corrupt/stale file and reset.
            logger.warning(
                "Canonical secrets unreadable (%s): %s -- resetting file",
                path.name,
                e.detail or str(e),
            )
            path.unlink(missing_ok=True)
            return None

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
        try:
            with SopsClient(self.age_key_file) as sops:
                sops.encrypt_in_place(path)
            return True
        except SopsEncryptionError as e:
            logger.error("Failed to encrypt canonical secrets: %s", e.detail)
            return False

    # ---------------- Public API ----------------
    def save(self) -> bool:
        self._check_domain_separation()
        path = self._active_path()

        # Refresh integrity before persisting
        self.data["integrity"] = self._compute_integrity()
        yaml_str = yaml.dump(self.data, default_flow_style=False, sort_keys=False)

        # The content must never appear under its final name before it is in its
        # final state. Write to a temp file in the SAME directory (os.replace is
        # only atomic within one filesystem), then swap it in atomically.
        #
        # mkstemp creates the file O_EXCL at 0o600, so the mode is in force
        # *before* any content is written -- a write_text() followed by a chmod
        # would leave a real, if brief, world-readable window instead.
        #
        # The suffix mirrors the final name so SOPS' .sops.yaml creation rules
        # match the temp file too. (encrypt_in_place makes its own .enc.yaml
        # temp, so this is belt-and-braces rather than load-bearing today.)
        suffix = ".enc.yaml" if self.encrypted else ".yaml"
        fd, tmp_str = tempfile.mkstemp(
            dir=self.secrets_dir, prefix=".canonical-", suffix=suffix
        )
        tmp = Path(tmp_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(yaml_str)
            # No-op when not encrypted. On failure the definitive file is left
            # untouched -- the previous state survives a failed save.
            if not self._encrypt_in_place(tmp):
                return False
            os.replace(tmp, path)
        except OSError as e:
            logger.error("Failed to write canonical secrets to %s: %s", path.name, e)
            return False
        finally:
            # No-op after a successful replace; the cleanup that matters is the
            # failure path, which must not leave a temp file behind.
            tmp.unlink(missing_ok=True)

        # Only now that the new state is in place: drop the opposite-mode
        # variant left by a previous run. Removing it first would destroy the
        # old state before the new one exists.
        try:
            other = self._plaintext_path() if self.encrypted else self._encrypted_path()
            if other.exists():
                other.unlink()
        except OSError:
            pass
        return True

    def ensure_service(self, service: str):
        if service in self._forbidden_services:
            raise AdminSecretLeakError(
                f"Service {service!r} belongs to the Garage administration "
                "secret domain (§3.1) and must not enter the canonical store."
            )
        if "services" not in self.data:
            self.data["services"] = {}
        self.data["services"].setdefault(service, {})

    def ensure_service_entries(self, service: str, required_keys: dict[str, Callable[[], str]]) -> dict[str, str]:
        """Ensure required secret keys for a service exist.

        Args:
          service: service name (e.g., 'authentik')
          required_keys: mapping key_name -> generator function returning new secret value
        Returns:
          dict of the service's secrets after ensuring
        """
        self.ensure_service(service)
        offending = sorted(set(required_keys) & self._forbidden_keys)
        if offending:
            raise AdminSecretLeakError(
                f"Key(s) {', '.join(offending)} belong to the Garage "
                "administration secret domain (§3.1) and must not enter the "
                "canonical store."
            )
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

    def get_service_secrets(self, service: str) -> dict[str, str]:
        svc = self.data.get("services", {}).get(service, {})
        result = {}
        for k, v in svc.items():
            if isinstance(v, dict):
                result[k] = v.get('value')
            else:
                result[k] = v
        return result

    # Cluster-level (non-secret) settings stored alongside the encrypted
    # service secrets so `setup gitops` has a single source of truth for
    # "what domain did the previous run use" without needing a separate
    # state file. Not covered by the integrity hash (only `services` is).
    def get_cluster_domain(self) -> str | None:
        return self.data.get("cluster", {}).get("domain")

    def set_cluster_domain(self, domain: str) -> bool:
        self.data.setdefault("cluster", {})["domain"] = domain
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.save()

    def get_cluster_ssh_key_file(self) -> str | None:
        """Path of the SSH key `cluster bootstrap` last used, if any.

        Recorded so `noah garage deploy` can REFUSE that same key (T2): a key
        shared between the cluster and the Garage nodes hands the storage tier
        to whoever gets root on the compute node, which is precisely what
        condition 3 of §10.2 forbids. Comparing against a recorded fact beats
        guessing at conventional paths.
        """
        return self.data.get("cluster", {}).get("ssh_key_file")

    def set_cluster_ssh_key_file(self, ssh_key_file: str) -> bool:
        self.data.setdefault("cluster", {})["ssh_key_file"] = str(ssh_key_file)
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.save()

    def get_node_public_ip(self) -> str | None:
        return self.data.get("cluster", {}).get("node_public_ip")

    def set_node_public_ip(self, node_public_ip: str) -> bool:
        self.data.setdefault("cluster", {})["node_public_ip"] = node_public_ip
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.save()

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
_store_instance: CanonicalSecretsStore | None = None

def get_canonical_store(project_root: Path | None = None) -> CanonicalSecretsStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = CanonicalSecretsStore(project_root or Path.cwd())
    return _store_instance

if __name__ == "__main__":
    store = get_canonical_store()
    print(f"Encrypted: {store.encrypted}")
    print(yaml.dump(store.data, sort_keys=False))
