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
import socket
import ssl
import subprocess
import time
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


def _node_internal_ips() -> List[str]:
    """Node InternalIPs via kubectl — the DNS-independent connect targets for the
    URL probe. nginx binds the node's :443 (hostPort), so these reach the same
    ingress as the public hostname, yet unlike the public EIP they're reachable
    from the node itself (AWS 1:1 NAT has no hairpin to the instance's own EIP)."""
    data, _ = _get_json("nodes")
    if not data:
        return []
    ips: List[str] = []
    for item in data.get("items", []):
        for addr in item.get("status", {}).get("addresses", []):
            if addr.get("type") == "InternalIP" and addr.get("address"):
                ips.append(addr["address"])
    return ips


def _status_code(status_line: str) -> Optional[int]:
    """Parse the numeric status from an HTTP status line (`HTTP/1.1 200 OK`)."""
    parts = status_line.split()
    if len(parts) >= 2 and parts[0].startswith("HTTP/"):
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def _probe_host(host: str, connect_ips: List[str], timeout: int) -> Tuple[bool, str]:
    """Probe https://host without DNS: connect to each candidate node-local IP in
    turn, always presenting `host` for SNI + the HTTP Host header so TLS validates
    against the service's Let's Encrypt cert and nginx routes by vhost. Returns
    (reachable, detail).

    Any HTTP status (200/302/401/…) means the ingress + app are serving → reachable;
    only connection/TLS failures count as a miss. TLS is verified (default context),
    so a not-yet-issued cert surfaces as unreachable until issuance completes."""
    ctx = ssl.create_default_context()
    last = "no node-local address to probe"
    for ip in connect_ips:
        try:
            with socket.create_connection((ip, 443), timeout=timeout) as raw, \
                    ctx.wrap_socket(raw, server_hostname=host) as tls:
                tls.settimeout(timeout)
                tls.sendall(
                    f"GET / HTTP/1.1\r\nHost: {host}\r\n"
                    "User-Agent: noah-verify\r\nConnection: close\r\n\r\n".encode()
                )
                buf = b""
                while b"\r\n" not in buf and len(buf) < 256:
                    chunk = tls.recv(256 - len(buf))
                    if not chunk:
                        break
                    buf += chunk
            status_line = buf.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        except ssl.SSLError as exc:
            # The server completed the TCP connect but the TLS cert isn't valid
            # yet (e.g. Let's Encrypt issuance pending). Every node-local target
            # serves the same cert, so stop here rather than retry.
            return False, str(exc) or exc.__class__.__name__
        except OSError as exc:
            # Connection refused/timeout on this candidate — try the next one.
            last = str(exc) or exc.__class__.__name__
            continue
        code = _status_code(status_line)
        if code is not None:
            return True, f"HTTP {code} (via {ip})"
        last = f"unexpected response {status_line!r}"
    return False, last


def _check_urls(domain: str, timeout: int = 10) -> List[Row]:
    """Probe each service URL once; returns one (url, reachable, detail) Row each.

    DNS-independent: connects to node-local addresses (the node's InternalIP, then
    loopback) rather than resolving the public hostname. On the single-node EC2 the
    public EIP isn't reachable from the node (AWS 1:1 NAT has no hairpin) and public
    DNS may not resolve on the node yet — both would surface as a false 'timed out'.
    SNI/Host stays the service host so TLS still validates against the LE cert."""
    connect_ips = _node_internal_ips()
    connect_ips.append("127.0.0.1")
    rows: List[Row] = []
    for sub in _SERVICE_SUBDOMAINS:
        host = f"{sub}.{domain}"
        ok, detail = _probe_host(host, connect_ips, timeout)
        rows.append((f"https://{host}", ok, detail))
    return rows


def _all_urls_ok(url_rows: Optional[List[Row]]) -> bool:
    return bool(url_rows) and all(ok for _, ok, _ in url_rows)


def _print_node_side_help() -> None:
    click.echo("  Check status directly on the cluster node:")
    click.echo("    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml")
    click.echo("    flux get all --all-namespaces")


def _print_admin_credentials(domain: Optional[str]) -> None:
    """Print the Authentik admin login provisioned during bootstrap (user
    `akadmin`). Best-effort: the password lives in the SOPS-encrypted canonical
    store, so this prints a hint instead when it can't be read (e.g. no Age key
    on this machine)."""
    try:
        from Scripts.core_helm.authentik_credentials import get_authentik_credentials
        creds, err = get_authentik_credentials(domain=domain)
    except Exception as exc:  # pragma: no cover - defensive
        creds, err = None, str(exc)

    click.echo(click.style("\n Authentik admin login:", bold=True))
    if creds:
        click.echo(f"   Username : {creds['admin_username']}")
        click.echo(f"   Password : {creds['admin_password']}")
        click.echo(click.style(
            "   (From the canonical secrets store — also via `noah password show-password`.)",
            fg="bright_black"))
    else:
        click.echo(click.style(f"   Could not read admin credentials ({err}).", fg="yellow"))
        click.echo("   Retrieve them with: noah password show-password")


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
                "   (Flux converged but some URLs aren't serving yet — the ingress "
                "controller or Let's Encrypt TLS issuance can take a few minutes.)", fg="bright_black"))


def verify_deployment(domain: Optional[str] = None, timeout: int = 600,
                      poll_interval: int = 10, url_timeout: int = 300) -> bool:
    """Verify a deployment in two phases and return True only if both pass:

    1. Poll until all Flux Kustomizations + HelmReleases are Ready (or `timeout`
       seconds elapse).
    2. Once Flux has converged and a `domain` is known, poll the service URLs over
       HTTPS until they all respond (or `url_timeout` seconds elapse) — this
       confirms the ingress serves each vhost and TLS is issued. The probe is
       DNS-independent: it connects to node-local addresses (see `_check_urls`),
       not the public hostname, so it works when run on the node itself. Skipped
       when no domain is provided, preserving the Flux-only verdict.

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

    # Phase 2: confirm the URLs actually serve (ingress routes the vhost and TLS
    # is issued), probing node-local addresses so it works on the node itself.
    # Only meaningful once Flux has converged and a domain is known; otherwise
    # url_rows stays None and the verdict is Flux-only.
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
    # Surface the admin login only once the deployment fully succeeded (URLs
    # validated), so the operator can sign in immediately.
    if success and domain:
        _print_admin_credentials(domain)
    return success
