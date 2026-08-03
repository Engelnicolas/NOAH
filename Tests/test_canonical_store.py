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
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.security import canonical_store as cs  # noqa: E402
from Scripts.security.canonical_store import (  # noqa: E402
    CANONICAL_FILENAME_PLAINTEXT,
    CURRENT_SCHEMA_VERSION,
    CanonicalSecretsStore,
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
