"""
Automates preparation of the NOAH GitOps repository:
  1. Copy flux-repo/ template to a target directory
  2. Substitute the example.com placeholder domain
  3. Fill *.enc.yaml placeholders from the canonical secrets store
     (generating any missing secrets automatically)
  4. Write .sops.yaml from the local Age public key
  5. SOPS-encrypt every *.enc.yaml in-place
  6. Git-init, commit, and push to GitHub (optional)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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
    return text.replace("example.com", domain)


def _get_or_generate_secrets(project_root: Path, domain: str) -> dict:
    """Return all secrets needed to fill the enc.yaml placeholders."""
    from Scripts.security.canonical_store import get_canonical_store
    from Scripts.security.security_manager import NoahSecurityManager

    store = get_canonical_store(project_root)
    manager = NoahSecurityManager(project_root=project_root)

    # Ensure all required services are populated in the canonical store
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
        "REPLACE_WITH_CLOUDFLARE_TOKEN": cf_token,
        "REPLACE_WITH_50_CHAR_SECRET":   auth.get("secret_key", ""),
        "REPLACE_WITH_ADMIN_PASSWORD":   auth.get("bootstrap_password", ""),
        "REPLACE_WITH_BOOTSTRAP_TOKEN":  auth.get("bootstrap_token", ""),
        "REPLACE_WITH_POSTGRES_PASSWORD":      auth.get("postgresql_password", ""),
        "REPLACE_WITH_POSTGRES_ROOT_PASSWORD": auth.get("postgresql_password", ""),
        "REPLACE_WITH_OIDC_CLIENT_ID":     headlamp.get("oidc_client_id", "headlamp"),
        "REPLACE_WITH_OIDC_CLIENT_SECRET": headlamp.get("oidc_client_secret", ""),
        f"admin@example.com":             f"admin@{domain}",
    }


def _fill_file(path: Path, replacements: dict) -> None:
    text = path.read_text()
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    path.write_text(text)


def _sops_encrypt(path: Path, sops_yaml: Path) -> None:
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(sops_yaml.parent / ".." / "Age" / "keys.txt")}
    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", str(path)],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"SOPS encryption failed for {path}:\n{result.stderr}")


def _github_push(target_dir: Path, github_repo: str, github_token: str, print_status) -> str:
    """Create the GitHub repo (if needed) and push. Returns the repo URL."""
    repo_url = f"https://github.com/{github_repo}.git"
    authed_url = f"https://x-access-token:{github_token}@github.com/{github_repo}.git"

    # Create repo via gh CLI if available and repo doesn't exist yet
    repo_already_existed = False
    if shutil.which("gh"):
        check = subprocess.run(
            ["gh", "repo", "view", github_repo],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_TOKEN": github_token}
        )
        if check.returncode != 0:
            print_status(f"[INFO] Creating GitHub repository {github_repo}...", "INFO")
            result = subprocess.run(
                ["gh", "repo", "create", github_repo, "--private", "--confirm"],
                capture_output=True, text=True,
                env={**os.environ, "GITHUB_TOKEN": github_token}
            )
            if result.returncode != 0:
                # Newer gh versions use different flags
                result = subprocess.run(
                    ["gh", "repo", "create", github_repo, "--private"],
                    capture_output=True, text=True,
                    env={**os.environ, "GITHUB_TOKEN": github_token}
                )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to create GitHub repo:\n{result.stderr}")
            print_status(f"[SUCCESS] Repository {github_repo} created", "SUCCESS")
        else:
            print_status(f"[INFO] Repository {github_repo} already exists — keeping it, updating content", "INFO")
            repo_already_existed = True
    else:
        print_status("[WARNING] gh CLI not found — assuming repo already exists", "WARNING")
        repo_already_existed = True

    _run(["git", "init", "-b", "main"], cwd=target_dir)
    _run(["git", "add", "."], cwd=target_dir)
    _run(["git", "commit", "-m", "chore: update NOAH GitOps configuration"], cwd=target_dir)
    _run(["git", "remote", "add", "origin", authed_url], cwd=target_dir)

    # When the remote already has commits, a regular push will be rejected as
    # non-fast-forward. Force-push intentionally: the local tree (freshly built
    # from the flux-repo template with updated secrets/key) is authoritative.
    if repo_already_existed:
        print_status("[INFO] Force-pushing updated configuration to existing repo...", "INFO")
        _run(["git", "push", "-u", "--force", "origin", "main"], cwd=target_dir)
    else:
        _run(["git", "push", "-u", "origin", "main"], cwd=target_dir)

    return repo_url


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def setup_gitops(
    domain: str,
    target_dir: Path,
    github_repo: Optional[str],
    github_token: Optional[str],
    push: bool,
    project_root: Path,
    print_status,
) -> str:
    """
    Prepare the GitOps repository and optionally push to GitHub.
    Returns the flux-repo URL (local path or GitHub URL).
    """
    flux_template = project_root / "flux-repo"
    if not flux_template.exists():
        raise RuntimeError("flux-repo/ template directory not found in project root.")

    # 1. Copy template
    if target_dir.exists():
        print_status(f"[INFO] {target_dir} already exists — recreating from template", "INFO")
        shutil.rmtree(target_dir)
    shutil.copytree(flux_template, target_dir)
    print_status(f"[SUCCESS] Copied flux-repo template to {target_dir}", "SUCCESS")

    # 2. Substitute domain in plain YAML files
    for yaml_file in target_dir.rglob("*.yaml"):
        if yaml_file.name.endswith(".enc.yaml"):
            continue
        text = yaml_file.read_text()
        if "example.com" in text:
            yaml_file.write_text(_substitute_domain(text, domain))
    print_status(f"[SUCCESS] Substituted domain → {domain}", "SUCCESS")

    # 3. Read / generate secrets
    print_status("[INFO] Loading secrets from canonical store...", "INFO")
    replacements = _get_or_generate_secrets(project_root, domain)
    # Also substitute domain inside enc.yaml files (e.g. auth URL, email)
    replacements["example.com"] = domain
    print_status("[SUCCESS] Secrets loaded", "SUCCESS")

    # 4. Fill *.enc.yaml placeholders
    for enc_file in target_dir.rglob("*.enc.yaml"):
        _fill_file(enc_file, replacements)
    print_status("[SUCCESS] Filled secret placeholders in *.enc.yaml files", "SUCCESS")

    # 5. Write .sops.yaml
    age_pub = _age_public_key(project_root)
    _write_sops_yaml(target_dir, age_pub)
    print_status("[SUCCESS] Generated .sops.yaml", "SUCCESS")

    # 6. SOPS-encrypt each *.enc.yaml
    sops_yaml = target_dir / ".sops.yaml"
    enc_files = list(target_dir.rglob("*.enc.yaml"))
    for enc_file in enc_files:
        _sops_encrypt(enc_file, sops_yaml)
        print_status(f"[SUCCESS] Encrypted {enc_file.relative_to(target_dir)}", "SUCCESS")

    # 7. Push to GitHub
    repo_url = str(target_dir)
    if push:
        if not github_repo:
            raise RuntimeError("--github-repo is required when --push is set.")
        if not github_token:
            raise RuntimeError(
                "GitHub token required. Set GITHUB_TOKEN env var or pass --github-token."
            )
        repo_url = _github_push(target_dir, github_repo, github_token, print_status)
        print_status(f"[SUCCESS] Pushed to {repo_url}", "SUCCESS")
    else:
        print_status(f"[INFO] GitOps repo ready at {target_dir} (not pushed)", "INFO")

    return repo_url
