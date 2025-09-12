"""
NOAH cluster status utilities
"""

import click


def show_cluster_status(ctx):
    """Show status of all deployed services"""
    click.echo("[VERBOSE] Gathering system status information...")
    click.echo("NOAH System Status")
    click.echo("-" * 50)
    ctx.obj['cluster'].show_status()


def create_status_command(cli_group):
    """Create the status command for the CLI"""
    @cli_group.command()  # type: ignore
    @click.pass_context
    def status(ctx):
        """Show status of all deployed services"""
        show_cluster_status(ctx)
    
    return status