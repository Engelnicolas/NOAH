"""
NOAH cluster status utilities
"""

import click


def show_cluster_status(ctx):
    """Show status of all deployed services with fallback messaging."""
    click.echo("[VERBOSE] Gathering system status information...")
    click.echo("NOAH System Status")
    click.echo("-" * 50)
    before_count = ctx.obj.get('_status_lines_printed', 0)
    # Delegate to cluster manager
    ctx.obj['cluster'].show_status()
    after_count = ctx.obj.get('_status_lines_printed', before_count)
    # If no cluster output occurred and no warnings were printed, show fallback
    # (ClusterManager.show_status already prints warnings if no client, so only fallback if completely quiet)
    # We'll implement a simple heuristic: if Kubernetes client is None and nothing else printed beyond header.
    if getattr(ctx.obj['cluster'], 'apps_v1', None) is None:
        # Already prints warnings internally; nothing extra needed.
        return
    # If apps_v1 exists but produced no deployment lines, indicate empty namespaces
    # (We could enhance ClusterManager to return data, but here we add a quick pass.)
    # This is a lightweight enhancement: check two target namespaces for emptiness.
    try:
        namespaces = ['identity', 'kube-system']
        printed_any = False
        # A crude detection: we cannot easily know printed lines without intercepting stdout; so we
        # re-query and print an explicit message if both namespaces lack deployments.
        empty_all = True
        for ns in namespaces:
            # Attempt list again but don't duplicate if deployments previously printed.
            deployments = ctx.obj['cluster'].apps_v1.list_namespaced_deployment(namespace=ns)
            if deployments.items:
                empty_all = False
                break
        if empty_all:
            click.echo("(No deployments found in monitored namespaces: identity, kube-system)")
            click.echo("💡 If you just created the cluster, deploy components: python noah.py deploy all")
    except Exception:
        # Swallow secondary errors silently to avoid clutter
        pass


def create_status_command(cli_group):
    """Create the status command for the CLI"""
    @cli_group.command()  # type: ignore
    @click.pass_context
    def status(ctx):
        """Show status of all deployed services"""
        show_cluster_status(ctx)
    
    return status