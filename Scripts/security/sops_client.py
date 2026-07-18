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

"""SopsClient -- Contextual SOPS wrapper for NOAH.

Provides a typed, testable interface over the SOPS binary, replacing the
scattered subprocess.run("sops", ...) call sites throughout the codebase.

Exception hierarchy
-------------------
SopsError (base)
 ├── SopsBinaryNotFoundError   sops binary absent from PATH
 ├── SopsKeyError              Age key missing or unreadable
 ├── SopsDecryptionError       decryption failure (corrupted file, wrong key)
 ├── SopsEncryptionError       encryption failure
 ├── SopsConfigError           .sops.yaml missing or invalid
 └── SopsTimeoutError          subprocess exceeded the configured timeout

Every exception carries the raw SOPS stderr in its .detail attribute to aid
logging and debugging without accidentally leaking it in user-facing messages.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class SopsError(Exception):
    """Base exception for all SOPS-related errors."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail

    def __str__(self) -> str:
        return super().__str__()


class SopsBinaryNotFoundError(SopsError):
    """sops binary is absent from PATH."""


class SopsKeyError(SopsError):
    """Age key is missing or unreadable."""


class SopsDecryptionError(SopsError):
    """Decryption failure (corrupted file or wrong key)."""


class SopsEncryptionError(SopsError):
    """Encryption failure."""


class SopsConfigError(SopsError):
    """.sops.yaml is missing or invalid."""


class SopsTimeoutError(SopsError):
    """Subprocess exceeded the configured timeout."""


# ---------------------------------------------------------------------------
# SopsClient
# ---------------------------------------------------------------------------

class SopsClient:
    """Typed, testable wrapper around the SOPS binary.

    Parameters
    ----------
    age_key_file:
        Path to Age/keys.txt -- validated at init time.
    sops_config:
        Path to .sops.yaml -- optional, used when present.
    timeout:
        Subprocess timeout in seconds (default: 30).
    _runner:
        Optional callable used instead of subprocess.run, enabling unit tests
        without the SOPS binary. Must accept a list[str] and return a
        subprocess.CompletedProcess.
    """

    def __init__(
        self,
        age_key_file: Path,
        sops_config: Optional[Path] = None,
        timeout: int = 30,
        _runner: Optional[Callable[[list[str]], subprocess.CompletedProcess]] = None,
    ) -> None:
        self.age_key_file = Path(age_key_file)
        self.sops_config = Path(sops_config) if sops_config else None
        self.timeout = timeout
        self._run_fn = _runner or self._default_run

        # Validate at init time so failures surface immediately.
        if _runner is None:
            self._validate()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "SopsClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Never suppress exceptions. Log unexpected non-SOPS errors.
        if exc_type is not None and not issubclass(exc_type, SopsError):
            logger.error(
                "Unexpected error inside SopsClient context: %s: %s",
                exc_type.__name__,
                exc_val,
            )
        return False

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def decrypt_yaml(self, path: Path) -> dict:
        """Decrypt a .enc.yaml file and return the parsed Python dict.

        Raises
        ------
        SopsDecryptionError
            If the file is corrupted or the key is invalid.
        SopsKeyError
            If the Age key file is missing or unreadable.
        """
        raw = self.decrypt_to_string(path)
        return yaml.safe_load(raw) or {}

    def decrypt_to_string(self, path: Path) -> str:
        """Return the raw decrypted content as a string without parsing it.

        Useful for callers (e.g. secure_env_loader) that handle their own
        YAML parsing.

        Raises
        ------
        SopsDecryptionError
            If decryption fails.
        SopsKeyError
            If the Age key is unavailable.
        """
        result = self._run(["sops", "-d", str(path)])
        if result.returncode != 0:
            self._raise_for_decrypt_error(result.returncode, result.stderr)
        return result.stdout

    def encrypt_in_place(self, path: Path) -> None:
        """Encrypt *path* in place (equivalent to ``sops -e --in-place``).

        Atomic: uses a temporary file + rename to prevent file corruption
        if SOPS crashes mid-write.

        Raises
        ------
        SopsEncryptionError
            If encryption fails.
        """
        path = Path(path)
        tmp_path: Optional[Path] = None
        try:
            # 1. Copy plaintext to a temp file in the same directory.
            # Suffix must match a .sops.yaml creation rule so SOPS can find the key.
            fd, tmp_str = tempfile.mkstemp(dir=path.parent, suffix=".enc.yaml")
            tmp_path = Path(tmp_str)
            os.close(fd)
            tmp_path.write_bytes(path.read_bytes())

            # 2. Encrypt the temp file in place.
            result = self._run(["sops", "-e", "--in-place", str(tmp_path)])
            if result.returncode != 0:
                raise SopsEncryptionError(
                    f"SOPS encryption failed for {path.name}",
                    detail=result.stderr,
                )

            # 3. Atomic replace: encrypted temp overwrites original.
            os.replace(tmp_path, path)
            tmp_path = None  # ownership transferred
        except SopsEncryptionError:
            raise
        except Exception as exc:
            raise SopsEncryptionError(
                f"Unexpected error during encryption of {path.name}: {exc}",
                detail="",
            ) from exc
        finally:
            # 4. On failure: clean up the temporary file.
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def encrypt_to(self, source: Path, destination: Path) -> None:
        """Encrypt *source* to *destination* without modifying *source*.

        Raises
        ------
        SopsEncryptionError
            If encryption fails.
        """
        result = self._run(
            ["sops", "--encrypt", "--output", str(destination), str(source)]
        )
        if result.returncode != 0:
            raise SopsEncryptionError(
                f"SOPS encryption failed: {source.name} -> {destination.name}",
                detail=result.stderr,
            )

    @staticmethod
    def is_available() -> bool:
        """Return True if the sops binary is present in PATH.

        Never raises -- intended for conditional checks such as
        ``_should_encrypt()``.
        """
        try:
            result = subprocess.run(
                ["sops", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Raise early if the Age key is missing or unreadable."""
        if not self.age_key_file.exists():
            raise SopsKeyError(
                f"Age key file not found: {self.age_key_file}",
                detail="",
            )
        if not os.access(self.age_key_file, os.R_OK):
            raise SopsKeyError(
                f"Age key file is not readable: {self.age_key_file}",
                detail="",
            )

    def _build_env(self) -> dict[str, str]:
        """Build the subprocess environment for every SOPS call.

        Rebuilt on every call so that mutations to os.environ between calls
        are always reflected.
        """
        env = os.environ.copy()
        env["SOPS_AGE_KEY_FILE"] = str(self.age_key_file)
        if self.sops_config and self.sops_config.exists():
            env["SOPS_CONFIG"] = str(self.sops_config)
        return env

    def _default_run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Execute *cmd* with timeout and environment injection."""
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self._build_env(),
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise SopsTimeoutError(
                f"SOPS command timed out after {self.timeout}s: {cmd}",
                detail="",
            ) from exc
        except FileNotFoundError as exc:
            raise SopsBinaryNotFoundError(
                "SOPS binary not found in PATH. "
                "Install via: https://github.com/getsops/sops",
                detail="",
            ) from exc

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Dispatch to either the injected runner or the real subprocess."""
        return self._run_fn(cmd)

    def _raise_for_decrypt_error(self, returncode: int, stderr: str) -> None:
        """Map a non-zero returncode + stderr to a typed exception.

        SOPS exit codes (documented):
          0   success
          1   generic error (decryption failure, config error, etc.)
          2   encryption failure
          128 key-related error
        """
        stderr_lower = stderr.lower()

        if returncode == 128 or "key" in stderr_lower:
            raise SopsKeyError(
                "Age key unavailable or invalid for decryption",
                detail=stderr,
            )

        if returncode == 1:
            if "mac mismatch" in stderr_lower or "could not decrypt" in stderr_lower:
                raise SopsDecryptionError(
                    "SOPS decryption failed: file may be corrupted or wrong key",
                    detail=stderr,
                )
            if "config" in stderr_lower or "creation_rules" in stderr_lower:
                raise SopsConfigError(
                    "SOPS configuration error",
                    detail=stderr,
                )
            # Generic exit-code-1 fallback
            raise SopsError(
                "SOPS decryption failed",
                detail=stderr,
            )

        if returncode == 2:
            raise SopsEncryptionError(
                "SOPS encryption failed",
                detail=stderr,
            )

        # Unknown non-zero code
        raise SopsError(
            f"SOPS exited with unexpected code {returncode}",
            detail=stderr,
        )
