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

"""Garage administration secrets — the third secret domain (§3.1, decision G1).

Why a second store at all
-------------------------
NOAH hands the cluster's Age private key to the compute node (it becomes the
`sops-age` Secret in flux-system, so kustomize-controller can decrypt). Anyone
who reaches cluster-admin, escapes a container, or gets root on that node can
therefore read the whole canonical store. That is accepted for the S3
*consumption* keys — being read by the cluster is their purpose — and it is
unacceptable for anything that grants access to the Garage machines
themselves.

This module holds that second set:

  * the SSH key of the Garage nodes,
  * `rpc_secret` (whoever has it joins the Garage cluster),
  * the admin API token,
  * the `owner`-class S3 key,
  * the cloud provider API credentials (G13 — a token that can snapshot the
    Garage volumes reads all of Garage without ever touching a machine),
  * the OpenTofu state encryption passphrase (G14).

The test is never "is this a Garage secret", it is **"does this grant access to
the Garage data"**.

Everything is encrypted to `Age/garage-admin.txt`, an identity that is never
transmitted to any node and never leaves the operator workstation. The
canonical store refuses these keys outright (canonical_store.ADMIN_ONLY_KEYS),
so the separation cannot be lost by accident.

The class is a subclass of CanonicalSecretsStore rather than a rewrite: the
atomic 0600 write, the environment lock and the integrity hash are exactly the
guarantees this store needs, and duplicating them would mean maintaining two
copies of the same care.
"""

from __future__ import annotations

import os
import secrets
import stat
import subprocess
import tempfile
from pathlib import Path

from Scripts.security.canonical_store import (
    CanonicalSecretsStore,
    SopsEncryptionError,
)

GARAGE_ADMIN_FILENAME_ENCRYPTED = "garage-admin.enc.yaml"
GARAGE_ADMIN_FILENAME_PLAINTEXT = "garage-admin.yaml"

#: Service key under which every domain-3 secret is filed.
ADMIN_SERVICE = "garage-admin"

#: Service key for the cloud provider API credentials (G13). Kept apart from
#: ADMIN_SERVICE so `noah garage admin show` can list one without the other.
CLOUD_SERVICE = "cloud-provider"

#: pbkdf2 imposes a 16-character floor on the state passphrase (G14); 32 hex
#: characters clears it without asking the operator to invent one.
_TOFU_PASSPHRASE_BYTES = 16


class GarageAdminIdentityError(RuntimeError):
    """The domain-3 Age identity is missing, unreadable, or not distinct.

    Not derived from SopsError, for the same reason InsecureStoreError is not:
    it is a policy refusal and must not be caught by the SOPS handlers.
    """


def resolve_admin_age_key_file(project_root: Path) -> Path:
    """`GARAGE_ADMIN_AGE_KEY_FILE` when set, else <root>/Age/garage-admin.txt.

    Honouring the variable is what lets the identity live off the repository —
    on a removable medium, in escrow (lot 7) — without downgrading the store.
    """
    env_key = os.environ.get("GARAGE_ADMIN_AGE_KEY_FILE")
    return Path(env_key) if env_key else project_root / "Age" / "garage-admin.txt"


def _age_public_key(age_key_file: Path) -> str | None:
    """Read the `# public key:` line out of an age-keygen file."""
    try:
        content = age_key_file.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in content.splitlines():
        if line.startswith("# public key:"):
            return line.split(":", 1)[1].strip()
    return None


def create_admin_identity(project_root: Path, *, force: bool = False) -> Path:
    """Generate `Age/garage-admin.txt` and return its path.

    Refuses to overwrite an existing identity unless *force* is set: losing it
    makes every domain-3 secret unrecoverable, and a re-run of a setup command
    is not an intent to destroy them.
    """
    key_file = resolve_admin_age_key_file(project_root)
    if key_file.exists() and not force:
        return key_file

    key_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        result = subprocess.run(["age-keygen"], capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise GarageAdminIdentityError(
            "age-keygen not found. Install age "
            "(https://github.com/FiloSottile/age) or run "
            "`python3 noah.py setup initialize`."
        ) from exc
    if result.returncode != 0:
        raise GarageAdminIdentityError(
            f"age-keygen failed: {result.stderr.strip()}"
        )

    # mkstemp + replace, so the identity is never briefly world-readable.
    fd, tmp_str = tempfile.mkstemp(dir=key_file.parent, prefix=".garage-admin-")
    tmp = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(result.stdout)
        os.replace(tmp, key_file)
    finally:
        tmp.unlink(missing_ok=True)
    os.chmod(key_file, 0o600)
    return key_file


def require_admin_identity(project_root: Path) -> Path:
    """Return the domain-3 identity path, or refuse.

    Called before anything reaches out to a Garage node (T4): deploying first
    and discovering afterwards that there is nowhere safe to file the rpc
    secret is how domain-3 secrets end up in the canonical store.
    """
    key_file = resolve_admin_age_key_file(project_root)
    if not key_file.exists():
        raise GarageAdminIdentityError(
            f"Garage administration Age identity not found: {key_file}\n"
            "  Create it with `python3 noah.py garage admin init`.\n"
            "  It is the second secret domain (Garage.md §3.1): it is never "
            "sent to any node, and it must NOT be Age/keys.txt."
        )
    cluster_key = project_root / "Age" / "keys.txt"
    if key_file.resolve() == cluster_key.resolve():
        raise GarageAdminIdentityError(
            "The Garage administration identity is the cluster identity "
            f"({key_file}). The cluster key is handed to the compute node as "
            "the sops-age Secret, so this would publish every Garage "
            "administration secret to the very node condition 3 of §10.2 keeps "
            "them from."
        )
    admin_pub = _age_public_key(key_file)
    cluster_pub = _age_public_key(cluster_key)
    if admin_pub and cluster_pub and admin_pub == cluster_pub:
        raise GarageAdminIdentityError(
            "The Garage administration identity has the same public key as the "
            "cluster identity. Two files, one identity, is the same leak: "
            "regenerate one of them."
        )
    return key_file


class GarageAdminStore(CanonicalSecretsStore):
    """Secret domain 3 — same store machinery, second Age identity.

    Three overrides and nothing else: where the identity lives, where the file
    lives, and which recipient it is encrypted to. Everything the canonical
    store does about atomicity, the plaintext lock and integrity is inherited
    verbatim.
    """

    # This IS the domain the canonical store refuses to hold.
    _forbidden_services = frozenset()
    _forbidden_keys = frozenset()

    def _resolve_age_key_file(self) -> Path:
        return resolve_admin_age_key_file(self.project_root)

    def _encrypted_path(self) -> Path:
        return self.secrets_dir / GARAGE_ADMIN_FILENAME_ENCRYPTED

    def _plaintext_path(self) -> Path:
        return self.secrets_dir / GARAGE_ADMIN_FILENAME_PLAINTEXT

    def __post_init__(self):
        super().__post_init__()
        if self.encrypted:
            # Only meaningful when something is actually being encrypted; in a
            # plaintext dev/test store there is no recipient to confuse.
            require_admin_identity(self.project_root)

    def _encrypt_in_place(self, path: Path) -> bool:
        """Encrypt to the domain-3 recipient EXPLICITLY.

        The repository's .sops.yaml has a single creation rule matching
        `.*\\.enc\\.yaml$` with the CLUSTER's Age recipient. Falling back on it
        here would file every administration secret under a key the compute
        node holds — acceptance criterion 2 fails by construction, and nothing
        in the output would say so. `--age` on the command line overrides the
        creation rules, which is exactly what this store needs.

        Raises rather than returning False on failure: save() ignores a False
        return in most call paths, which would lose an administration secret
        without a word.
        """
        if not self.encrypted:
            return True
        recipient = _age_public_key(self.age_key_file)
        if not recipient:
            raise GarageAdminIdentityError(
                f"No `# public key:` line in {self.age_key_file}; cannot "
                "determine the recipient to encrypt the administration store to."
            )
        env = {**os.environ, "SOPS_AGE_KEY_FILE": str(self.age_key_file)}
        result = subprocess.run(
            ["sops", "--encrypt", "--age", recipient, "--in-place", str(path)],
            env=env, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SopsEncryptionError(
                "SOPS encryption of the Garage administration store failed",
                detail=result.stderr,
            )
        return True


_admin_store_instance: GarageAdminStore | None = None


def get_admin_store(project_root: Path | None = None) -> GarageAdminStore:
    global _admin_store_instance
    if _admin_store_instance is None:
        _admin_store_instance = GarageAdminStore(project_root or Path.cwd())
    return _admin_store_instance


# ---------------------------------------------------------------------------
# Generators — domain 3 secrets
# ---------------------------------------------------------------------------

def _hex(nbytes: int) -> str:
    return secrets.token_hex(nbytes)


def _garage_access_key_id() -> str:
    """`GK` + 24 hex characters — the shape Garage itself emits (§6.2)."""
    return "GK" + secrets.token_hex(12)


def _garage_secret_key() -> str:
    """64 hex characters — the shape Garage itself emits (§6.2)."""
    return secrets.token_hex(32)


def ensure_admin_secrets(store: GarageAdminStore) -> dict[str, str]:
    """Create the domain-3 secrets that do not exist yet, return them all.

    Idempotent by construction (ensure_service_entries only fills blanks), so
    a re-run of `garage deploy` reuses the rpc secret the nodes already agreed
    on rather than splitting the cluster in two.
    """
    return store.ensure_service_entries(ADMIN_SERVICE, {
        # 32 bytes hex, identical on every node — `openssl rand -hex 32` (§5).
        "rpc_secret": lambda: _hex(32),
        "admin_token": lambda: _hex(32),
        # owner-class S3 key: stays in domain 3, never delivered to the cluster.
        "owner_access_key_id": _garage_access_key_id,
        "owner_secret_key": _garage_secret_key,
        # G14 — pbkdf2 floor is 16 characters; 32 hex clears it.
        "tofu_state_passphrase": lambda: _hex(_TOFU_PASSPHRASE_BYTES),
    })


def ensure_ssh_key(store: GarageAdminStore) -> tuple[str, str]:
    """Return (private, public) for the Garage node SSH key, creating it once.

    The private half lives encrypted in this store and is materialised to a
    0600 file only for the duration of an Ansible run. It is never copied to
    the bastion: `ProxyJump` carries the connection, it does not hold the key
    (G20). A key on the compute node would hand storage-tier access to whoever
    gets root there — precisely what T2 exists to prevent.
    """
    existing = store.get_service_secrets(ADMIN_SERVICE)
    if existing.get("ssh_private_key") and existing.get("ssh_public_key"):
        return existing["ssh_private_key"], existing["ssh_public_key"]

    with tempfile.TemporaryDirectory(prefix="noah-garage-key-") as tmpdir:
        key_path = Path(tmpdir) / "garage-admin"
        result = subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-N", "", "-C",
             "noah-garage-admin", "-f", str(key_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise GarageAdminIdentityError(
                f"ssh-keygen failed: {result.stderr.strip()}"
            )
        private = key_path.read_text(encoding="utf-8")
        public = key_path.with_suffix(".pub").read_text(encoding="utf-8")

    pair = store.ensure_service_entries(ADMIN_SERVICE, {
        "ssh_private_key": lambda: private,
        "ssh_public_key": lambda: public,
    })
    return pair["ssh_private_key"], pair["ssh_public_key"]


def materialize_ssh_key(store: GarageAdminStore, directory: Path) -> Path:
    """Write the domain-3 SSH private key into *directory* at 0600.

    *directory* is expected to be a TemporaryDirectory owned by the caller, so
    the key exists on disk only while ansible-playbook is running.
    """
    private, _public = ensure_ssh_key(store)
    key_path = Path(directory) / "garage-admin-key"
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(private if private.endswith("\n") else private + "\n")
    return key_path


def set_cloud_credentials(store: GarageAdminStore, provider: str, **values: str) -> None:
    """File cloud provider API credentials in domain 3 (G13).

    A token that can `CreateSnapshot` on the Garage volumes reads all of Garage
    without ever touching a machine — same status as the SSH key, so same
    store. Never `~/.aws/credentials`, never a `.tfvars`.
    """
    store.ensure_service(CLOUD_SERVICE)
    svc = store.data["services"][CLOUD_SERVICE]
    entry = svc.setdefault(provider, {})
    if not isinstance(entry, dict):  # legacy scalar, replaced wholesale
        entry = {}
    entry.update({k: v for k, v in values.items() if v})
    svc[provider] = entry
    store.save()


def get_cloud_credentials(store: GarageAdminStore, provider: str) -> dict[str, str]:
    svc = store.data.get("services", {}).get(CLOUD_SERVICE, {}) or {}
    entry = svc.get(provider) or {}
    return dict(entry) if isinstance(entry, dict) else {}


def tofu_environment(store: GarageAdminStore, provider: str = "aws") -> dict[str, str]:
    """Environment for a `tofu` invocation, built from domain 3 only.

    The state passphrase arrives as TF_VAR_state_passphrase, consumed by a
    variable that has NO default: OpenTofu then fails immediately when it is
    absent instead of writing the state in the clear (G14, §16.5).
    """
    admin = store.get_service_secrets(ADMIN_SERVICE)
    env = {"TF_VAR_state_passphrase": admin.get("tofu_state_passphrase", "")}
    creds = get_cloud_credentials(store, provider)
    if provider == "aws":
        if creds.get("access_key_id"):
            env["AWS_ACCESS_KEY_ID"] = creds["access_key_id"]
        if creds.get("secret_access_key"):
            env["AWS_SECRET_ACCESS_KEY"] = creds["secret_access_key"]
        if creds.get("session_token"):
            env["AWS_SESSION_TOKEN"] = creds["session_token"]
        if creds.get("region"):
            env["AWS_REGION"] = creds["region"]
    return env
