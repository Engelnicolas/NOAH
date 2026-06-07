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


def _infer_previous_domain(gitops_dir: Path, current_domain: str) -> Optional[str]:
    """Scan plain .yaml files for an `admin@<domain>` pattern to recover the
    previously-used domain when the canonical store doesn't have one yet —
    handles the migration case where existing files were filled with some
    domain before this rotation feature existed. Returns a value only when
    exactly one candidate domain (other than example.com or the current
    --domain) appears across the tree, to avoid guessing under ambiguity."""
    import re
    pattern = re.compile(r"admin@([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,})")
    candidates: set[str] = set()
    for yaml_file in gitops_dir.rglob("*.yaml"):
        if yaml_file.name.endswith(".enc.yaml"):
            continue
        for m in pattern.finditer(yaml_file.read_text()):
            d = m.group(1)
            if d not in ("example.com", current_domain):
                candidates.add(d)
    return next(iter(candidates)) if len(candidates) == 1 else None


def _substitute_domain(text: str, domain: str, previous_domain: Optional[str] = None) -> str:
    # `previous_domain` handles re-runs with a new --domain after the file was
    # already filled with a different one. Substitute the email form first so
    # the bare-domain rule doesn't mangle anything unexpected.
    if previous_domain and previous_domain != domain:
        text = text.replace(f"admin@{previous_domain}", f"admin@{domain}")
        text = text.replace(previous_domain, domain)
    text = text.replace("example.com", domain)
    text = text.replace("${DOMAIN}", domain)
    return text


def _get_or_generate_secrets(
    project_root: Path, domain: str, previous_domain: Optional[str] = None
) -> dict:
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

    def _ys(v: str) -> str:
        """Return a YAML-safe single-quoted scalar for embedding in a YAML block."""
        return "'" + v.replace("'", "''") + "'"

    replacements: dict[str, str] = {}

    # Domain rotation: if a previous run wrote a different domain, swap it for
    # the new one before the standard `example.com` rule (which has nothing
    # left to match once a file has already been filled with a real domain).
    # Email form first so a `<prev> → <new>` pass doesn't have to know about it.
    if previous_domain and previous_domain != domain:
        replacements[f"admin@{previous_domain}"] = f"admin@{domain}"
        replacements[previous_domain] = domain

    replacements.update({
        # Plain values — used in Kubernetes Secret stringData fields (not nested YAML)
        "REPLACE_WITH_CLOUDFLARE_TOKEN":       cf_token,
        "REPLACE_WITH_OIDC_CLIENT_ID":         headlamp.get("oidc_client_id", "headlamp"),
        "REPLACE_WITH_OIDC_CLIENT_SECRET":     headlamp.get("oidc_client_secret", ""),
        "REPLACE_WITH_BOOTSTRAP_TOKEN":        auth.get("bootstrap_token", ""),
        "admin@example.com":                   f"admin@{domain}",
        # YAML-quoted values — embedded inside a `values.yaml: |` block (nested YAML)
        "REPLACE_WITH_50_CHAR_SECRET":         _ys(auth.get("secret_key", "")),
        "REPLACE_WITH_ADMIN_PASSWORD":         _ys(auth.get("bootstrap_password", "")),
        "REPLACE_WITH_POSTGRES_PASSWORD":      _ys(auth.get("postgresql_password", "")),
        "REPLACE_WITH_POSTGRES_ROOT_PASSWORD": _ys(auth.get("postgresql_password", "")),
    })
    return replacements


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


# Plaintext templates for every *.enc.yaml file the gitops/ tree owns. Used to
# regenerate a file when SOPS cannot decrypt it because the recipient on the
# envelope no longer matches any locally available age identity (e.g. the
# Age/keys.txt was rotated and the old private key is gone). Keyed by the
# file's path relative to gitops/. Placeholder strings here MUST match keys
# produced by _get_or_generate_secrets so step 4 can substitute real values.
_DEFAULT_TEMPLATES: dict[str, str] = {
    "infrastructure/external-dns/cloudflare-secret.enc.yaml": """\
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-token
  namespace: external-dns
type: Opaque
stringData:
  api-token: REPLACE_WITH_CLOUDFLARE_TOKEN
""",
    "infrastructure/cert-manager-issuers/cloudflare-secret.enc.yaml": """\
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-token
  namespace: cert-manager
type: Opaque
stringData:
  api-token: REPLACE_WITH_CLOUDFLARE_TOKEN
""",
    "apps/authentik/bootstrap-token.enc.yaml": """\
apiVersion: v1
kind: Secret
metadata:
  name: authentik-bootstrap-token
  namespace: authentik
type: Opaque
stringData:
  # Key name matches the AUTHENTIK_TOKEN env var the inline provisioner
  # script (authentik-provisioner-script ConfigMap) reads via `envFrom`.
  AUTHENTIK_TOKEN: REPLACE_WITH_BOOTSTRAP_TOKEN
""",
    "apps/authentik/values-secret.enc.yaml": """\
apiVersion: v1
kind: Secret
metadata:
  name: authentik-values
  namespace: authentik
type: Opaque
stringData:
  values.yaml: |
    authentik:
      secret_key: REPLACE_WITH_50_CHAR_SECRET
      bootstrap_password: REPLACE_WITH_ADMIN_PASSWORD
      bootstrap_token: REPLACE_WITH_BOOTSTRAP_TOKEN
      bootstrap_email: admin@example.com
      postgresql:
        password: REPLACE_WITH_POSTGRES_PASSWORD
    postgresql:
      auth:
        password: REPLACE_WITH_POSTGRES_PASSWORD
        postgresPassword: REPLACE_WITH_POSTGRES_ROOT_PASSWORD
""",
    "apps/headlamp/oidc-secret.enc.yaml": """\
apiVersion: v1
kind: Secret
metadata:
  name: headlamp-oidc
  namespace: headlamp
type: Opaque
stringData:
  clientID: REPLACE_WITH_OIDC_CLIENT_ID
  clientSecret: REPLACE_WITH_OIDC_CLIENT_SECRET
""",
}


def _is_unreachable_recipient_error(stderr: str) -> bool:
    return "no identity matched any of the recipients" in stderr


def _decrypt_or_regenerate(
    enc_file: Path,
    gitops_dir: Path,
    age_key_file: Path,
    print_status,
) -> bool:
    """Decrypt enc_file in place. If decryption fails because the file is
    sealed to an age recipient we no longer have the private key for,
    overwrite it with the plaintext template (so step 4 can re-substitute
    placeholders and step 6 can re-encrypt under the current key).

    Returns True if the file was regenerated from a template (meaning the
    original ciphertext is unrecoverable and must be re-encrypted fresh);
    False if it was decrypted normally (meaning the original ciphertext
    can be reused if the plaintext doesn't end up changing)."""
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--decrypt", "--in-place", str(enc_file)],
        env=env, capture_output=True, text=True
    )
    if result.returncode == 0:
        return False

    if not _is_unreachable_recipient_error(result.stderr):
        raise RuntimeError(f"SOPS decryption failed for {enc_file}:\n{result.stderr}")

    rel = str(enc_file.relative_to(gitops_dir))
    template = _DEFAULT_TEMPLATES.get(rel)
    if template is None:
        raise RuntimeError(
            f"SOPS decryption failed for {enc_file} because the file is sealed "
            f"to an age recipient not present in {age_key_file}, and no "
            f"regeneration template is registered for '{rel}'. Either restore "
            f"the original age private key, or add an entry for this path to "
            f"_DEFAULT_TEMPLATES in Scripts/gitops/gitops_init.py."
        )
    enc_file.write_text(template)
    print_status(
        f"[INFO] {rel}: sealed to an unavailable age key; regenerated from template",
        "INFO",
    )
    return True


def _sops_encrypt(path: Path, sops_yaml: Path, age_key_file: Path) -> None:
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", str(path)],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"SOPS encryption failed for {path}:\n{result.stderr}")


def render_app_secret_manifests(project_root: Path, domain: str) -> str:
    """Render the application Secret manifests as a single plaintext, multi-document
    YAML stream, built from the canonical store using the same templates and
    placeholder substitution as the (now removed) gitops/*.enc.yaml files.

    This is the out-of-band delivery path: the bootstrap passes the result to the
    `app-secrets` Ansible role, which `kubectl apply`s it directly into the
    cluster. Secrets therefore never need to be committed to Git during a
    deployment. Reused for re-delivery after rotation.
    """
    from Scripts.security.canonical_store import get_canonical_store

    store = get_canonical_store(project_root)
    previous_domain = store.get_cluster_domain()
    replacements = _get_or_generate_secrets(project_root, domain, previous_domain)
    replacements["example.com"] = domain
    replacements["${DOMAIN}"] = domain

    documents: list[str] = []
    for template in _DEFAULT_TEMPLATES.values():
        text = template
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        documents.append(text.rstrip("\n"))
    return "\n---\n".join(documents) + "\n"


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

    # Read the domain the previous run wrote (if any) so step 1 and step 4 can
    # rewrite files that were already filled with a different domain. Falls
    # back to inferring from existing files when the store has no record (e.g.
    # files were filled before this rotation feature existed).
    from Scripts.security.canonical_store import get_canonical_store
    store = get_canonical_store(project_root)
    previous_domain = store.get_cluster_domain() or _infer_previous_domain(
        gitops_dir, domain
    )

    # 1. Substitute domain in plain YAML files
    for yaml_file in gitops_dir.rglob("*.yaml"):
        if yaml_file.name.endswith(".enc.yaml"):
            continue
        text = yaml_file.read_text()
        triggers = ("example.com", "${DOMAIN}")
        needs_rewrite = any(t in text for t in triggers) or (
            previous_domain and previous_domain != domain and previous_domain in text
        )
        if needs_rewrite:
            yaml_file.write_text(_substitute_domain(text, domain, previous_domain))
    print_status(f"[SUCCESS] Substituted domain → {domain}", "SUCCESS")

    # 2. Load secrets
    print_status("[INFO] Loading secrets from canonical store...", "INFO")
    replacements = _get_or_generate_secrets(project_root, domain, previous_domain)
    replacements["example.com"] = domain
    replacements["${DOMAIN}"] = domain
    print_status("[SUCCESS] Secrets loaded", "SUCCESS")

    # Steps 3–6 modify *.enc.yaml files in place. Between decrypt (step 3) and
    # encrypt (step 6) they hold plaintext secrets on disk — if the process
    # crashes there, the user could accidentally `git add` and commit secrets.
    # The try/except below guarantees that no .enc.yaml is left in a plaintext
    # state when this function exits, by restoring the original ciphertext
    # (for files we successfully decrypted) or the placeholder template (for
    # files that had to be regenerated because their key was rotated).
    #
    # Crash-recovery records — also reused by step 6 for idempotency.
    original_ciphertext: dict[Path, bytes] = {}
    regenerated_templates: dict[Path, str] = {}
    completed: set[Path] = set()

    try:
        # 3. Decrypt or regenerate. SOPS uses a random IV per encryption, so
        # re-encrypting the same plaintext yields different ciphertext and
        # dirties git. To keep no-op re-runs clean, snapshot original ciphertext
        # for files we can still decrypt; step 6 reuses it when plaintext is
        # unchanged. For files sealed to an unreachable key, capture the
        # template instead — that's the only safe rollback target.
        for enc_file in gitops_dir.rglob("*.enc.yaml"):
            if _is_sops_encrypted(enc_file):
                snapshot = enc_file.read_bytes()
                regenerated = _decrypt_or_regenerate(
                    enc_file, gitops_dir, age_key_file, print_status
                )
                if regenerated:
                    regenerated_templates[enc_file] = enc_file.read_text()
                else:
                    original_ciphertext[enc_file] = snapshot

        plaintext_before_fill: dict[Path, bytes] = {
            f: f.read_bytes() for f in original_ciphertext
        }

        # 4. Fill *.enc.yaml placeholders
        for enc_file in gitops_dir.rglob("*.enc.yaml"):
            _fill_file(enc_file, replacements)
        print_status("[SUCCESS] Filled secret placeholders in *.enc.yaml files", "SUCCESS")

        # 5. Write .sops.yaml
        age_pub = _age_public_key(project_root)
        _write_sops_yaml(gitops_dir, age_pub)
        print_status("[SUCCESS] Generated .sops.yaml", "SUCCESS")

        # 6. SOPS-encrypt each *.enc.yaml — but if the plaintext didn't change
        # versus the previous run, restore the original ciphertext to avoid the
        # spurious git diff that a fresh IV would cause.
        sops_yaml = gitops_dir / ".sops.yaml"
        unchanged = 0
        for enc_file in gitops_dir.rglob("*.enc.yaml"):
            if enc_file in original_ciphertext:
                if enc_file.read_bytes() == plaintext_before_fill[enc_file]:
                    enc_file.write_bytes(original_ciphertext[enc_file])
                    completed.add(enc_file)
                    unchanged += 1
                    continue
            _sops_encrypt(enc_file, sops_yaml, age_key_file)
            completed.add(enc_file)
            print_status(f"[SUCCESS] Encrypted {enc_file.relative_to(gitops_dir)}", "SUCCESS")
        if unchanged:
            print_status(
                f"[INFO] {unchanged} file(s) unchanged — kept existing ciphertext (no git churn)",
                "INFO",
            )
    except BaseException:
        # Best-effort restoration so no plaintext .enc.yaml survives a crash
        # or Ctrl-C. Snapshots return files to byte-identical pre-run state;
        # templates leave regenerated files as plain placeholders (no secrets).
        for f, blob in original_ciphertext.items():
            if f in completed:
                continue
            try:
                f.write_bytes(blob)
            except OSError as restore_err:
                print_status(f"[WARN] Failed to restore {f}: {restore_err}", "WARN")
        for f, template in regenerated_templates.items():
            if f in completed:
                continue
            try:
                f.write_text(template)
            except OSError as restore_err:
                print_status(f"[WARN] Failed to restore {f}: {restore_err}", "WARN")
        print_status(
            "[ERROR] setup_gitops failed; .enc.yaml files restored to pre-run state",
            "ERROR",
        )
        raise

    # Record the domain so the next run can rewrite files that were filled
    # with this value if --domain changes.
    if store.get_cluster_domain() != domain:
        store.set_cluster_domain(domain)
