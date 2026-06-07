#!/usr/bin/env python3
"""
Tests for canonical store cluster metadata accessors (domain + node public IP).

Isolated: each test uses a temporary project_root and NOAH_DISABLE_SOPS so it
never touches the real Secrets/canonical-secrets store.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.security.canonical_store import CanonicalSecretsStore  # noqa: E402


def _store(tmp_path):
    (tmp_path / "Secrets").mkdir(exist_ok=True)
    return CanonicalSecretsStore(project_root=tmp_path)


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
