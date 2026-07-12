#!/usr/bin/env python3
"""
Cloudflare DNS Wizard for NOAH
Interactive wizard that prompts for a Cloudflare API token, validates it,
lists available DNS zones, persists credentials to the SOPS-encrypted config,
and enables external-dns in the deployment configuration.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore


class CloudflareWizard:
    """
    Interactive wizard for configuring Cloudflare DNS automation.

    Usage::

        wizard = CloudflareWizard(project_root=Path("/path/to/NOAH"))
        wizard.run()
    """

    CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.config_file = self.project_root / "Config" / "config.enc.yaml"
        self._token: Optional[str] = None
        self._zone_id: Optional[str] = None
        self._domain: Optional[str] = None

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """
        Run the full interactive wizard.

        Returns:
            True if configuration was completed successfully, False if skipped/failed.
        """
        print("\n" + "=" * 60)
        print("  Cloudflare DNS Wizard")
        print("=" * 60)
        print(
            "\nThis wizard configures automatic DNS record management via Cloudflare.\n"
            "You will need a Cloudflare API token with Zone:DNS:Edit permissions.\n"
        )

        if not self._check_requests():
            print(
                "[WARNING] The 'requests' package is not installed.\n"
                "          Skipping Cloudflare DNS wizard.\n"
                "          Install it with: pip install requests"
            )
            return False

        answer = input("Would you like to configure Cloudflare DNS now? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("[INFO] Skipping Cloudflare DNS wizard. You can run it later.")
            return False

        try:
            self._token = self._prompt_token()
            zones = self._list_zones(self._token)
            if not zones:
                print("[WARNING] No DNS zones found for this token. Check token permissions.")
                return False

            self._zone_id, self._domain = self._prompt_zone(zones)
            self._persist()
            self._persist_to_canonical_store()
            self._enable_external_dns()
            self._print_success()
            return True

        except KeyboardInterrupt:
            print("\n\n[INFO] Cloudflare wizard cancelled by user.")
            return False
        except Exception as exc:
            print(f"\n[ERROR] Cloudflare wizard failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Interactive steps
    # ------------------------------------------------------------------

    def _prompt_token(self) -> str:
        """Prompt for and validate a Cloudflare API token."""
        for attempt in range(3):
            token = input("Enter your Cloudflare API token: ").strip()
            if not token:
                print("[ERROR] Token cannot be empty.")
                continue
            print("[INFO] Validating token…")
            if self._validate_token(token):
                print("[SUCCESS] Token validated.")
                return token
            print(f"[ERROR] Token validation failed (attempt {attempt + 1}/3).")
        raise RuntimeError("Cloudflare API token validation failed after 3 attempts.")

    def _validate_token(self, token: str) -> bool:
        """
        Return True if the token is valid.

        Tries three endpoints in order, accepting the first success:
        1. /user/tokens/verify  — works for tokens with User:Read scope
        2. /zones               — works for any token with Zone:Read/DNS scope
        3. /accounts            — works for account-level tokens
        """
        headers = {"Authorization": f"Bearer {token}"}
        try:
            # Primary: standard token verification
            resp = requests.get(
                f"{self.CLOUDFLARE_API_BASE}/user/tokens/verify",
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200 and resp.json().get("success", False):
                return True
        except Exception:
            pass

        try:
            # Fallback 1: list zones — succeeds if token has Zone:Read or DNS:Edit
            resp = requests.get(
                f"{self.CLOUDFLARE_API_BASE}/zones",
                headers=headers,
                params={"per_page": 1},
                timeout=15,
            )
            if resp.status_code == 200 and resp.json().get("success", False):
                return True
        except Exception:
            pass

        try:
            # Fallback 2: list accounts — succeeds for account-scoped tokens
            resp = requests.get(
                f"{self.CLOUDFLARE_API_BASE}/accounts",
                headers=headers,
                params={"per_page": 1},
                timeout=15,
            )
            if resp.status_code == 200 and resp.json().get("success", False):
                return True
        except Exception:
            pass

        return False

    def _list_zones(self, token: str) -> list:
        """Return a list of DNS zones accessible with the given token."""
        zones = []
        page = 1
        while True:
            resp = requests.get(
                f"{self.CLOUDFLARE_API_BASE}/zones",
                headers={"Authorization": f"Bearer {token}"},
                params={"page": page, "per_page": 50},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            zones.extend(data.get("result", []))
            info = data.get("result_info", {})
            if page >= info.get("total_pages", 1):
                break
            page += 1
        return zones

    def _prompt_zone(self, zones: list) -> tuple:
        """
        Display available zones and prompt the user to select one.
        Auto-selects when only one zone is available.

        Returns:
            (zone_id, domain) tuple.
        """
        if len(zones) == 1:
            selected = zones[0]
            print(f"\n[INFO] Only one DNS zone found — auto-selecting: {selected['name']}")
            return selected["id"], selected["name"]

        print("\nAvailable DNS zones:")
        for i, zone in enumerate(zones, start=1):
            status = zone.get("status", "unknown")
            print(f"  [{i}] {zone['name']}  (status: {status})")

        while True:
            raw = input(f"\nSelect a zone [1-{len(zones)}]: ").strip()
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(zones):
                    selected = zones[idx]
                    return selected["id"], selected["name"]
            except ValueError:
                pass
            print(f"[ERROR] Please enter a number between 1 and {len(zones)}.")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        """
        Persist Cloudflare credentials into Config/config.enc.yaml via SOPS.
        Decrypts the file, merges new keys, and re-encrypts in place.
        """
        if not self.config_file.exists():
            print(f"[WARNING] Config file not found at {self.config_file}. Skipping persistence.")
            return

        # Decrypt current config to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, prefix="noah_config_"
        ) as tmp:
            tmp_path = Path(tmp.name)

        age_key_file = self.project_root / "Age" / "keys.txt"
        sops_env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}

        try:
            # Decrypt
            result = subprocess.run(
                ["sops", "--decrypt", str(self.config_file)],
                capture_output=True,
                text=True,
                env=sops_env,
            )
            if result.returncode != 0:
                print(f"[WARNING] Could not decrypt config file: {result.stderr.strip()}")
                print("[INFO] Credentials will be written to environment only.")
                self._persist_to_env()
                return

            import yaml  # type: ignore

            config_data = yaml.safe_load(result.stdout) or {}

            # Merge Cloudflare section
            if "cloudflare" not in config_data:
                config_data["cloudflare"] = {}
            config_data["cloudflare"]["api_token"] = self._token
            config_data["cloudflare"]["zone_id"] = self._zone_id
            config_data["cloudflare"]["domain"] = self._domain

            # Enable external-dns
            if "noah" not in config_data:
                config_data["noah"] = {}
            config_data["noah"]["external_dns_enabled"] = "true"

            # Write plaintext YAML to temp file
            with open(tmp_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            # Re-encrypt in place (using existing SOPS metadata from the original)
            enc_result = subprocess.run(
                ["sops", "--encrypt", "--in-place", str(tmp_path)],
                capture_output=True,
                text=True,
                env=sops_env,
            )
            if enc_result.returncode != 0:
                print(f"[WARNING] Could not encrypt config: {enc_result.stderr.strip()}")
                print("[INFO] Credentials will be written to environment only.")
                self._persist_to_env()
                return

            # Overwrite the original encrypted file
            import shutil

            shutil.move(str(tmp_path), str(self.config_file))
            print(f"[SUCCESS] Credentials persisted to {self.config_file}")

        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _persist_to_canonical_store(self) -> None:
        """Write the validated token into the canonical secrets store (same as set_cloudflare_token.py)."""
        try:
            from Scripts.security.canonical_store import get_canonical_store
            from datetime import datetime, timezone

            store = get_canonical_store(self.project_root)
            store.ensure_service("cloudflare")
            svc = store.data["services"]["cloudflare"]
            svc["api_token"] = {
                "value": self._token,
                "version": (svc["api_token"]["version"] + 1) if isinstance(svc.get("api_token"), dict) else 1,
                "rotated_at": datetime.now(timezone.utc).isoformat(),
            }
            store.save()
            print("[SUCCESS] Cloudflare token stored in canonical secrets store.")
        except Exception as exc:
            print(f"[WARNING] Could not write to canonical store: {exc}")
            print("[INFO] Run 'python3 Scripts/security/set_cloudflare_token.py <token>' manually if needed.")

    def _persist_to_env(self) -> None:
        """Fall-back: export credentials as environment variables for the current process."""
        os.environ["CLOUDFLARE_API_TOKEN"] = self._token or ""
        os.environ["CLOUDFLARE_ZONE_ID"] = self._zone_id or ""
        os.environ["CLOUDFLARE_DOMAIN"] = self._domain or ""
        os.environ["NOAH_EXTERNAL_DNS_ENABLED"] = "true"
        print("[INFO] Cloudflare credentials exported to environment variables.")

    def _enable_external_dns(self) -> None:
        """Ensure NOAH_EXTERNAL_DNS_ENABLED is set in the current process environment."""
        os.environ["NOAH_EXTERNAL_DNS_ENABLED"] = "true"
        if self._token:
            os.environ["CLOUDFLARE_API_TOKEN"] = self._token
        if self._zone_id:
            os.environ["CLOUDFLARE_ZONE_ID"] = self._zone_id
        if self._domain:
            os.environ["CLOUDFLARE_DOMAIN"] = self._domain
            os.environ.setdefault("NOAH_DOMAIN", self._domain)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_requests(self) -> bool:
        """Return True if the 'requests' package is importable."""
        return requests is not None

    def _print_success(self) -> None:
        print("\n" + "=" * 60)
        print("  Cloudflare DNS Configuration Complete")
        print("=" * 60)
        print(f"  Domain  : {self._domain}")
        print(f"  Zone ID : {self._zone_id}")
        print("  external-dns: ENABLED")
        print(
            "\n  DNS records will be automatically managed during deployment.\n"
            "  You can skip this wizard in future runs with --skip-dns-wizard.\n"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NOAH Cloudflare DNS Wizard")
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).parent.parent.parent),
        help="Path to NOAH project root",
    )
    args = parser.parse_args()
    wizard = CloudflareWizard(project_root=Path(args.project_root))
    success = wizard.run()
    sys.exit(0 if success else 1)
