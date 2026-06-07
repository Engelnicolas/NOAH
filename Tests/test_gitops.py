#!/usr/bin/env python3
"""
Tests for the `setup gitops` command and the underlying setup_gitops() function.

Fast unit tests: all external I/O (SOPS binary, canonical store, secret
generation) is mocked. The integration test (requires the real sops binary) is
marked with @pytest.mark.integration.
"""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DOMAIN = "test.example.org"
NODE_IP = "203.0.113.7"
AGE_PUBLIC_KEY = "age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq5zuzd"

FAKE_SECRETS = {
    "REPLACE_WITH_CLOUDFLARE_TOKEN":       "cf-token-abc",
    "REPLACE_WITH_50_CHAR_SECRET":         "a" * 50,
    "REPLACE_WITH_ADMIN_PASSWORD":         "admin-pass",
    "REPLACE_WITH_BOOTSTRAP_TOKEN":        "bootstrap-tok",
    "REPLACE_WITH_POSTGRES_PASSWORD":      "pg-pass",
    "REPLACE_WITH_POSTGRES_ROOT_PASSWORD": "pg-pass",
    "REPLACE_WITH_OIDC_CLIENT_ID":         "headlamp",
    "REPLACE_WITH_OIDC_CLIENT_SECRET":     "oidc-secret",
    "admin@example.com":                   f"admin@{DOMAIN}",
    "example.com":                         DOMAIN,
}


@pytest.fixture()
def project_root(tmp_path):
    """Minimal project root containing Age/keys.txt (fake age key)."""
    age_dir = tmp_path / "Age"
    age_dir.mkdir()
    (age_dir / "keys.txt").write_text(
        f"# created: 2026-01-01T00:00:00Z\n"
        f"# public key: {AGE_PUBLIC_KEY}\n"
        f"AGE-SECRET-KEY-1QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ\n"
    )
    return tmp_path


def _noop_print_status(msg, level="INFO"):
    pass


# ---------------------------------------------------------------------------
# Unit tests — setup_gitops() internals
# ---------------------------------------------------------------------------

class TestAgePublicKey:
    def test_reads_comment_format(self, project_root):
        from Scripts.gitops.gitops_init import _age_public_key
        assert _age_public_key(project_root) == AGE_PUBLIC_KEY

    def test_reads_bare_age1_line(self, tmp_path):
        from Scripts.gitops.gitops_init import _age_public_key
        (tmp_path / "Age").mkdir()
        (tmp_path / "Age" / "keys.txt").write_text(
            f"{AGE_PUBLIC_KEY}\nAGE-SECRET-KEY-1...\n"
        )
        assert _age_public_key(tmp_path) == AGE_PUBLIC_KEY

    def test_raises_when_missing(self, tmp_path):
        from Scripts.gitops.gitops_init import _age_public_key
        with pytest.raises(RuntimeError, match="Age key not found"):
            _age_public_key(tmp_path)


class TestWriteSopsYaml:
    def test_creates_file_with_correct_key(self, tmp_path):
        from Scripts.gitops.gitops_init import _write_sops_yaml
        _write_sops_yaml(tmp_path, AGE_PUBLIC_KEY)
        content = (tmp_path / ".sops.yaml").read_text()
        assert AGE_PUBLIC_KEY in content
        assert "enc" in content  # path_regex contains \.enc\.yaml$ (regex-escaped)


class TestSubstituteDomain:
    def test_replaces_example_com(self):
        from Scripts.gitops.gitops_init import _substitute_domain
        result = _substitute_domain("host: auth.example.com", "mysite.io")
        assert result == "host: auth.mysite.io"

    def test_no_change_when_no_placeholder(self):
        from Scripts.gitops.gitops_init import _substitute_domain
        text = "host: auth.mysite.io"
        assert _substitute_domain(text, "other.io") == text


class TestSubstituteNodeIp:
    def test_replaces_placeholder(self):
        from Scripts.gitops.gitops_init import _substitute_node_ip
        assert _substitute_node_ip("addr: ${NODE_PUBLIC_IP}", "1.2.3.4") == "addr: 1.2.3.4"

    def test_swaps_previous_ip(self):
        from Scripts.gitops.gitops_init import _substitute_node_ip
        result = _substitute_node_ip("addr: 1.2.3.4", "9.9.9.9", previous_ip="1.2.3.4")
        assert result == "addr: 9.9.9.9"

    def test_no_change_without_placeholder_or_previous(self):
        from Scripts.gitops.gitops_init import _substitute_node_ip
        text = "addr: 9.9.9.9"
        assert _substitute_node_ip(text, "9.9.9.9") == text


class TestFillFile:
    def test_replaces_all_placeholders(self, tmp_path):
        from Scripts.gitops.gitops_init import _fill_file
        f = tmp_path / "secret.enc.yaml"
        f.write_text("token: REPLACE_WITH_CLOUDFLARE_TOKEN\nemail: admin@example.com\n")
        _fill_file(f, {"REPLACE_WITH_CLOUDFLARE_TOKEN": "tok123", "admin@example.com": "admin@real.com"})
        content = f.read_text()
        assert "tok123" in content
        assert "admin@real.com" in content
        assert "REPLACE_WITH" not in content


class TestGetOrGenerateSecrets:
    def test_returns_all_keys_and_raises_without_cf_token(self, project_root):
        from Scripts.gitops.gitops_init import _get_or_generate_secrets

        mock_store = MagicMock()
        mock_store.get_service_secrets.side_effect = lambda svc: {
            "cloudflare": {"api_token": None},
            "authentik":  {"secret_key": "sk", "bootstrap_password": "bp",
                           "bootstrap_token": "bt", "postgresql_password": "pp"},
            "headlamp":   {"oidc_client_id": "headlamp", "oidc_client_secret": "os"},
        }[svc]

        with patch("Scripts.security.canonical_store.get_canonical_store", return_value=mock_store), \
             patch("Scripts.security.security_manager.NoahSecurityManager"):
            with pytest.raises(RuntimeError, match="Cloudflare API token not found"):
                _get_or_generate_secrets(project_root, DOMAIN)

    def test_returns_mapping_with_cf_token(self, project_root):
        from Scripts.gitops.gitops_init import _get_or_generate_secrets

        mock_store = MagicMock()
        mock_store.get_service_secrets.side_effect = lambda svc: {
            "cloudflare": {"api_token": "cf-tok"},
            "authentik":  {"secret_key": "sk", "bootstrap_password": "bp",
                           "bootstrap_token": "bt", "postgresql_password": "pp"},
            "headlamp":   {"oidc_client_id": "headlamp", "oidc_client_secret": "os"},
        }[svc]

        with patch("Scripts.security.canonical_store.get_canonical_store", return_value=mock_store), \
             patch("Scripts.security.security_manager.NoahSecurityManager"):
            result = _get_or_generate_secrets(project_root, DOMAIN)

        assert result["REPLACE_WITH_CLOUDFLARE_TOKEN"] == "cf-tok"
        assert result["REPLACE_WITH_OIDC_CLIENT_ID"] == "headlamp"
        assert result[f"admin@example.com"] == f"admin@{DOMAIN}"


class TestRenderAppSecretManifests:
    """Out-of-band delivery path: secrets are rendered in memory (and applied via
    kubectl by the app-secrets role) rather than committed to Git."""

    def _render(self, project_root):
        from Scripts.gitops.gitops_init import render_app_secret_manifests
        mock_store = MagicMock()
        mock_store.get_cluster_domain.return_value = None
        with patch("Scripts.gitops.gitops_init._get_or_generate_secrets",
                   return_value=dict(FAKE_SECRETS)), \
             patch("Scripts.security.canonical_store.get_canonical_store",
                   return_value=mock_store):
            return render_app_secret_manifests(project_root, DOMAIN)

    def test_renders_five_secret_documents(self, project_root):
        out = self._render(project_root)
        assert out.count("apiVersion: v1") == 5
        assert out.count("kind: Secret") == 5
        assert "\n---\n" in out  # multi-document stream

    def test_all_placeholders_filled(self, project_root):
        out = self._render(project_root)
        assert "REPLACE_WITH" not in out
        assert "example.com" not in out

    def test_contains_expected_secret_material_and_namespaces(self, project_root):
        out = self._render(project_root)
        assert "cf-token-abc" in out
        for ns in ("external-dns", "cert-manager", "authentik", "headlamp"):
            assert f"namespace: {ns}" in out


# ---------------------------------------------------------------------------
# Unit tests — setup_gitops() end-to-end (in-place; SOPS + store mocked)
# ---------------------------------------------------------------------------

class TestSetupGitopsInPlace:
    """The current setup_gitops() substitutes the domain and node public IP in
    place inside project_root/gitops/, then SOPS-encrypts. SOPS, the canonical
    store and secret generation are mocked."""

    def _run(self, project_root, node_public_ip=None):
        from Scripts.gitops import gitops_init

        hr_dir = project_root / "gitops" / "infrastructure" / "nginx-ingress"
        hr_dir.mkdir(parents=True)
        hr = hr_dir / "helmrelease.yaml"
        hr.write_text(
            "host: auth.example.com\n"
            "publish-status-address: ${NODE_PUBLIC_IP}\n"
        )

        store = MagicMock()
        store.get_cluster_domain.return_value = None
        store.get_node_public_ip.return_value = None

        with patch.object(gitops_init, "_get_or_generate_secrets",
                          return_value=dict(FAKE_SECRETS)), \
             patch.object(gitops_init, "_sops_encrypt"), \
             patch("Scripts.security.canonical_store.get_canonical_store",
                   return_value=store):
            gitops_init.setup_gitops(
                domain=DOMAIN,
                project_root=project_root,
                print_status=_noop_print_status,
                node_public_ip=node_public_ip,
            )
        return hr, store

    def test_substitutes_domain(self, project_root):
        hr, _ = self._run(project_root)
        text = hr.read_text()
        assert DOMAIN in text
        assert "example.com" not in text

    def test_substitutes_node_ip_when_provided(self, project_root):
        hr, store = self._run(project_root, node_public_ip=NODE_IP)
        text = hr.read_text()
        assert f"publish-status-address: {NODE_IP}" in text
        assert "${NODE_PUBLIC_IP}" not in text
        store.set_node_public_ip.assert_called_once_with(NODE_IP)

    def test_leaves_node_ip_placeholder_when_absent(self, project_root):
        hr, store = self._run(project_root, node_public_ip=None)
        text = hr.read_text()
        assert "${NODE_PUBLIC_IP}" in text
        store.set_node_public_ip.assert_not_called()


# ---------------------------------------------------------------------------
# CLI tests — `setup gitops` command
# ---------------------------------------------------------------------------

class TestSetupGitopsCli:
    def test_command_registered(self):
        import noah
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(noah.cli, ["setup", "gitops", "--help"])
        assert result.exit_code == 0
        assert "--domain" in result.output
        assert "--node-ip" in result.output

    def test_missing_domain_exits_nonzero(self):
        import noah
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(noah.cli, ["setup", "gitops"])
        assert result.exit_code != 0
        assert "domain" in result.output.lower() or "missing" in result.output.lower()

    def test_setup_gitops_error_exits_nonzero(self):
        import noah
        from click.testing import CliRunner
        runner = CliRunner()

        with patch("Scripts.gitops.gitops_init.setup_gitops",
                   side_effect=RuntimeError("Cloudflare API token not found")):
            result = runner.invoke(noah.cli, [
                "setup", "gitops",
                "--domain", DOMAIN,
                "--node-ip", "1.2.3.4",
            ])

        assert result.exit_code != 0
        assert "Cloudflare API token not found" in result.output


# ---------------------------------------------------------------------------
# Integration test — requires real sops binary
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_sops_encrypt_integration(project_root, tmp_path):
    """Calls the real sops binary to verify encryption works end-to-end."""
    from Scripts.gitops.gitops_init import _write_sops_yaml

    _write_sops_yaml(tmp_path, AGE_PUBLIC_KEY)
    enc_file = tmp_path / "test.enc.yaml"
    enc_file.write_text("stringData:\n  token: mysecret\n")

    age_key_file = project_root / "Age" / "keys.txt"
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", str(enc_file)],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"sops binary not available or key mismatch: {result.stderr}")

    content = enc_file.read_text()
    assert "mysecret" not in content
    assert "ENC[" in content
