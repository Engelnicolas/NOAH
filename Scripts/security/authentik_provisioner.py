#!/usr/bin/env python3
"""
Authentik SSO Provisioner for NOAH
Idempotently provisions OIDC providers and proxy applications in Authentik
via the REST API. Supports both Headlamp (OIDC) and Hubble UI (forward-auth proxy).
"""

import os
import sys
import time
import json
import logging
from typing import Optional

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' package not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)


class AuthentikProvisioner:
    """
    Idempotent Authentik REST API provisioner.

    Provisions OIDC providers, proxy providers, and applications for NOAH
    services. All operations use get-or-create semantics so the playbooks
    are safe to re-run.
    """

    def __init__(
        self,
        authentik_url: str,
        api_token: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        """
        Args:
            authentik_url: Base URL of Authentik, e.g. https://auth.example.com
            api_token:     Authentik bootstrap/admin API token
            verify_ssl:    Whether to verify TLS (set False for self-signed certs)
            timeout:       HTTP request timeout in seconds
        """
        self.base_url = authentik_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v3"
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Readiness
    # ------------------------------------------------------------------

    def wait_ready(self, max_retries: int = 30, delay: int = 10) -> bool:
        """
        Poll Authentik's /-/health/ready/ until it responds 200 or 204.

        Returns:
            True when ready, False if max_retries exceeded.
        """
        url = f"{self.base_url}/-/health/ready/"
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
                if resp.status_code in (200, 204):
                    logger.info("Authentik is ready.")
                    return True
                logger.debug(
                    "Authentik not ready yet (HTTP %s), attempt %d/%d",
                    resp.status_code,
                    attempt,
                    max_retries,
                )
            except requests.RequestException as exc:
                logger.debug("Connection error on attempt %d/%d: %s", attempt, max_retries, exc)
            time.sleep(delay)
        logger.error("Authentik did not become ready after %d attempts.", max_retries)
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code in (401, 403):
            raise RuntimeError(
                f"Authentik API returned {resp.status_code}: the bootstrap token is invalid or "
                "does not match the token stored in the Authentik database. "
                "Ensure AUTHENTIK_BOOTSTRAP_TOKEN matches the 'bootstrap-token' key in the "
                "'authentik-secret' Kubernetes secret (namespace: identity)."
            )
        resp.raise_for_status()

    def _get(self, path: str, params: Optional[dict] = None) -> requests.Response:
        url = f"{self.api_url}{path}"
        return self.session.get(url, params=params, timeout=self.timeout, verify=self.verify_ssl)

    def _post(self, path: str, data: dict) -> requests.Response:
        url = f"{self.api_url}{path}"
        return self.session.post(url, json=data, timeout=self.timeout, verify=self.verify_ssl)

    def _patch(self, path: str, data: dict) -> requests.Response:
        url = f"{self.api_url}{path}"
        return self.session.patch(url, json=data, timeout=self.timeout, verify=self.verify_ssl)

    def _delete(self, path: str) -> requests.Response:
        url = f"{self.api_url}{path}"
        return self.session.delete(url, timeout=self.timeout, verify=self.verify_ssl)

    def _list_first(self, path: str, params: dict) -> Optional[dict]:
        """Return the first result from a paginated list endpoint, or None."""
        resp = self._get(path, params=params)
        self._raise_for_status(resp)
        results = resp.json().get("results", [])
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Flows and mappings
    # ------------------------------------------------------------------

    def get_authorization_flow(self, slug: str = "default-provider-authorization-implicit-consent") -> str:
        """Return the pk of an authorization flow by slug."""
        flow = self._list_first("/flows/instances/", {"slug": slug})
        if not flow:
            # Fall back to the first available authorization flow
            resp = self._get("/flows/instances/", params={"designation": "authorization"})
            self._raise_for_status(resp)
            results = resp.json().get("results", [])
            if not results:
                raise RuntimeError("No authorization flows found in Authentik.")
            flow = results[0]
        return flow["pk"]

    def get_property_mappings(self, managed_list: Optional[list] = None) -> list:
        """
        Return a list of property-mapping PKs for OIDC scope claims.
        Defaults to the four standard OpenID scopes.
        """
        if managed_list is None:
            # Standard OIDC scopes Headlamp requests (openid/profile/email).
            # offline_access is intentionally omitted — Headlamp does not request
            # it, and advertising an unused scope only confuses consent.
            managed_list = [
                "goauthentik.io/providers/oauth2/scope-openid",
                "goauthentik.io/providers/oauth2/scope-profile",
                "goauthentik.io/providers/oauth2/scope-email",
            ]
        pks = []
        for managed in managed_list:
            mapping = self._list_first("/propertymappings/provider/scope/", {"managed": managed})
            if mapping:
                pks.append(mapping["pk"])
        return pks

    def get_default_outpost(self) -> Optional[dict]:
        """Return the default embedded outpost (type=proxy)."""
        outpost = self._list_first("/outposts/instances/", {"managed": "goauthentik.io/outposts/embedded"})
        if not outpost:
            # Fall back to first proxy outpost
            resp = self._get("/outposts/instances/", params={"type": "proxy"})
            self._raise_for_status(resp)
            results = resp.json().get("results", [])
            outpost = results[0] if results else None
        return outpost

    # ------------------------------------------------------------------
    # OIDC Provider
    # ------------------------------------------------------------------

    def get_or_create_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uris: list,
        authorization_flow_pk: str,
        property_mapping_pks: Optional[list] = None,
    ) -> dict:
        """
        Idempotently create or retrieve an OAuth2/OIDC provider.

        Returns:
            Provider dict from Authentik API.
        """
        existing = self._list_first("/providers/oauth2/", {"name": name})
        if existing:
            logger.info("OIDC provider '%s' already exists (pk=%s).", name, existing["pk"])
            # Patch to ensure redirect URIs stay current
            self._patch(
                f"/providers/oauth2/{existing['pk']}/",
                {"redirect_uris": "\n".join(redirect_uris)},
            )
            return existing

        payload = {
            "name": name,
            "client_id": client_id,
            "client_secret": client_secret,
            "client_type": "confidential",
            "redirect_uris": "\n".join(redirect_uris),
            "authorization_flow": authorization_flow_pk,
            "sub_mode": "hashed_user_id",
            "include_claims_in_id_token": True,
            # per_provider → the discovery `issuer` is ".../application/o/<slug>/",
            # matching the per-application OIDC_ISSUER_URL clients like Headlamp
            # are configured with. "global" would publish the bare base URL and
            # break go-oidc's issuer check.
            "issuer_mode": "per_provider",
        }
        if property_mapping_pks:
            payload["property_mappings"] = property_mapping_pks

        resp = self._post("/providers/oauth2/", payload)
        self._raise_for_status(resp)
        provider = resp.json()
        logger.info("Created OIDC provider '%s' (pk=%s).", name, provider["pk"])
        return provider

    # ------------------------------------------------------------------
    # Proxy Provider (for forward-auth)
    # ------------------------------------------------------------------

    def get_or_create_proxy_provider(
        self,
        name: str,
        external_host: str,
        authorization_flow_pk: str,
        mode: str = "forward_single",
    ) -> dict:
        """
        Idempotently create or retrieve a Proxy provider for forward-auth.

        Args:
            name:                   Provider name.
            external_host:          The URL the proxy will protect (e.g. https://hubble.example.com).
            authorization_flow_pk:  PK of the authorization flow.
            mode:                   'forward_single' or 'forward_domain'.

        Returns:
            Provider dict from Authentik API.
        """
        existing = self._list_first("/providers/proxy/", {"name": name})
        if existing:
            logger.info("Proxy provider '%s' already exists (pk=%s).", name, existing["pk"])
            return existing

        payload = {
            "name": name,
            "external_host": external_host,
            "authorization_flow": authorization_flow_pk,
            "mode": mode,
            "cookie_domain": "",
            "access_token_validity": "hours=24",
            "refresh_token_validity": "days=30",
        }
        resp = self._post("/providers/proxy/", payload)
        self._raise_for_status(resp)
        provider = resp.json()
        logger.info("Created proxy provider '%s' (pk=%s).", name, provider["pk"])
        return provider

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def get_or_create_application(
        self,
        name: str,
        slug: str,
        provider_pk: int,
        meta_launch_url: str = "",
        group: str = "",
    ) -> dict:
        """
        Idempotently create or retrieve an Authentik application.

        Returns:
            Application dict from Authentik API.
        """
        existing = self._list_first("/core/applications/", {"slug": slug})
        if existing:
            logger.info("Application '%s' already exists.", slug)
            return existing

        payload: dict = {
            "name": name,
            "slug": slug,
            "provider": provider_pk,
        }
        if meta_launch_url:
            payload["meta_launch_url"] = meta_launch_url
        if group:
            payload["group"] = group

        resp = self._post("/core/applications/", payload)
        self._raise_for_status(resp)
        app = resp.json()
        logger.info("Created application '%s'.", slug)
        return app

    # ------------------------------------------------------------------
    # Outpost membership
    # ------------------------------------------------------------------

    def add_provider_to_outpost(self, outpost: dict, provider_pk: int) -> None:
        """Add a provider to an outpost (idempotent)."""
        current_providers = outpost.get("providers", [])
        if provider_pk in current_providers:
            logger.info("Provider %s already in outpost '%s'.", provider_pk, outpost.get("name"))
            return

        updated = list(current_providers) + [provider_pk]
        resp = self._patch(f"/outposts/instances/{outpost['pk']}/", {"providers": updated})
        self._raise_for_status(resp)
        logger.info("Added provider %s to outpost '%s'.", provider_pk, outpost.get("name"))

    # ------------------------------------------------------------------
    # High-level provisioning helpers
    # ------------------------------------------------------------------

    def provision_oidc_app(
        self,
        app_name: str,
        app_slug: str,
        client_id: str,
        client_secret: str,
        redirect_uris: list,
        launch_url: str = "",
    ) -> dict:
        """
        Full OIDC application provisioning for services like Headlamp.

        Steps:
          1. Wait for Authentik to be ready.
          2. Resolve authorization flow + property mappings.
          3. Get-or-create OIDC provider.
          4. Get-or-create application linked to provider.

        Returns:
            dict with keys: provider, application
        """
        logger.info("Provisioning OIDC app '%s' (client_id=%s)…", app_name, client_id)

        auth_flow_pk = self.get_authorization_flow()
        mapping_pks = self.get_property_mappings()
        provider = self.get_or_create_provider(
            name=f"{app_name} Provider",
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uris,
            authorization_flow_pk=auth_flow_pk,
            property_mapping_pks=mapping_pks,
        )
        application = self.get_or_create_application(
            name=app_name,
            slug=app_slug,
            provider_pk=provider["pk"],
            meta_launch_url=launch_url,
        )
        return {"provider": provider, "application": application}

    def provision_proxy_app(
        self,
        app_name: str,
        app_slug: str,
        external_host: str,
        mode: str = "forward_single",
    ) -> dict:
        """
        Full proxy/forward-auth application provisioning for services like Hubble UI.

        Steps:
          1. Resolve authorization flow.
          2. Get-or-create proxy provider.
          3. Get-or-create application linked to provider.
          4. Add provider to the default embedded outpost.

        Returns:
            dict with keys: provider, application, outpost
        """
        logger.info("Provisioning proxy app '%s' (host=%s)…", app_name, external_host)

        auth_flow_pk = self.get_authorization_flow()
        provider = self.get_or_create_proxy_provider(
            name=f"{app_name} Provider",
            external_host=external_host,
            authorization_flow_pk=auth_flow_pk,
            mode=mode,
        )
        application = self.get_or_create_application(
            name=app_name,
            slug=app_slug,
            provider_pk=provider["pk"],
            meta_launch_url=external_host,
        )
        outpost = self.get_default_outpost()
        if outpost:
            self.add_provider_to_outpost(outpost, provider["pk"])
        else:
            logger.warning("No embedded outpost found; skipping outpost membership.")

        return {"provider": provider, "application": application, "outpost": outpost}

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def delete_application(self, slug: str) -> bool:
        """
        Delete an Authentik application by slug (and its linked provider).

        Returns:
            True if deleted, False if not found.
        """
        app = self._list_first("/core/applications/", {"slug": slug})
        if not app:
            logger.info("Application '%s' not found; nothing to delete.", slug)
            return False

        provider_pk = app.get("provider")
        resp = self._delete(f"/core/applications/{app['pk']}/")
        self._raise_for_status(resp)
        logger.info("Deleted application '%s'.", slug)

        if provider_pk:
            # Attempt to delete the linked provider (best-effort)
            for provider_path in ("/providers/oauth2/", "/providers/proxy/"):
                del_resp = self._delete(f"{provider_path}{provider_pk}/")
                if del_resp.status_code in (200, 204):
                    logger.info("Deleted provider pk=%s.", provider_pk)
                    break

        return True


# ---------------------------------------------------------------------------
# CLI entry-point (called from Ansible shell tasks)
# ---------------------------------------------------------------------------

def _build_provisioner_from_env() -> "AuthentikProvisioner":
    """Build an AuthentikProvisioner from environment variables."""
    url = os.environ.get("AUTHENTIK_URL", "")
    token = os.environ.get("AUTHENTIK_BOOTSTRAP_TOKEN", "")
    if not url or not token:
        raise RuntimeError(
            "AUTHENTIK_URL and AUTHENTIK_BOOTSTRAP_TOKEN must be set in the environment."
        )
    verify_ssl = os.environ.get("AUTHENTIK_VERIFY_SSL", "true").lower() != "false"
    return AuthentikProvisioner(url, token, verify_ssl=verify_ssl)


def _cli_provision_headlamp(domain: str) -> None:
    """Provision Headlamp OIDC app (called from Ansible)."""
    provisioner = _build_provisioner_from_env()

    if not provisioner.wait_ready():
        print("[ERROR] Authentik is not ready. Aborting.", file=sys.stderr)
        sys.exit(1)

    client_id = os.environ.get("HEADLAMP_OIDC_CLIENT_ID", "headlamp")
    client_secret = os.environ.get("HEADLAMP_OIDC_CLIENT_SECRET", "")
    if not client_secret:
        raise RuntimeError("HEADLAMP_OIDC_CLIENT_SECRET must be set in the environment.")

    redirect_uris = [f"https://headlamp.{domain}/oidc-callback"]
    result = provisioner.provision_oidc_app(
        app_name="Headlamp",
        app_slug="headlamp",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=redirect_uris,
        launch_url=f"https://headlamp.{domain}",
    )
    print(json.dumps({"status": "ok", "slug": result["application"]["slug"]}))


def _cli_provision_hubble(domain: str) -> None:
    """Provision Hubble UI forward-auth proxy app (called from Ansible)."""
    provisioner = _build_provisioner_from_env()

    if not provisioner.wait_ready():
        print("[ERROR] Authentik is not ready. Aborting.", file=sys.stderr)
        sys.exit(1)

    external_host = f"https://hubble.{domain}"
    result = provisioner.provision_proxy_app(
        app_name="Hubble UI",
        app_slug="hubble-ui",
        external_host=external_host,
        mode="forward_single",
    )
    print(json.dumps({"status": "ok", "slug": result["application"]["slug"]}))


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Authentik SSO Provisioner for NOAH")
    parser.add_argument(
        "command",
        choices=["provision-headlamp", "provision-hubble", "wait-ready"],
        help="Action to perform",
    )
    parser.add_argument("--domain", default="", help="Base domain")
    args = parser.parse_args()

    if args.command == "provision-headlamp":
        _cli_provision_headlamp(args.domain)
    elif args.command == "provision-hubble":
        _cli_provision_hubble(args.domain)
    elif args.command == "wait-ready":
        provisioner = _build_provisioner_from_env()
        ok = provisioner.wait_ready()
        sys.exit(0 if ok else 1)
