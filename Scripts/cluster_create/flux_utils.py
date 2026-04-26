"""
NOAH v0.0.9 — `noah flux ...` command implementations.

Thin wrappers over the official flux CLI. They exist so operators
running NOAH from the workdir don't need to remember the longer flux
incantations and so we can layer NOAH-specific defaults (e.g. log
namespace = flux-system) on top.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import List

import click  # type: ignore


def _require_flux() -> None:
    if shutil.which("flux") is None:
        raise click.ClickException(
            "flux CLI not found in PATH. Run `noah cluster bootstrap` first, "
            "or install flux from https://fluxcd.io/flux/installation/."
        )


def _run(cmd: List[str]) -> int:
    return subprocess.run(cmd).returncode


def cmd_sync() -> int:
    """Force immediate reconciliation of every Kustomization + HelmRelease."""
    _require_flux()
    click.echo("🔁 Reconciling all Kustomizations …")
    rc1 = _run(["flux", "reconcile", "kustomization", "--all", "--with-source"])
    click.echo("🔁 Reconciling all HelmReleases …")
    rc2 = _run(["flux", "reconcile", "helmrelease", "--all"])
    return rc1 or rc2


def cmd_status() -> int:
    """Show the state of every Flux resource in the cluster."""
    _require_flux()
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
    cmd = ["flux", "logs", "--all-namespaces", f"--tail={tail}"]
    if follow:
        cmd.append("--follow")
    return _run(cmd)
