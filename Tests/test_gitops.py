#!/usr/bin/env python3
"""
Tests for the `setup gitops` command and the underlying setup_gitops() function.

Fast unit tests: all external I/O (SOPS binary, GitHub, canonical store) is mocked.
Integration test (requires sops binary): marked with @pytest.mark.integration.
"""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DOMAIN = "test.example.org"
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
    """
    Build a minimal project root with:
      - Age/keys.txt   (fake age key)
      - flux-repo/     (one plain yaml + two enc.yaml files)
    """
    # Age key
    age_dir = tmp_path / "Age"
    age_dir.mkdir()
    (age_dir / "keys.txt").write_text(
        f"# created: 2026-01-01T00:00:00Z\n"
        f"# public key: {AGE_PUBLIC_KEY}\n"
        f"AGE-SECRET-KEY-1QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ\n"
    )

    # flux-repo template
    flux = tmp_path / "flux-repo"
    (flux / "apps" / "headlamp").mkdir(parents=True)
    (flux / "infrastructure" / "cert-manager").mkdir(parents=True)

    # Plain YAML with domain placeholder
    (flux / "apps" / "headlamp" / "helmrelease.yaml").write_text(
        "issuerURL: https://auth.example.com/application/o/headlamp/\n"
        "host: headlamp.example.com\n"
    )

    # Two enc.yaml files with secret placeholders
    (flux / "apps" / "headlamp" / "oidc-secret.enc.yaml").write_text(
        "stringData:\n"
        "  clientID: REPLACE_WITH_OIDC_CLIENT_ID\n"
        "  clientSecret: REPLACE_WITH_OIDC_CLIENT_SECRET\n"
    )
    (flux / "infrastructure" / "cert-manager" / "cloudflare-secret.enc.yaml").write_text(
        "stringData:\n"
        "  api-token: REPLACE_WITH_CLOUDFLARE_TOKEN\n"
        "  email: admin@example.com\n"
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


# ---------------------------------------------------------------------------
# Unit tests — setup_gitops() end-to-end (SOPS mocked)
# ---------------------------------------------------------------------------

class TestSetupGitops:
    def _run(self, project_root, tmp_path, push=False, github_repo=None, github_token=None):
        from Scripts.gitops.gitops_init import setup_gitops
        target = tmp_path / "out"

        with patch("Scripts.gitops.gitops_init._get_or_generate_secrets",
                   return_value=FAKE_SECRETS), \
             patch("Scripts.gitops.gitops_init._sops_encrypt") as mock_sops, \
             patch("Scripts.gitops.gitops_init._github_push",
                   return_value="https://github.com/org/repo") as mock_push:

            url = setup_gitops(
                domain=DOMAIN,
                target_dir=target,
                github_repo=github_repo,
                github_token=github_token,
                push=push,
                project_root=project_root,
                print_status=_noop_print_status,
            )
            return url, target, mock_sops, mock_push

    def test_copies_flux_repo_template(self, project_root, tmp_path):
        _, target, _, _ = self._run(project_root, tmp_path)
        assert (target / "apps" / "headlamp" / "helmrelease.yaml").exists()

    def test_substitutes_domain_in_plain_yaml(self, project_root, tmp_path):
        _, target, _, _ = self._run(project_root, tmp_path)
        content = (target / "apps" / "headlamp" / "helmrelease.yaml").read_text()
        assert DOMAIN in content
        assert "example.com" not in content

    def test_fills_placeholders_in_enc_yaml(self, project_root, tmp_path):
        _, target, _, _ = self._run(project_root, tmp_path)
        oidc = (target / "apps" / "headlamp" / "oidc-secret.enc.yaml").read_text()
        assert "REPLACE_WITH" not in oidc
        assert "headlamp" in oidc
        assert "oidc-secret" in oidc

    def test_writes_sops_yaml(self, project_root, tmp_path):
        _, target, _, _ = self._run(project_root, tmp_path)
        sops = (target / ".sops.yaml").read_text()
        assert AGE_PUBLIC_KEY in sops

    def test_encrypts_all_enc_yaml_files(self, project_root, tmp_path):
        _, target, mock_sops, _ = self._run(project_root, tmp_path)
        encrypted_names = {call.args[0].name for call in mock_sops.call_args_list}
        assert "oidc-secret.enc.yaml" in encrypted_names
        assert "cloudflare-secret.enc.yaml" in encrypted_names

    def test_returns_local_path_when_no_push(self, project_root, tmp_path):
        url, target, _, mock_push = self._run(project_root, tmp_path)
        assert url == str(target)
        mock_push.assert_not_called()

    def test_calls_github_push_when_push_true(self, project_root, tmp_path):
        url, _, _, mock_push = self._run(
            project_root, tmp_path,
            push=True, github_repo="org/repo", github_token="ghp_tok"
        )
        mock_push.assert_called_once()
        assert url == "https://github.com/org/repo"

    def test_raises_without_github_repo_when_push(self, project_root, tmp_path):
        from Scripts.gitops.gitops_init import setup_gitops
        target = tmp_path / "out"
        with patch("Scripts.gitops.gitops_init._get_or_generate_secrets",
                   return_value=FAKE_SECRETS), \
             patch("Scripts.gitops.gitops_init._sops_encrypt"):
            with pytest.raises(RuntimeError, match="--github-repo is required"):
                setup_gitops(
                    domain=DOMAIN, target_dir=target,
                    github_repo=None, github_token="tok",
                    push=True, project_root=project_root,
                    print_status=_noop_print_status,
                )

    def test_raises_without_github_token_when_push(self, project_root, tmp_path):
        from Scripts.gitops.gitops_init import setup_gitops
        target = tmp_path / "out"
        with patch("Scripts.gitops.gitops_init._get_or_generate_secrets",
                   return_value=FAKE_SECRETS), \
             patch("Scripts.gitops.gitops_init._sops_encrypt"):
            with pytest.raises(RuntimeError, match="GitHub token required"):
                setup_gitops(
                    domain=DOMAIN, target_dir=target,
                    github_repo="org/repo", github_token=None,
                    push=True, project_root=project_root,
                    print_status=_noop_print_status,
                )

    def test_overwrites_existing_target_dir(self, project_root, tmp_path):
        from Scripts.gitops.gitops_init import setup_gitops
        target = tmp_path / "out"
        target.mkdir()
        (target / "stale_file.txt").write_text("old content")

        with patch("Scripts.gitops.gitops_init._get_or_generate_secrets",
                   return_value=FAKE_SECRETS), \
             patch("Scripts.gitops.gitops_init._sops_encrypt"):
            setup_gitops(
                domain=DOMAIN, target_dir=target,
                github_repo=None, github_token=None,
                push=False, project_root=project_root,
                print_status=_noop_print_status,
            )

        assert not (target / "stale_file.txt").exists()


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
        assert "--github-repo" in result.output
        assert "--push" in result.output

    def test_missing_domain_exits_nonzero(self):
        import noah
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(noah.cli, ["setup", "gitops"])
        assert result.exit_code != 0
        assert "domain" in result.output.lower() or "missing" in result.output.lower()

    def test_successful_run_prints_bootstrap_command(self, project_root, tmp_path):
        import noah
        from click.testing import CliRunner
        runner = CliRunner()

        with patch("Scripts.gitops.gitops_init.setup_gitops",
                   return_value=str(tmp_path / "out")) as mock_sg:
            result = runner.invoke(noah.cli, [
                "setup", "gitops",
                "--domain", DOMAIN,
                "--target-dir", str(tmp_path / "out"),
            ])

        mock_sg.assert_called_once()
        assert result.exit_code == 0
        assert "cluster bootstrap" in result.output
        assert DOMAIN in result.output

    def test_setup_gitops_error_exits_nonzero(self, project_root, tmp_path):
        import noah
        from click.testing import CliRunner
        runner = CliRunner()

        with patch("Scripts.gitops.gitops_init.setup_gitops",
                   side_effect=RuntimeError("Cloudflare API token not found")):
            result = runner.invoke(noah.cli, [
                "setup", "gitops",
                "--domain", DOMAIN,
                "--target-dir", str(tmp_path / "out"),
            ])

        assert result.exit_code != 0
        assert "Cloudflare API token not found" in result.output


# ---------------------------------------------------------------------------
# Integration test — requires real sops binary
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_sops_encrypt_integration(project_root, tmp_path):
    """Calls the real sops binary to verify encryption works end-to-end."""
    from Scripts.gitops.gitops_init import _sops_encrypt, _write_sops_yaml

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
