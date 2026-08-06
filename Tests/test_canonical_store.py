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
Tests for canonical store cluster metadata accessors (domain + node public IP).

Isolated: each test uses a temporary project_root and NOAH_DISABLE_SOPS so it
never touches the real Secrets/canonical-secrets store.
"""
import os
import stat
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.security import canonical_store as cs  # noqa: E402
from Scripts.security.canonical_store import (  # noqa: E402
    CANONICAL_FILENAME_ENCRYPTED,
    CANONICAL_FILENAME_PLAINTEXT,
    CURRENT_SCHEMA_VERSION,
    CanonicalSecretsStore,
    InsecureStoreError,
    PlaintextReason,
    get_canonical_store,
)


def _store(tmp_path):
    (tmp_path / "Secrets").mkdir(exist_ok=True)
    return CanonicalSecretsStore(project_root=tmp_path)


def _write_raw(tmp_path, payload):
    """Seed a plaintext store file directly, bypassing the store API."""
    secrets_dir = tmp_path / "Secrets"
    secrets_dir.mkdir(exist_ok=True)
    (secrets_dir / CANONICAL_FILENAME_PLAINTEXT).write_text(yaml.safe_dump(payload))


def test_node_public_ip_defaults_to_none(tmp_path, monkeypatch):
    monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
    assert _store(tmp_path).get_node_public_ip() is None


def test_node_public_ip_roundtrip_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
    assert _store(tmp_path).set_node_public_ip("198.51.100.9") is True
    # A fresh instance must read the value back from disk.
    assert _store(tmp_path).get_node_public_ip() == "198.51.100.9"


def test_domain_and_node_ip_are_independent(tmp_path, monkeypatch):
    monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
    store = _store(tmp_path)
    store.set_cluster_domain("d.example")
    store.set_node_public_ip("198.51.100.9")
    reloaded = _store(tmp_path)
    assert reloaded.get_cluster_domain() == "d.example"
    assert reloaded.get_node_public_ip() == "198.51.100.9"


# ---------------------------------------------------------------------------
# ensure_service_entries — the generate-once-then-reuse contract that keeps
# secrets stable across Helm, Ansible and every regeneration call.
# ---------------------------------------------------------------------------

class TestEnsureServiceEntries:
    def test_generates_missing_keys_with_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = _store(tmp_path)
        out = store.ensure_service_entries("authentik", {"secret_key": lambda: "generated"})
        assert out == {"secret_key": "generated"}
        entry = store.data["services"]["authentik"]["secret_key"]
        assert entry["value"] == "generated"
        assert entry["version"] == 1
        assert entry["rotated_at"]

    def test_existing_values_are_never_regenerated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = _store(tmp_path)
        store.ensure_service_entries("authentik", {"secret_key": lambda: "first"})

        calls = []

        def _gen():
            calls.append(1)
            return "second"

        again = store.ensure_service_entries("authentik", {"secret_key": _gen})
        assert again["secret_key"] == "first"
        assert calls == [], "generator must not run for an existing key"

    def test_persists_across_instances(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        _store(tmp_path).ensure_service_entries("headlamp", {"oidc_client_secret": lambda: "s3cret"})
        assert _store(tmp_path).get_service_secrets("headlamp") == {"oidc_client_secret": "s3cret"}

    def test_legacy_raw_string_is_wrapped_in_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = _store(tmp_path)
        # A v2 file may still carry a bare string written by an older NOAH.
        store.data["services"] = {"cilium": {"cluster_mesh_key": "bare-value"}}
        out = store.ensure_service_entries("cilium", {"cluster_mesh_key": lambda: "unused"})
        assert out["cluster_mesh_key"] == "bare-value"
        assert store.data["services"]["cilium"]["cluster_mesh_key"]["version"] == 1

    def test_empty_value_is_treated_as_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = _store(tmp_path)
        store.data["services"] = {"authentik": {"secret_key": ""}}
        out = store.ensure_service_entries("authentik", {"secret_key": lambda: "regenerated"})
        assert out["secret_key"] == "regenerated"


class TestGetServiceSecrets:
    def test_unknown_service_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        assert _store(tmp_path).get_service_secrets("nope") == {}

    def test_flattens_metadata_and_raw_values(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = _store(tmp_path)
        store.data["services"] = {
            "stalwart": {
                "admin_password": {"value": "wrapped", "version": 2, "rotated_at": "x"},
                "legacy_key": "raw",
            }
        }
        assert store.get_service_secrets("stalwart") == {
            "admin_password": "wrapped",
            "legacy_key": "raw",
        }


class TestSchemaUpgrade:
    def test_v1_raw_values_are_wrapped_on_load(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        _write_raw(tmp_path, {
            "version": 1,
            "services": {"authentik": {"secret_key": "legacy-plain"}},
        })
        store = _store(tmp_path)
        assert store.data["version"] == CURRENT_SCHEMA_VERSION
        entry = store.data["services"]["authentik"]["secret_key"]
        assert entry["value"] == "legacy-plain"
        assert entry["version"] == 1
        # The value itself must survive the migration untouched.
        assert store.get_service_secrets("authentik") == {"secret_key": "legacy-plain"}

    def test_already_wrapped_entries_are_left_alone(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        _write_raw(tmp_path, {
            "version": 1,
            "services": {
                "authentik": {
                    "secret_key": {"value": "kept", "version": 7, "rotated_at": "earlier"}
                }
            },
        })
        entry = _store(tmp_path).data["services"]["authentik"]["secret_key"]
        assert entry == {"value": "kept", "version": 7, "rotated_at": "earlier"}


class TestGetCanonicalStore:
    def test_returns_a_cached_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        monkeypatch.setattr(cs, "_store_instance", None)
        (tmp_path / "Secrets").mkdir(exist_ok=True)
        first = get_canonical_store(tmp_path)
        assert get_canonical_store(tmp_path) is first


# ---------------------------------------------------------------------------
# Plaintext lock: the store refuses to write in the clear unless the
# environment says otherwise, and defaults to refusing.
# ---------------------------------------------------------------------------

def _age_key(project_root: Path) -> Path:
    """Create a plausible Age key file inside the project root."""
    age_dir = project_root / "Age"
    age_dir.mkdir(exist_ok=True)
    key = age_dir / "keys.txt"
    key.write_text("# public key: age1fake\nAGE-SECRET-KEY-1FAKE\n")
    return key


def _sops(monkeypatch, available: bool) -> None:
    monkeypatch.setattr(cs.SopsClient, "is_available", staticmethod(lambda: available))


def _stub_encrypt(monkeypatch, ok: bool = True, on_call=None) -> None:
    """Stand in for _encrypt_in_place, which shells out to the sops binary.

    Mirrors what the real one leaves behind: encrypted bytes in a file whose
    0600 mode is preserved (it os.replaces its own mkstemp temp into place).
    """
    def _impl(self, path):
        path = Path(path)
        if on_call is not None:
            on_call(path)
        if not ok:
            return False
        path.write_text("sops:\n    version: fake\n", encoding="utf-8")
        return True

    monkeypatch.setattr(cs.CanonicalSecretsStore, "_encrypt_in_place", _impl)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


class TestPlaintextLock:
    def test_t1_unset_environment_with_missing_key_refuses(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NOAH_ENVIRONMENT", raising=False)
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        with pytest.raises(InsecureStoreError) as exc:
            CanonicalSecretsStore(project_root=tmp_path)
        assert PlaintextReason.KEY_MISSING.value in str(exc.value)
        # The refusal is worth nothing if a file was written on the way out.
        assert list((tmp_path / "Secrets").iterdir()) == []

    def test_t2_opt_out_does_not_cross_the_lock(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        _age_key(tmp_path)
        _sops(monkeypatch, True)
        with pytest.raises(InsecureStoreError) as exc:
            CanonicalSecretsStore(project_root=tmp_path)
        assert PlaintextReason.OPT_OUT.value in str(exc.value)

    def test_t3_missing_sops_binary_refuses(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        _age_key(tmp_path)
        _sops(monkeypatch, False)
        with pytest.raises(InsecureStoreError) as exc:
            CanonicalSecretsStore(project_root=tmp_path)
        assert PlaintextReason.SOPS_MISSING.value in str(exc.value)

    def test_t4_development_writes_plaintext_and_warns_loudly(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "development")
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = CanonicalSecretsStore(project_root=tmp_path)
        assert store.encrypted is False
        assert store.save() is True
        assert (tmp_path / "Secrets" / CANONICAL_FILENAME_PLAINTEXT).exists()
        # logger.warning alone drowns in CLI output; stderr is the visible half.
        assert "UNENCRYPTED" in capsys.readouterr().err

    def test_t5_key_and_sops_present_encrypts(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        _age_key(tmp_path)
        _sops(monkeypatch, True)
        _stub_encrypt(monkeypatch)
        store = CanonicalSecretsStore(project_root=tmp_path)
        assert store.encrypted is True
        assert store.save() is True
        assert (tmp_path / "Secrets" / CANONICAL_FILENAME_ENCRYPTED).exists()

    def test_t6_age_key_file_outside_the_repo_still_encrypts(self, tmp_path, monkeypatch):
        """Non-regression: honouring AGE_KEY_FILE is what lets the key live
        outside the repo without silently downgrading the store to plaintext."""
        external = tmp_path / "elsewhere"
        external.mkdir()
        key = external / "keys.txt"
        key.write_text("AGE-SECRET-KEY-1FAKE\n")
        project = tmp_path / "repo"
        project.mkdir()

        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        monkeypatch.setenv("AGE_KEY_FILE", str(key))
        _sops(monkeypatch, True)

        store = CanonicalSecretsStore(project_root=project)
        assert store.age_key_file == key
        assert store.encrypted is True

    def test_t7_failed_construction_caches_no_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        monkeypatch.setattr(cs, "_store_instance", None)
        with pytest.raises(InsecureStoreError):
            get_canonical_store(tmp_path)
        assert cs._store_instance is None

    def test_t8_refusal_is_not_absorbed_by_authentik_credentials(self, tmp_path, monkeypatch):
        """The broad `except Exception` there would otherwise flatten the
        refusal into an error string, leaving the lock inert on that path."""
        from Scripts.core_helm import authentik_credentials

        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        monkeypatch.setattr(cs, "_store_instance", None)
        monkeypatch.chdir(tmp_path)  # get_canonical_store() defaults to cwd

        with pytest.raises(InsecureStoreError):
            authentik_credentials.get_admin_credentials()

    def test_each_reason_yields_a_distinct_actionable_message(self, tmp_path):
        """Three causes, three remedies: revoke an opt-out, restore a key,
        install a binary. One shared message would force a manual diagnosis."""
        messages = {
            cs._remediation_message(r, tmp_path / "Age" / "keys.txt")
            for r in PlaintextReason
        }
        assert len(messages) == len(PlaintextReason) == 3

    @pytest.mark.parametrize(
        "value", ["development", "dev", "test", "ci", "TEST", " Development "]
    )
    def test_unlocked_values_are_matched_case_and_space_insensitively(
        self, monkeypatch, value
    ):
        monkeypatch.setenv("NOAH_ENVIRONMENT", value)
        assert cs._environment_is_locked() is False

    @pytest.mark.parametrize("value", ["production", "staging", "", "  ", "prod", "devel"])
    def test_locked_values_include_empty_and_unknown(self, monkeypatch, value):
        """The list is closed: anything not explicitly unlocked fails closed."""
        monkeypatch.setenv("NOAH_ENVIRONMENT", value)
        assert cs._environment_is_locked() is True

    def test_unset_environment_is_locked(self, monkeypatch):
        monkeypatch.delenv("NOAH_ENVIRONMENT", raising=False)
        assert cs._environment_is_locked() is True


# ---------------------------------------------------------------------------
# Atomic save: the content must never appear under its final name before it is
# in its final state, nor at permissions wider than 0600.
# ---------------------------------------------------------------------------

class TestAtomicSave:
    def _encrypted_store(self, tmp_path, monkeypatch, **stub):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "production")
        monkeypatch.delenv("NOAH_DISABLE_SOPS", raising=False)
        _age_key(tmp_path)
        _sops(monkeypatch, True)
        _stub_encrypt(monkeypatch, **stub)
        return CanonicalSecretsStore(project_root=tmp_path)

    def test_t9_plaintext_never_appears_under_the_definitive_name(self, tmp_path, monkeypatch):
        final = tmp_path / "Secrets" / CANONICAL_FILENAME_ENCRYPTED
        seen = {}

        def _observe(tmp):
            # Sampled at the one moment plaintext exists on disk.
            seen["tmp_is_not_final"] = tmp != final
            seen["tmp_holds_plaintext"] = "probe" in tmp.read_text()
            seen["final_exists"] = final.exists()

        store = self._encrypted_store(tmp_path, monkeypatch, on_call=_observe)
        store.data.setdefault("services", {})["probe"] = {"k": "v"}
        assert store.save() is True

        assert seen["tmp_is_not_final"] is True
        assert seen["tmp_holds_plaintext"] is True
        assert seen["final_exists"] is False

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_t10_encrypted_file_is_0600(self, tmp_path, monkeypatch):
        store = self._encrypted_store(tmp_path, monkeypatch)
        assert store.save() is True
        assert _mode(tmp_path / "Secrets" / CANONICAL_FILENAME_ENCRYPTED) == 0o600

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_t11_plaintext_file_is_0600_too(self, tmp_path, monkeypatch):
        """A degraded mode is no excuse for open permissions."""
        monkeypatch.setenv("NOAH_ENVIRONMENT", "development")
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        store = CanonicalSecretsStore(project_root=tmp_path)
        assert store.save() is True
        assert _mode(tmp_path / "Secrets" / CANONICAL_FILENAME_PLAINTEXT) == 0o600

    def test_t12_failed_encryption_leaves_the_previous_file_intact(self, tmp_path, monkeypatch):
        store = self._encrypted_store(tmp_path, monkeypatch)
        assert store.save() is True
        final = tmp_path / "Secrets" / CANONICAL_FILENAME_ENCRYPTED
        before = final.read_bytes()

        _stub_encrypt(monkeypatch, ok=False)
        store.data.setdefault("services", {})["new"] = {"k": "v"}
        assert store.save() is False
        assert final.read_bytes() == before
        assert [p.name for p in (tmp_path / "Secrets").iterdir()] == [final.name]

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_t13_secrets_directory_is_0700(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOAH_ENVIRONMENT", "development")
        monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
        CanonicalSecretsStore(project_root=tmp_path)
        assert _mode(tmp_path / "Secrets") == 0o700

    def test_t14_opposite_variant_is_dropped_only_after_a_successful_replace(
        self, tmp_path, monkeypatch
    ):
        secrets_dir = tmp_path / "Secrets"
        secrets_dir.mkdir(exist_ok=True)
        stale = secrets_dir / CANONICAL_FILENAME_PLAINTEXT
        stale.write_text("version: 2\nservices: {}\n")

        store = self._encrypted_store(tmp_path, monkeypatch, ok=False)
        assert store.save() is False
        # Removing it first would destroy the old state before the new exists.
        assert stale.exists()

        _stub_encrypt(monkeypatch, ok=True)
        assert store.save() is True
        assert not stale.exists()
