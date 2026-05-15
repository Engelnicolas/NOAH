#!/usr/bin/env python3
"""Unit and integration tests for SopsClient.

Unit tests run without the SOPS binary by injecting a mock runner.
Integration tests require the real sops binary and are marked with
@pytest.mark.integration -- they are excluded from the standard CI pipeline.

Run unit tests only:
    pytest Tests/test_sops_client.py -m "not integration"

Run all tests (requires sops binary):
    pytest Tests/test_sops_client.py
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.security.sops_client import (
    SopsClient,
    SopsBinaryNotFoundError,
    SopsConfigError,
    SopsDecryptionError,
    SopsEncryptionError,
    SopsError,
    SopsKeyError,
    SopsTimeoutError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _mock_runner(returncode: int, stdout: str = "", stderr: str = ""):
    """Return a runner callable that always returns the given result."""
    def runner(cmd):
        return _make_completed(returncode, stdout, stderr)
    return runner


def _fake_key_file(tmp_path: Path) -> Path:
    """Create a fake (but existent + readable) Age key file."""
    key_file = tmp_path / "keys.txt"
    key_file.write_text("# public key: age1fakekey\nAGE-SECRET-KEY-1FAKE\n")
    return key_file


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_all_subclass_sops_error(self):
        for cls in (
            SopsBinaryNotFoundError,
            SopsKeyError,
            SopsDecryptionError,
            SopsEncryptionError,
            SopsConfigError,
            SopsTimeoutError,
        ):
            assert issubclass(cls, SopsError)

    def test_detail_attribute(self):
        err = SopsDecryptionError("msg", detail="raw stderr")
        assert err.detail == "raw stderr"
        assert str(err) == "msg"

    def test_detail_defaults_to_empty_string(self):
        err = SopsError("msg")
        assert err.detail == ""


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

class TestConstructorValidation:
    def test_raises_key_error_when_age_key_missing(self, tmp_path):
        missing = tmp_path / "nonexistent" / "keys.txt"
        with pytest.raises(SopsKeyError):
            SopsClient(age_key_file=missing)

    def test_no_raise_when_runner_injected_and_key_missing(self, tmp_path):
        """With a custom _runner, init-time validation is skipped."""
        missing = tmp_path / "nonexistent" / "keys.txt"
        client = SopsClient(age_key_file=missing, _runner=_mock_runner(0))
        assert client is not None

    def test_accepts_valid_key_file(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        # is_available() may return False in CI; skip binary check via _runner
        client = SopsClient(age_key_file=key_file, _runner=_mock_runner(0))
        assert client.age_key_file == key_file


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_enter_returns_self(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        client = SopsClient(key_file, _runner=_mock_runner(0))
        with client as ctx:
            assert ctx is client

    def test_exit_returns_false_does_not_suppress(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        client = SopsClient(key_file, _runner=_mock_runner(0))
        with pytest.raises(ValueError):
            with client:
                raise ValueError("should propagate")

    def test_sops_error_propagates_out_of_context(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        client = SopsClient(key_file, _runner=_mock_runner(1, stderr="mac mismatch"))
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("sops: {}")
        with pytest.raises(SopsDecryptionError):
            with client:
                client.decrypt_to_string(enc_file)


# ---------------------------------------------------------------------------
# decrypt_to_string
# ---------------------------------------------------------------------------

class TestDecryptToString:
    def test_success_returns_stdout(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(0, stdout="db_password: secret\n")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        result = client.decrypt_to_string(enc_file)
        assert result == "db_password: secret\n"

    def test_returncode_128_raises_key_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(128, stderr="Failed to get the data key")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        with pytest.raises(SopsKeyError) as exc_info:
            client.decrypt_to_string(enc_file)
        assert exc_info.value.detail == "Failed to get the data key"

    def test_returncode_1_mac_mismatch_raises_decryption_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(1, stderr="mac mismatch")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        with pytest.raises(SopsDecryptionError):
            client.decrypt_to_string(enc_file)

    def test_returncode_1_could_not_decrypt_raises_decryption_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(1, stderr="could not decrypt")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        with pytest.raises(SopsDecryptionError):
            client.decrypt_to_string(enc_file)

    def test_returncode_1_config_error_raises_config_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(1, stderr="error loading config: creation_rules")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        with pytest.raises(SopsConfigError):
            client.decrypt_to_string(enc_file)

    def test_returncode_1_generic_raises_sops_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(1, stderr="something unexpected happened")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        with pytest.raises(SopsError):
            client.decrypt_to_string(enc_file)

    def test_returncode_2_raises_encryption_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(2, stderr="encryption error")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        with pytest.raises(SopsEncryptionError):
            client.decrypt_to_string(enc_file)


# ---------------------------------------------------------------------------
# decrypt_yaml
# ---------------------------------------------------------------------------

class TestDecryptYaml:
    def test_returns_parsed_dict(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(0, stdout="db_password: secret\nhost: localhost\n")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        result = client.decrypt_yaml(enc_file)
        assert result == {"db_password": "secret", "host": "localhost"}

    def test_empty_output_returns_empty_dict(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        runner = _mock_runner(0, stdout="")
        client = SopsClient(key_file, _runner=runner)
        enc_file = tmp_path / "test.enc.yaml"
        enc_file.write_text("placeholder")
        result = client.decrypt_yaml(enc_file)
        assert result == {}


# ---------------------------------------------------------------------------
# encrypt_in_place (atomicity)
# ---------------------------------------------------------------------------

class TestEncryptInPlace:
    def test_success_replaces_file_with_encrypted_content(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        plaintext = tmp_path / "secrets.yaml"
        plaintext.write_text("password: hunter2\n")
        encrypted_content = "ENC[AES256_GCM,data:abc,type:str]\nsops: {}\n"

        def runner(cmd):
            # Simulate: sops -e --in-place <tmp_file>
            # Find the tmp file path from cmd (last arg)
            tmp_file = Path(cmd[-1])
            tmp_file.write_text(encrypted_content)
            return _make_completed(0)

        client = SopsClient(key_file, _runner=runner)
        client.encrypt_in_place(plaintext)
        assert plaintext.read_text() == encrypted_content

    def test_failure_raises_encryption_error_and_leaves_original(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        plaintext = tmp_path / "secrets.yaml"
        original_content = "password: hunter2\n"
        plaintext.write_text(original_content)

        runner = _mock_runner(1, stderr="encryption failed")
        client = SopsClient(key_file, _runner=runner)

        with pytest.raises(SopsEncryptionError):
            client.encrypt_in_place(plaintext)

        # Original file must still be intact
        assert plaintext.read_text() == original_content

    def test_no_temp_file_left_on_failure(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        plaintext = tmp_path / "secrets.yaml"
        plaintext.write_text("password: hunter2\n")

        runner = _mock_runner(1, stderr="encryption failed")
        client = SopsClient(key_file, _runner=runner)

        before = set(tmp_path.iterdir())
        with pytest.raises(SopsEncryptionError):
            client.encrypt_in_place(plaintext)
        after = set(tmp_path.iterdir())
        # No new files left behind
        assert after == before


# ---------------------------------------------------------------------------
# encrypt_to
# ---------------------------------------------------------------------------

class TestEncryptTo:
    def test_success_calls_sops_with_correct_args(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        source = tmp_path / "plain.yaml"
        dest = tmp_path / "plain.enc.yaml"
        source.write_text("key: value\n")
        captured = {}

        def runner(cmd):
            captured["cmd"] = cmd
            dest.write_text("ENC[...]\n")
            return _make_completed(0)

        client = SopsClient(key_file, _runner=runner)
        client.encrypt_to(source, dest)
        assert "--encrypt" in captured["cmd"]
        assert "--output" in captured["cmd"]
        assert str(dest) in captured["cmd"]
        assert str(source) in captured["cmd"]

    def test_failure_raises_encryption_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        source = tmp_path / "plain.yaml"
        dest = tmp_path / "plain.enc.yaml"
        source.write_text("key: value\n")
        runner = _mock_runner(1, stderr="encrypt failure")
        client = SopsClient(key_file, _runner=runner)
        with pytest.raises(SopsEncryptionError):
            client.encrypt_to(source, dest)


# ---------------------------------------------------------------------------
# _build_env
# ---------------------------------------------------------------------------

class TestBuildEnv:
    def test_sets_sops_age_key_file(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        client = SopsClient(key_file, _runner=_mock_runner(0))
        env = client._build_env()
        assert env["SOPS_AGE_KEY_FILE"] == str(key_file)

    def test_sets_sops_config_when_present(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        sops_cfg = tmp_path / ".sops.yaml"
        sops_cfg.write_text("creation_rules: []\n")
        client = SopsClient(key_file, sops_config=sops_cfg, _runner=_mock_runner(0))
        env = client._build_env()
        assert env.get("SOPS_CONFIG") == str(sops_cfg)

    def test_does_not_set_sops_config_when_absent(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        missing_cfg = tmp_path / ".sops.yaml"  # does not exist
        client = SopsClient(key_file, sops_config=missing_cfg, _runner=_mock_runner(0))
        env = client._build_env()
        assert "SOPS_CONFIG" not in env

    def test_reflects_os_environ_mutations(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        client = SopsClient(key_file, _runner=_mock_runner(0))
        os.environ["NOAH_TEST_VAR_12345"] = "present"
        try:
            env = client._build_env()
            assert env.get("NOAH_TEST_VAR_12345") == "present"
        finally:
            del os.environ["NOAH_TEST_VAR_12345"]


# ---------------------------------------------------------------------------
# _default_run -- timeout and binary-not-found
# ---------------------------------------------------------------------------

class TestDefaultRun:
    def test_timeout_raises_sops_timeout_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        # Real client (no injected runner) but we patch subprocess.run
        client = SopsClient.__new__(SopsClient)
        client.age_key_file = key_file
        client.sops_config = None
        client.timeout = 5
        client._run_fn = client._default_run

        with patch(
            "Scripts.security.sops_client.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["sops"], timeout=5),
        ):
            with pytest.raises(SopsTimeoutError):
                client._default_run(["sops", "-d", "file.yaml"])

    def test_binary_not_found_raises_sops_binary_not_found_error(self, tmp_path):
        key_file = _fake_key_file(tmp_path)
        client = SopsClient.__new__(SopsClient)
        client.age_key_file = key_file
        client.sops_config = None
        client.timeout = 5
        client._run_fn = client._default_run

        with patch(
            "Scripts.security.sops_client.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(SopsBinaryNotFoundError):
                client._default_run(["sops", "-d", "file.yaml"])


# ---------------------------------------------------------------------------
# is_available (static)
# ---------------------------------------------------------------------------

class TestIsAvailable:
    def test_returns_true_when_sops_exits_zero(self):
        with patch(
            "Scripts.security.sops_client.subprocess.run",
            return_value=_make_completed(0),
        ):
            assert SopsClient.is_available() is True

    def test_returns_false_when_sops_exits_nonzero(self):
        with patch(
            "Scripts.security.sops_client.subprocess.run",
            return_value=_make_completed(1),
        ):
            assert SopsClient.is_available() is False

    def test_returns_false_when_binary_missing(self):
        with patch(
            "Scripts.security.sops_client.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            assert SopsClient.is_available() is False

    def test_never_raises(self):
        with patch(
            "Scripts.security.sops_client.subprocess.run",
            side_effect=Exception("unexpected"),
        ):
            # Must not propagate
            result = SopsClient.is_available()
            assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Integration tests (require real sops binary)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestIntegration:
    """Requires the sops binary and a valid Age key in the environment."""

    @pytest.fixture(autouse=True)
    def skip_if_no_sops(self):
        if not SopsClient.is_available():
            pytest.skip("sops binary not available")

    @pytest.fixture
    def age_key(self, tmp_path):
        """Generate a real Age key for testing."""
        key_file = tmp_path / "keys.txt"
        result = subprocess.run(
            ["age-keygen", "-o", str(key_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("age-keygen not available")
        return key_file

    @pytest.fixture
    def sops_config(self, tmp_path, age_key):
        """Write a minimal .sops.yaml pointing at our test Age key."""
        pub_key = None
        for line in age_key.read_text().splitlines():
            if line.startswith("# public key:"):
                pub_key = line.split(":", 1)[1].strip()
                break
        if not pub_key:
            pytest.skip("Could not extract Age public key")

        cfg = tmp_path / ".sops.yaml"
        cfg.write_text(
            f"creation_rules:\n  - path_regex: '.*\\.enc\\.yaml$'\n    age: {pub_key}\n"
        )
        return cfg

    def test_round_trip_decrypt_yaml(self, tmp_path, age_key, sops_config):
        plaintext_file = tmp_path / "secret.yaml"
        plaintext_file.write_text("db_password: hunter2\nhost: localhost\n")

        enc_file = tmp_path / "secret.enc.yaml"
        with SopsClient(age_key, sops_config) as sops:
            sops.encrypt_to(plaintext_file, enc_file)

        assert enc_file.exists()

        with SopsClient(age_key, sops_config) as sops:
            result = sops.decrypt_yaml(enc_file)

        assert result["db_password"] == "hunter2"
        assert result["host"] == "localhost"

    def test_encrypt_in_place_atomicity(self, tmp_path, age_key, sops_config):
        plaintext_file = tmp_path / "secret.enc.yaml"
        plaintext_file.write_text("api_key: top_secret\n")

        with SopsClient(age_key, sops_config) as sops:
            sops.encrypt_in_place(plaintext_file)

        # File must exist and be encrypted (not plain YAML)
        content = plaintext_file.read_text()
        assert "top_secret" not in content
        assert "sops" in content.lower()

    def test_decrypt_to_string_returns_raw_yaml(self, tmp_path, age_key, sops_config):
        plaintext_file = tmp_path / "secret.yaml"
        plaintext_file.write_text("token: abc123\n")
        enc_file = tmp_path / "secret.enc.yaml"

        with SopsClient(age_key, sops_config) as sops:
            sops.encrypt_to(plaintext_file, enc_file)
            raw = sops.decrypt_to_string(enc_file)

        assert "token" in raw
        assert "abc123" in raw
