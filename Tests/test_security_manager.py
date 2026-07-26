#!/usr/bin/env python3
"""
Tests for NoahSecurityManager: password generation, per-service secret
definitions, and canonical-store rotation semantics.

Isolated: every test builds the manager against a temporary project_root with
NOAH_DISABLE_SOPS set, so the real Secrets/ store is never read or written.
"""
import string
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.security import canonical_store as cs  # noqa: E402
from Scripts.security.security_manager import NoahSecurityManager  # noqa: E402

SPECIALS = "!@#$%^&*()-_=+[]{}|;:,.<>?"


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """A manager rooted in tmp_path, with the store singleton reset per test."""
    monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
    monkeypatch.setattr(cs, "_store_instance", None)
    return NoahSecurityManager(project_root=tmp_path)


# ---------------------------------------------------------------------------
# generate_secure_password
# ---------------------------------------------------------------------------

class TestGenerateSecurePassword:
    @pytest.mark.parametrize("length", [8, 24, 32, 50, 64])
    def test_honours_requested_length(self, manager, length):
        assert len(manager.generate_secure_password(length)) == length

    def test_guarantees_one_of_each_character_class(self, manager):
        pw = manager.generate_secure_password(16)
        assert any(c in string.ascii_lowercase for c in pw)
        assert any(c in string.ascii_uppercase for c in pw)
        assert any(c in string.digits for c in pw)
        assert any(c in SPECIALS for c in pw)

    def test_alphanumeric_only_when_special_disabled(self, manager):
        # Used for values interpolated into URLs and unquoted YAML scalars.
        pw = manager.generate_secure_password(40, include_special=False)
        assert len(pw) == 40
        assert all(c in string.ascii_letters + string.digits for c in pw)

    def test_successive_calls_differ(self, manager):
        generated = {manager.generate_secure_password(32) for _ in range(20)}
        assert len(generated) == 20


# ---------------------------------------------------------------------------
# generate_service_secrets — the key set each service is expected to own
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    'authentik': {
        'secret_key', 'bootstrap_password', 'bootstrap_token', 'postgresql_password',
        'redis_password', 'oidc_client_secret', 'jwt_signing_key', 'session_secret',
        'email_password',
    },
    'cilium': {'hubble_tls_key', 'cluster_mesh_key', 'ca_key_passphrase'},
    'headlamp': {'oidc_client_id', 'oidc_client_secret'},
    'hubble-ui': {'proxy_client_id', 'proxy_client_secret', 'cookie_secret'},
    'nextcloud': {
        'admin_password', 'db_password', 'db_root_password', 'redis_password',
        'oidc_client_id', 'oidc_client_secret',
    },
    'stalwart': {'admin_password', 'oidc_client_id', 'oidc_client_secret', 'dkim_private_key'},
}


class TestGenerateServiceSecrets:
    @pytest.mark.parametrize("service,keys", sorted(EXPECTED_KEYS.items()))
    def test_produces_expected_key_set(self, manager, service, keys):
        assert set(manager.generate_service_secrets(service)) == keys

    def test_unknown_service_returns_empty(self, manager):
        assert manager.generate_service_secrets('does-not-exist') == {}

    def test_values_are_stable_across_calls(self, manager):
        # The whole point of the canonical store: Helm, Ansible and any later
        # regeneration must observe identical values.
        first = manager.generate_service_secrets('nextcloud')
        assert manager.generate_service_secrets('nextcloud') == first

    def test_fixed_oidc_client_ids(self, manager):
        assert manager.generate_service_secrets('headlamp')['oidc_client_id'] == 'headlamp'
        assert manager.generate_service_secrets('nextcloud')['oidc_client_id'] == 'nextcloud'
        assert manager.generate_service_secrets('stalwart')['oidc_client_id'] == 'stalwart'

    def test_nextcloud_passwords_have_no_special_characters(self, manager):
        # Interpolated into unquoted URLs / YAML by the Nextcloud chart.
        secrets_map = manager.generate_service_secrets('nextcloud')
        for key in ('admin_password', 'db_password', 'db_root_password', 'redis_password'):
            assert all(c in string.ascii_letters + string.digits for c in secrets_map[key]), key

    def test_cloudflare_token_starts_empty(self, manager):
        # Cannot be auto-generated; set later via set-cloudflare-token.
        assert manager.generate_service_secrets('cloudflare') == {'api_token': ''}

    def test_stalwart_dkim_is_an_rsa_private_key(self, manager):
        pem = manager.generate_service_secrets('stalwart')['dkim_private_key']
        assert '-----BEGIN PRIVATE KEY-----' in pem
        assert '-----END PRIVATE KEY-----' in pem


# ---------------------------------------------------------------------------
# rotate_service_secrets_canonical
# ---------------------------------------------------------------------------

class TestRotateServiceSecrets:
    def test_generates_when_service_has_no_secrets_yet(self, manager):
        out = manager.rotate_service_secrets_canonical('authentik')
        assert set(out) == EXPECTED_KEYS['authentik']

    def test_rotation_changes_value_and_bumps_version(self, manager):
        before = manager.generate_service_secrets('authentik')
        store = cs.get_canonical_store(manager.project_root)
        assert store.data['services']['authentik']['secret_key']['version'] == 1

        after = manager.rotate_service_secrets_canonical('authentik', ['secret_key'])

        assert after['secret_key'] != before['secret_key']
        entry = store.data['services']['authentik']['secret_key']
        assert entry['version'] == 2
        assert entry['value'] == after['secret_key']

    def test_only_targeted_keys_rotate(self, manager):
        before = manager.generate_service_secrets('authentik')
        after = manager.rotate_service_secrets_canonical('authentik', ['secret_key'])
        untouched = EXPECTED_KEYS['authentik'] - {'secret_key'}
        for key in untouched:
            assert after[key] == before[key], key

    def test_unknown_key_is_ignored(self, manager):
        before = manager.generate_service_secrets('authentik')
        after = manager.rotate_service_secrets_canonical('authentik', ['not_a_real_key'])
        assert after == before

    def test_rotating_all_keys_changes_every_generated_value(self, manager):
        before = manager.generate_service_secrets('cilium')
        after = manager.rotate_service_secrets_canonical('cilium')
        for key in EXPECTED_KEYS['cilium']:
            assert after[key] != before[key], key

    def test_fixed_client_id_survives_rotation(self, manager):
        manager.generate_service_secrets('headlamp')
        after = manager.rotate_service_secrets_canonical('headlamp')
        assert after['oidc_client_id'] == 'headlamp'


# ---------------------------------------------------------------------------
# Regression: rotation used to be defined separately from generation, so
# hubble-ui, nextcloud, stalwart and cloudflare were generatable but silently
# not rotatable — `secrets rotate --service nextcloud` was a no-op.
# ---------------------------------------------------------------------------

ROTATABLE_SERVICES = sorted(EXPECTED_KEYS) + ['cloudflare']


class TestGenerateRotateParity:
    @pytest.mark.parametrize("service", ROTATABLE_SERVICES)
    def test_every_generatable_service_is_rotatable(self, manager, service):
        generated = manager.generate_service_secrets(service)
        assert generated, f"{service} generates nothing"
        assert set(manager._service_generators(service)) == set(generated)

    @pytest.mark.parametrize("service", ['nextcloud', 'stalwart', 'hubble-ui'])
    def test_apps_extra_rotation_actually_changes_values(self, manager, service):
        before = manager.generate_service_secrets(service)
        after = manager.rotate_service_secrets_canonical(service)
        # Fixed client IDs are intentionally stable; every generated secret moves.
        rotated = [k for k in before if not k.endswith('client_id')]
        assert rotated
        for key in rotated:
            assert after[key] != before[key], f"{service}.{key} did not rotate"

    def test_stalwart_dkim_rotation_yields_a_new_valid_key(self, manager):
        before = manager.generate_service_secrets('stalwart')['dkim_private_key']
        after = manager.rotate_service_secrets_canonical('stalwart')['dkim_private_key']
        assert after != before
        assert '-----BEGIN PRIVATE KEY-----' in after
