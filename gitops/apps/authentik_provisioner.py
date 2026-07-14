#!/usr/bin/env python3
"""
Registers a NOAH service in Authentik, idempotently.

Modes:
  --type proxy : Proxy Provider (forward-auth) bound to the embedded
                 outpost, e.g. Hubble UI. No client credentials needed.
  --type oidc  : OAuth2/OIDC Provider + Application, e.g. Headlamp. Reads
                 OIDC_CLIENT_ID / OIDC_CLIENT_SECRET from the environment
                 and registers a confidential client. Redirect URIs come from
                 --redirect-uri (repeatable); when omitted, defaults to
                 "<external-host>/oidc-callback" (the Headlamp callback).

Reads AUTHENTIK_URL and AUTHENTIK_TOKEN from the environment.
Idempotent: re-running is a no-op if the provider/app already exist.
"""
import argparse
import os
import sys
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def headers():
    return {
        "Authorization": f"Bearer {os.environ['AUTHENTIK_TOKEN']}",
        "Content-Type": "application/json",
    }


def base_url():
    return os.environ["AUTHENTIK_URL"].rstrip("/") + "/api/v3"


def api(method, path, **kwargs):
    r = getattr(requests, method)(
        f"{base_url()}{path}", headers=headers(), verify=False, timeout=30, **kwargs
    )
    if not r.ok:
        print(f"ERROR {method.upper()} {path}: {r.status_code} {r.text}", file=sys.stderr)
        sys.exit(1)
    return r.json()


def find_or_create(path, key, value, payload):
    """Get-or-create by `key`==`value`. When the item already exists, PATCH it
    with `payload` so drift (stale redirect_uri, rotated client_secret,
    changed external_host, etc.) self-heals on every idempotent re-run
    instead of freezing in whatever state first created it."""
    for item in api("get", path, params={"search": value}).get("results", []):
        if item.get(key) == value:
            print(f"[INFO] Already exists: {value} — syncing config")
            # Authentik's detail endpoint is keyed by slug for applications
            # but by numeric pk for providers/outposts.
            item_id = item.get("slug", item.get("pk"))
            return api("patch", f"{path}{item_id}/", json=payload)
    print(f"[INFO] Creating: {value}")
    return api("post", path, json=payload)


def default_flow(designation, preferred_slug_fragment):
    flows = api("get", "/flows/instances/", params={"designation": designation})
    results = flows.get("results", [])
    for flow in results:
        if preferred_slug_fragment in flow["slug"]:
            return flow["pk"]
    if results:
        return results[0]["pk"]
    print(f"[ERROR] No {designation} flow found", file=sys.stderr)
    sys.exit(1)


def scope_mapping_pks(scope_names):
    """Resolve the PKs of the managed OIDC scope property mappings by
    scope_name. Tries the current endpoint, then an older fallback, so the
    script tolerates Authentik API reorganisations across versions."""
    for path in ("/propertymappings/provider/scope/", "/propertymappings/scope/"):
        r = requests.get(
            f"{base_url()}{path}", headers=headers(),
            params={"page_size": 100}, verify=False, timeout=30,
        )
        if not r.ok:
            continue
        pks = [m["pk"] for m in r.json().get("results", [])
               if m.get("scope_name") in scope_names]
        if pks:
            return pks
    print("[WARNING] No scope property mappings resolved; the provider will "
          "advertise no scopes", file=sys.stderr)
    return []


def default_signing_key():
    """Pick a certificate-keypair PK so OIDC tokens are RS256-signed and a
    JWKS is published (Headlamp/go-oidc verifies via JWKS). Prefers the
    managed self-signed cert, falls back to the first keypair with a key."""
    for params in ({"name": "authentik Self-signed Certificate"}, {"has_key": "true"}):
        r = requests.get(
            f"{base_url()}/crypto/certificatekeypairs/", headers=headers(),
            params=params, verify=False, timeout=30,
        )
        if r.ok and r.json().get("results"):
            return r.json()["results"][0]["pk"]
    print("[WARNING] No certificate-keypair found; OIDC tokens may be unsigned",
          file=sys.stderr)
    return None


def wait_for_authentik(timeout=600, interval=10):
    """Block until the Authentik API is reachable AND the default flows
    exist. The provisioning Job can be scheduled before Authentik has
    finished its first-boot bootstrap (Postgres migrations + flow import);
    waiting here makes the Job resilient to that start-up race instead of
    burning through the Job backoffLimit."""
    deadline = time.time() + timeout
    while True:
        try:
            r = requests.get(
                f"{base_url()}/flows/instances/",
                headers=headers(),
                params={"designation": "authorization"},
                verify=False,
                timeout=15,
            )
            if r.ok and r.json().get("results"):
                print("[INFO] Authentik is ready")
                return
        except requests.RequestException:
            pass
        if time.time() >= deadline:
            print("[ERROR] Authentik not ready within timeout", file=sys.stderr)
            sys.exit(1)
        print("[INFO] Waiting for Authentik to be ready...")
        time.sleep(interval)


def bind_embedded_outpost(provider_pk):
    outposts = api(
        "get", "/outposts/instances/",
        params={"managed": "goauthentik.io/outposts/embedded"},
    )
    if not outposts["results"]:
        print("[WARNING] No embedded outpost found — skipping outpost binding",
              file=sys.stderr)
        return
    outpost = outposts["results"][0]
    providers = outpost.get("providers", [])
    needs_update = provider_pk not in providers
    if needs_update:
        providers.append(provider_pk)
    # Always ensure authentik_host is set so the outpost can build correct
    # redirect URLs for unauthenticated forward-auth requests.
    external_url = os.environ.get("AUTHENTIK_EXTERNAL_URL", "")
    current_host = outpost.get("config", {}).get("authentik_host", "")
    if external_url and current_host != external_url:
        needs_update = True
    if needs_update:
        patch = {"providers": providers}
        if external_url:
            patch["config"] = {**outpost.get("config", {}), "authentik_host": external_url}
        api("patch", f"/outposts/instances/{outpost['pk']}/", json=patch)
        print(f"[INFO] Outpost updated (authentik_host={external_url or 'unchanged'})")
    else:
        print("[INFO] Provider already in embedded outpost")


def provision_proxy(service, external_host):
    auth_flow = default_flow("authorization", "default-provider-authorization")
    invalidation_flow = default_flow("invalidation", "default-provider-invalidation")
    provider = find_or_create(
        "/providers/proxy/", "name", f"{service}-proxy",
        {
            "name": f"{service}-proxy",
            "authorization_flow": auth_flow,
            "invalidation_flow": invalidation_flow,
            "mode": "forward_single",
            "external_host": external_host,
        },
    )
    provider_pk = provider["pk"]
    print(f"[INFO] Provider pk={provider_pk}")
    app = find_or_create(
        "/core/applications/", "slug", service,
        {"name": service.capitalize(), "slug": service, "provider": provider_pk},
    )
    print(f"[INFO] Application slug={app['slug']}")
    bind_embedded_outpost(provider_pk)


def provision_oidc(service, external_host, redirect_uris=None):
    client_id = os.environ.get("OIDC_CLIENT_ID", service)
    client_secret = os.environ.get("OIDC_CLIENT_SECRET", "")
    if not client_secret:
        print("[ERROR] OIDC_CLIENT_SECRET must be set for --type oidc", file=sys.stderr)
        sys.exit(1)
    if not redirect_uris:
        redirect_uris = [f"{external_host}/oidc-callback"]
    auth_flow = default_flow("authorization", "default-provider-authorization")
    invalidation_flow = default_flow("invalidation", "default-provider-invalidation")
    payload = {
        "name": f"{service}-oidc",
        "client_id": client_id,
        "client_secret": client_secret,
        "client_type": "confidential",
        "authorization_flow": auth_flow,
        "invalidation_flow": invalidation_flow,
        # Without this, Authentik defaults grant_types to an empty list,
        # rejecting the token exchange with "Invalid grant_type for
        # provider" (surfaces to Headlamp as oauth2 invalid_grant).
        "grant_types": ["authorization_code", "refresh_token"],
        # Authentik 2024.4+ models redirect URIs as structured objects.
        "redirect_uris": [
            {"matching_mode": "strict", "url": uri} for uri in redirect_uris
        ],
        "sub_mode": "hashed_user_id",
        "include_claims_in_id_token": True,
        # per_provider → discovery `issuer` is ".../application/o/<slug>/",
        # which is exactly the OIDC_ISSUER_URL Headlamp is configured with.
        # (go-oidc rejects the login if the issuer does not match.)
        "issuer_mode": "per_provider",
        "property_mappings": scope_mapping_pks({"openid", "email", "profile"}),
    }
    signing_key = default_signing_key()
    if signing_key:
        payload["signing_key"] = signing_key
    provider = find_or_create("/providers/oauth2/", "name", f"{service}-oidc", payload)
    provider_pk = provider["pk"]
    print(f"[INFO] Provider pk={provider_pk}")
    app = find_or_create(
        "/core/applications/", "slug", service,
        {
            "name": service.capitalize(),
            "slug": service,
            "provider": provider_pk,
            "meta_launch_url": external_host,
        },
    )
    print(f"[INFO] Application slug={app['slug']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--type", required=True, choices=["proxy", "oidc"])
    parser.add_argument("--external-host", required=True)
    parser.add_argument(
        "--redirect-uri",
        action="append",
        dest="redirect_uris",
        default=None,
        help="OIDC redirect URI (repeatable); defaults to <external-host>/oidc-callback",
    )
    args = parser.parse_args()

    # Tolerate the Job being scheduled before Authentik has finished booting.
    wait_for_authentik()

    if args.type == "proxy":
        provision_proxy(args.service, args.external_host)
    else:
        provision_oidc(args.service, args.external_host, args.redirect_uris)

    print("[SUCCESS] Provisioning complete")


if __name__ == "__main__":
    main()
