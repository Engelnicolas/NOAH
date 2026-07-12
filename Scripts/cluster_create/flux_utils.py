"""
NOAH v0.0.9 — `noah flux ...` command implementations.

Thin wrappers over the official flux CLI. They exist so operators
running NOAH from the workdir don't need to remember the longer flux
incantations and so we can layer NOAH-specific defaults (e.g. log
namespace = flux-system) on top.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import click  # type: ignore

from Scripts.utils.paths import NOAH_PATHS


def _require_flux() -> None:
    if shutil.which("flux") is None:
        raise click.ClickException(
            "flux CLI not found in PATH. Run `noah cluster bootstrap` first, "
            "or install flux from https://fluxcd.io/flux/installation/."
        )


def _require_kubeconfig() -> None:
    candidates = [
        os.environ.get("KUBECONFIG"),
        str(Path.home() / ".kube" / "config"),
        str(NOAH_PATHS["root_dir"] / "Kube" / "noah-cluster.yaml"),
    ]
    for path in candidates:
        if path and Path(path).exists():
            os.environ["KUBECONFIG"] = path
            return
    raise click.ClickException(
        "No kubeconfig found. This command must run on a node with cluster access.\n"
        "  On the cluster node:  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml\n"
        "  Or copy the kubeconfig to ~/.kube/config on this machine."
    )


def _run(cmd: List[str]) -> int:
    return subprocess.run(cmd).returncode


def cmd_sync() -> int:
    """Force immediate reconciliation of every Kustomization + HelmRelease."""
    _require_flux()
    _require_kubeconfig()
    click.echo("🔁 Reconciling all Kustomizations …")
    rc1 = _run(["flux", "reconcile", "kustomization", "--all", "--with-source"])
    click.echo("🔁 Reconciling all HelmReleases …")
    rc2 = _run(["flux", "reconcile", "helmrelease", "--all"])
    return rc1 or rc2


def cmd_status() -> int:
    """Show the state of every Flux resource in the cluster."""
    _require_flux()
    _require_kubeconfig()
    click.echo("== GitRepositories ==")
    _run(["flux", "get", "sources", "git", "--all-namespaces"])
    click.echo("\n== HelmRepositories ==")
    _run(["flux", "get", "sources", "helm", "--all-namespaces"])
    click.echo("\n== Kustomizations ==")
    _run(["flux", "get", "kustomizations", "--all-namespaces"])
    click.echo("\n== HelmReleases ==")
    _run(["flux", "get", "helmreleases", "--all-namespaces"])
    return 0


def cmd_logs(follow: bool, tail: int) -> int:
    """Aggregate logs from the Flux controllers in flux-system."""
    _require_flux()
    _require_kubeconfig()
    cmd = ["flux", "logs", "--all-namespaces", f"--tail={tail}"]
    if follow:
        cmd.append("--follow")
    return _run(cmd)
