"""
Automates preparation of the NOAH GitOps repository (gitops/ subdirectory):
  1. Substitute the example.com / ${DOMAIN} placeholder domain
  2. Load secrets from the canonical store (generating missing ones automatically)
  3. Decrypt any already-encrypted *.enc.yaml files (idempotent re-runs)
  4. Fill *.enc.yaml placeholders
  5. Write .sops.yaml from the local Age public key
  6. SOPS-encrypt every *.enc.yaml in-place

The gitops/ directory is part of the NOAH mono-repo.  After running this
command, commit and push the NOAH repo to GitHub so Flux can reconcile:
    git add gitops/ && git commit -m 'chore: update GitOps configuration'
    git push origin main
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=check)


def _age_public_key(project_root: Path) -> str:
    key_file = project_root / "Age" / "keys.txt"
    if not key_file.exists():
        raise RuntimeError(
            "Age key not found. Run 'python3 noah.py setup initialize' first."
        )
    for line in key_file.read_text().splitlines():
        if line.startswith("# public key:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("age1"):
            return line.strip()
    raise RuntimeError("Could not parse Age public key from Age/keys.txt.")


def _write_sops_yaml(target_dir: Path, age_public_key: str) -> None:
    content = f"""\
creation_rules:
  - path_regex: \\.enc\\.yaml$
    age: {age_public_key}
"""
    (target_dir / ".sops.yaml").write_text(content)


def _substitute_domain(text: str, domain: str) -> str:
    text = text.replace("example.com", domain)
    text = text.replace("${DOMAIN}", domain)
    return text


def _get_or_generate_secrets(project_root: Path, domain: str) -> dict:
    """Return all secrets needed to fill the enc.yaml placeholders."""
    from Scripts.security.canonical_store import get_canonical_store
    from Scripts.security.security_manager import NoahSecurityManager

    store = get_canonical_store(project_root)
    manager = NoahSecurityManager(project_root=project_root)

    for service in ("authentik", "headlamp", "cloudflare"):
        manager.generate_service_secrets(service)

    cf = store.get_service_secrets("cloudflare")
    auth = store.get_service_secrets("authentik")
    headlamp = store.get_service_secrets("headlamp")

    cf_token = cf.get("api_token")
    if not cf_token:
        raise RuntimeError(
            "Cloudflare API token not found in canonical store.\n"
            "Run: python3 Scripts/security/set_cloudflare_token.py 'your-token'"
        )

    return {
        "REPLACE_WITH_CLOUDFLARE_TOKEN":       cf_token,
        "REPLACE_WITH_50_CHAR_SECRET":         auth.get("secret_key", ""),
        "REPLACE_WITH_ADMIN_PASSWORD":         auth.get("bootstrap_password", ""),
        "REPLACE_WITH_BOOTSTRAP_TOKEN":        auth.get("bootstrap_token", ""),
        "REPLACE_WITH_POSTGRES_PASSWORD":      auth.get("postgresql_password", ""),
        "REPLACE_WITH_POSTGRES_ROOT_PASSWORD": auth.get("postgresql_password", ""),
        "REPLACE_WITH_OIDC_CLIENT_ID":         headlamp.get("oidc_client_id", "headlamp"),
        "REPLACE_WITH_OIDC_CLIENT_SECRET":     headlamp.get("oidc_client_secret", ""),
        "admin@example.com":                   f"admin@{domain}",
    }


def _fill_file(path: Path, replacements: dict) -> None:
    text = path.read_text()
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    path.write_text(text)


def _is_sops_encrypted(path: Path) -> bool:
    text = path.read_text()
    return text.startswith("sops:") or "\nsops:" in text


def _sops_decrypt(path: Path, age_key_file: Path) -> None:
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--decrypt", "--in-place", str(path)],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"SOPS decryption failed for {path}:\n{result.stderr}")


def _sops_encrypt(path: Path, sops_yaml: Path, age_key_file: Path) -> None:
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", str(path)],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"SOPS encryption failed for {path}:\n{result.stderr}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def setup_gitops(
    domain: str,
    project_root: Path,
    print_status,
) -> None:
    """
    Prepare the gitops/ subdirectory in-place: substitute domain, fill secrets,
    and SOPS-encrypt. Idempotent — decrypts existing encrypted files before
    re-filling so re-runs with different domains or rotated secrets work cleanly.

    After running, commit and push the NOAH repo so Flux can reconcile:
        git add gitops/ && git commit -m 'chore: update GitOps configuration'
        git push origin main
    """
    gitops_dir = project_root / "gitops"
    if not gitops_dir.exists():
        raise RuntimeError(
            "gitops/ directory not found in project root. "
            "Expected the GitOps manifests at gitops/."
        )

    age_key_file = project_root / "Age" / "keys.txt"

    # 1. Substitute domain in plain YAML files
    for yaml_file in gitops_dir.rglob("*.yaml"):
        if yaml_file.name.endswith(".enc.yaml"):
            continue
        text = yaml_file.read_text()
        if "example.com" in text or "${DOMAIN}" in text:
            yaml_file.write_text(_substitute_domain(text, domain))
    print_status(f"[SUCCESS] Substituted domain → {domain}", "SUCCESS")

    # 2. Load secrets
    print_status("[INFO] Loading secrets from canonical store...", "INFO")
    replacements = _get_or_generate_secrets(project_root, domain)
    replacements["example.com"] = domain
    replacements["${DOMAIN}"] = domain
    print_status("[SUCCESS] Secrets loaded", "SUCCESS")

    # 3. Decrypt any already-encrypted files before filling (idempotent re-runs)
    for enc_file in gitops_dir.rglob("*.enc.yaml"):
        if _is_sops_encrypted(enc_file):
            _sops_decrypt(enc_file, age_key_file)

    # 4. Fill *.enc.yaml placeholders
    for enc_file in gitops_dir.rglob("*.enc.yaml"):
        _fill_file(enc_file, replacements)
    print_status("[SUCCESS] Filled secret placeholders in *.enc.yaml files", "SUCCESS")

    # 5. Write .sops.yaml
    age_pub = _age_public_key(project_root)
    _write_sops_yaml(gitops_dir, age_pub)
    print_status("[SUCCESS] Generated .sops.yaml", "SUCCESS")

    # 6. SOPS-encrypt each *.enc.yaml
    sops_yaml = gitops_dir / ".sops.yaml"
    for enc_file in gitops_dir.rglob("*.enc.yaml"):
        _sops_encrypt(enc_file, sops_yaml, age_key_file)
        print_status(f"[SUCCESS] Encrypted {enc_file.relative_to(gitops_dir)}", "SUCCESS")
