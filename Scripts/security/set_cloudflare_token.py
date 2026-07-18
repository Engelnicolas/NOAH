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

"""Store the Cloudflare API token in the NOAH canonical secrets store (SOPS-encrypted).

Usage:
  python3 Scripts/security/set_cloudflare_token.py <token>
  python3 Scripts/security/set_cloudflare_token.py --token <token>
  echo "<token>" | python3 Scripts/security/set_cloudflare_token.py --stdin

The token is written once and reused by every subsequent deployment that
needs CLOUDFLARE_API_TOKEN (external-dns, cert-manager DNS-01, etc.).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from Scripts.security.canonical_store import get_canonical_store
except Exception as e:
    print(f"[ERROR] Failed to load NOAH modules: {e}", file=sys.stderr)
    sys.exit(1)


def set_token(token: str) -> None:
    token = token.strip()
    if not token:
        print("[ERROR] Token is empty.", file=sys.stderr)
        sys.exit(1)

    store = get_canonical_store(ROOT)
    store.ensure_service("cloudflare")
    svc = store.data["services"]["cloudflare"]

    from datetime import datetime, timezone
    svc["api_token"] = {
        "value": token,
        "version": (svc["api_token"]["version"] + 1) if isinstance(svc.get("api_token"), dict) else 1,
        "rotated_at": datetime.now(timezone.utc).isoformat(),
    }
    store.data.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
    store.save()
    print("✓ Cloudflare API token stored in canonical secrets store.")
    print("  Deployment will now read it automatically — no CLOUDFLARE_API_TOKEN env var needed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Store Cloudflare API token in NOAH canonical store")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("token", nargs="?", help="API token value")
    group.add_argument("--token", dest="token_flag", help="API token value")
    group.add_argument("--stdin", action="store_true", help="Read token from stdin")
    args = parser.parse_args()

    if args.stdin:
        token = sys.stdin.read()
    elif args.token_flag:
        token = args.token_flag
    elif args.token:
        token = args.token
    else:
        parser.print_help()
        return 1

    set_token(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
