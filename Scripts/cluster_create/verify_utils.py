"""
NOAH — post-bootstrap deployment verification.

`flux bootstrap` only *kicks off* reconciliation; cert-manager, external-dns,
Authentik, Headlamp, etc. become Ready over the following minutes. This module
polls the Flux Kustomizations + HelmReleases until they all report Ready (or a
timeout elapses) and prints a clear per-component verdict, so an operator knows
whether the cluster actually finished deploying.

Reused by `noah cluster verify` and by the tail of `noah cluster bootstrap`.
"""
from __future__ import annotations

import json
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

import click  # type: ignore

# Fully-qualified resource names so we don't collide with any same-short-name CRD.
KUSTOMIZATION_RESOURCE = "kustomizations.kustomize.toolkit.fluxcd.io"
HELMRELEASE_RESOURCE = "helmreleases.helm.toolkit.fluxcd.io"

# Service subdomains exposed via Ingress; probed for end-to-end reachability.
_SERVICE_SUBDOMAINS = ("auth", "headlamp", "hubble")

_RULE = "─" * 60

# (relative/name, ready, message)
Row = Tuple[str, bool, str]


def _kubectl_available() -> bool:
    return shutil.which("kubectl") is not None


def _get_json(resource: str) -> Tuple[Optional[dict], str]:
    """`kubectl get <resource> -A -o json`. Returns (parsed, error)."""
    r = subprocess.run(
        ["kubectl", "get", resource, "-A", "-o", "json"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None, r.stderr.strip()
    try:
        return json.loads(r.stdout), ""
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        return None, str(exc)


def _ready(item: dict) -> Tuple[bool, str]:
    """Read the Flux `Ready` condition of a single resource."""
    for cond in item.get("status", {}).get("conditions", []):
        if cond.get("type") == "Ready":
            return cond.get("status") == "True", cond.get("message", "").strip()
    return False, "no Ready condition yet (reconciling…)"


def _collect(resource: str) -> Tuple[List[Row], str]:
    data, err = _get_json(resource)
    if data is None:
        return [], err
    rows: List[Row] = []
    for item in data.get("items", []):
        meta = item.get("metadata", {})
        name = f"{meta.get('namespace', '')}/{meta.get('name', '')}"
        ok, msg = _ready(item)
        rows.append((name, ok, msg))
    return rows, ""


def _all_ready(ks_rows: List[Row], hr_rows: List[Row]) -> bool:
    # Require at least one of each so we don't declare success before the CRDs
    # have produced any objects.
    return (
        bool(ks_rows) and bool(hr_rows)
        and all(ok for _, ok, _ in ks_rows)
        and all(ok for _, ok, _ in hr_rows)
    )


def _probe_url(url: str, timeout: int) -> Tuple[bool, str]:
    """Probe a URL over HTTPS. Returns (reachable, detail).

    Any HTTP status (200/302/401/…) means the ingress + app are serving, so it
    counts as reachable — only a connection/DNS/TLS error counts as a failure.
    TLS is verified (default context), so a not-yet-issued Let's Encrypt cert
    surfaces as unreachable until issuance completes."""
    req = urllib.request.Request(url, method="GET")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        # Server responded with a 4xx/5xx — the stack is reachable.
        return True, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def _check_urls(domain: str, timeout: int = 10) -> List[Row]:
    """Probe each service URL once; returns one (url, reachable, detail) Row each."""
    rows: List[Row] = []
    for sub in _SERVICE_SUBDOMAINS:
        url = f"https://{sub}.{domain}"
        ok, detail = _probe_url(url, timeout)
        rows.append((url, ok, detail))
    return rows


def _all_urls_ok(url_rows: Optional[List[Row]]) -> bool:
    return bool(url_rows) and all(ok for _, ok, _ in url_rows)


def _print_node_side_help() -> None:
    click.echo("  Check status directly on the cluster node:")
    click.echo("    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml")
    click.echo("    flux get all --all-namespaces")


def _print_summary(ks_rows: List[Row], hr_rows: List[Row], success: bool,
                   url_rows: Optional[List[Row]], domain: Optional[str]) -> None:
    click.echo("\n" + _RULE)
    if success:
        msg = " ✅ Cluster deployed — components Ready" + (
            " and URLs reachable" if url_rows is not None else ""
        )
        click.echo(click.style(msg, fg="green", bold=True))
    else:
        click.echo(click.style(" ❌ Cluster NOT fully converged within the timeout", fg="red", bold=True))
    click.echo(_RULE)

    def _emit(title: str, rows: List[Row], show_detail_when_ok: bool = False) -> None:
        click.echo(click.style(f"\n {title}", bold=True))
        if not rows:
            click.echo(click.style("   (none found yet)", fg="yellow"))
            return
        for name, ok, msg in sorted(rows):
            icon = click.style("✔", fg="green") if ok else click.style("✗", fg="red", bold=True)
            line = f"   {icon}  {name}"
            if msg and (not ok or show_detail_when_ok):
                line += click.style(f"  — {msg}", fg="bright_black")
            click.echo(line)

    _emit("Kustomizations", ks_rows)
    _emit("HelmReleases", hr_rows)
    if url_rows is not None:
        _emit("Access URLs", url_rows, show_detail_when_ok=True)

    if not success:
        click.echo(click.style("\n Investigate with:", bold=True))
        click.echo("   noah flux status")
        click.echo("   flux get all --all-namespaces")
        click.echo("   flux logs --level=error --all-namespaces")
        click.echo("   noah cluster verify        # re-check after it has had more time")
        if _all_ready(ks_rows, hr_rows) and not _all_urls_ok(url_rows):
            click.echo(click.style(
                "   (Flux converged but some URLs aren't reachable yet — DNS propagation "
                "or Let's Encrypt TLS issuance can take a few minutes.)", fg="bright_black"))


def verify_deployment(domain: Optional[str] = None, timeout: int = 600,
                      poll_interval: int = 10, url_timeout: int = 300) -> bool:
    """Verify a deployment in two phases and return True only if both pass:

    1. Poll until all Flux Kustomizations + HelmReleases are Ready (or `timeout`
       seconds elapse).
    2. Once Flux has converged and a `domain` is known, poll the public service
       URLs over HTTPS until they all respond (or `url_timeout` seconds elapse) —
       this confirms DNS resolves to the node and TLS is issued. Skipped when no
       domain is provided, preserving the Flux-only verdict.

    Prints live progress and a final verdict.
    """
    # Import here to avoid a heavy import at module load and to reuse the same
    # kubeconfig resolution as `noah flux ...`.
    from Scripts.cluster_create.flux_utils import _require_kubeconfig

    if not _kubectl_available():
        click.echo(click.style("⚠️  kubectl not found on this machine — cannot verify from here.", fg="yellow"))
        _print_node_side_help()
        return False

    try:
        _require_kubeconfig()  # sets KUBECONFIG in env or raises
    except click.ClickException as exc:
        click.echo(click.style(f"⚠️  {exc.message}", fg="yellow"))
        _print_node_side_help()
        return False

    click.echo("\n" + _RULE)
    click.echo(click.style(" Verifying deployment (waiting for Flux to converge)", bold=True))
    click.echo(_RULE)
    click.echo(click.style(f"  timeout={timeout}s  poll={poll_interval}s\n", fg="bright_black"))

    deadline = time.monotonic() + timeout
    ks_rows: List[Row] = []
    hr_rows: List[Row] = []
    while True:
        ks_rows, _ = _collect(KUSTOMIZATION_RESOURCE)
        hr_rows, _ = _collect(HELMRELEASE_RESOURCE)

        ks_ready = sum(1 for _, ok, _ in ks_rows if ok)
        hr_ready = sum(1 for _, ok, _ in hr_rows if ok)
        remaining = int(deadline - time.monotonic())
        click.echo(
            f"  Kustomizations {ks_ready}/{len(ks_rows)} ready · "
            f"HelmReleases {hr_ready}/{len(hr_rows)} ready · "
            f"{max(remaining, 0)}s left"
        )

        if _all_ready(ks_rows, hr_rows):
            break
        if remaining <= 0:
            break
        time.sleep(min(poll_interval, max(remaining, 1)))

    flux_ok = _all_ready(ks_rows, hr_rows)

    # Phase 2: confirm the public URLs actually serve (DNS resolves to the node's
    # public IP and TLS is issued). Only meaningful once Flux has converged and a
    # domain is known; otherwise url_rows stays None and the verdict is Flux-only.
    url_rows: Optional[List[Row]] = None
    if flux_ok and domain:
        click.echo(click.style(
            f"\n Flux converged — checking URL reachability (timeout={url_timeout}s)", bold=True))
        url_deadline = time.monotonic() + url_timeout
        while True:
            url_rows = _check_urls(domain)
            ok = sum(1 for _, o, _ in url_rows if o)
            remaining = int(url_deadline - time.monotonic())
            click.echo(f"  URLs {ok}/{len(url_rows)} reachable · {max(remaining, 0)}s left")
            if _all_urls_ok(url_rows):
                break
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, max(remaining, 1)))

    success = flux_ok and (url_rows is None or _all_urls_ok(url_rows))
    _print_summary(ks_rows, hr_rows, success, url_rows, domain)
    return success
