"""
NOAH CLI - kubectl Utilities

This module contains kubectl-related utility functions for the NOAH CLI.
Helps manage kubectl configuration, cache, and environment cleanup.
"""

import os
import shutil
import click
from pathlib import Path


def cleanup_kubectl_cache():
    """
    Clean up kubectl client cache and configuration to prevent memcache errors.
    
    This function removes:
    - ~/.kube/config file
    - ~/.kube/cache directory  
    - KUBECONFIG environment variable (if pointing to K3s config)
    
    This prevents kubectl memcache errors after cluster destruction by ensuring
    the client doesn't try to connect to non-existent clusters.
    
    Returns:
        bool: True if cleanup was successful, False if errors occurred
    """
    try:
        kube_dir = Path.home() / '.kube'
        success = True
        
        # Remove kubectl config file
        config_file = kube_dir / 'config'
        if config_file.exists():
            config_file.unlink()
            click.echo("[VERBOSE] Removed kubectl config file")
        
        # Remove kubectl cache directory
        cache_dir = kube_dir / 'cache'
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            click.echo("[VERBOSE] Removed kubectl cache directory")
        
        # Clear KUBECONFIG environment variable if it points to removed K3s config
        kubeconfig = os.environ.get('KUBECONFIG')
        if kubeconfig == '/etc/rancher/k3s/k3s.yaml':
            if 'KUBECONFIG' in os.environ:
                del os.environ['KUBECONFIG']
            click.echo("[VERBOSE] Cleared KUBECONFIG environment variable")
        
        click.echo("[VERBOSE] kubectl cache cleanup completed - memcache errors should be resolved")
        return True
        
    except Exception as e:
        click.echo(f"[WARNING] kubectl cache cleanup failed: {e}")
        return False


def verify_kubectl_disconnected():
    """
    Verify that kubectl is properly disconnected from any cluster.
    
    This function checks that kubectl shows appropriate "no cluster" behavior
    after a cluster has been destroyed.
    
    Returns:
        dict: Status information about kubectl state
    """
    try:
        import subprocess
        
        # Test kubectl version (should work without cluster)
        try:
            result = subprocess.run(
                ['kubectl', 'version', '--client=true'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            client_version_works = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            client_version_works = False
        
        # Test kubectl cluster connection (should fail cleanly)
        try:
            result = subprocess.run(
                ['kubectl', 'cluster-info'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            cluster_accessible = result.returncode == 0
            connection_error = "connection refused" in result.stderr.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            cluster_accessible = False
            connection_error = False
        
        return {
            'kubectl_available': client_version_works,
            'cluster_accessible': cluster_accessible,
            'clean_disconnection': not cluster_accessible and connection_error,
            'status': 'clean' if (client_version_works and not cluster_accessible) else 'needs_cleanup'
        }
        
    except Exception as e:
        click.echo(f"[WARNING] kubectl verification failed: {e}")
        return {
            'kubectl_available': False,
            'cluster_accessible': False, 
            'clean_disconnection': False,
            'status': 'error',
            'error': str(e)
        }


def reset_kubectl_environment():
    """
    Completely reset kubectl environment to a clean state.
    
    This is a more comprehensive cleanup that ensures kubectl starts fresh
    without any cached or stale configuration.
    
    Returns:
        bool: True if reset was successful
    """
    try:
        kube_dir = Path.home() / '.kube'
        
        # Remove entire .kube directory if it exists
        if kube_dir.exists():
            shutil.rmtree(kube_dir)
            click.echo("[VERBOSE] Removed entire ~/.kube directory")
        
        # Clear all kubectl-related environment variables
        kubectl_env_vars = [
            'KUBECONFIG',
            'KUBERNETES_SERVICE_HOST',
            'KUBERNETES_SERVICE_PORT',
            'KUBECTL_EXTERNAL_DIFF'
        ]
        
        cleared_vars = []
        for var in kubectl_env_vars:
            if var in os.environ:
                del os.environ[var]
                cleared_vars.append(var)
        
        if cleared_vars:
            click.echo(f"[VERBOSE] Cleared environment variables: {', '.join(cleared_vars)}")
        
        click.echo("[VERBOSE] kubectl environment completely reset")
        return True
        
    except Exception as e:
        click.echo(f"[WARNING] kubectl environment reset failed: {e}")
        return False


def get_kubectl_status():
    """
    Get current kubectl configuration status.
    
    Returns:
        dict: Information about current kubectl state
    """
    try:
        kube_dir = Path.home() / '.kube'
        
        status = {
            'kube_dir_exists': kube_dir.exists(),
            'config_file_exists': (kube_dir / 'config').exists(),
            'cache_dir_exists': (kube_dir / 'cache').exists(),
            'kubeconfig_env': os.environ.get('KUBECONFIG'),
            'kubeconfig_file_exists': False
        }
        
        # Check if KUBECONFIG points to existing file
        kubeconfig_path = status['kubeconfig_env']
        if kubeconfig_path:
            status['kubeconfig_file_exists'] = Path(kubeconfig_path).exists()
        
        return status
        
    except Exception as e:
        return {'error': str(e)}


def display_kubectl_status():
    """Display current kubectl configuration status in a user-friendly format."""
    status = get_kubectl_status()
    
    if 'error' in status:
        click.echo(f"[ERROR] Could not get kubectl status: {status['error']}")
        return
    
    click.echo("\n=== kubectl Configuration Status ===")
    click.echo(f"~/.kube directory: {'✅ EXISTS' if status['kube_dir_exists'] else '❌ NOT FOUND'}")
    click.echo(f"~/.kube/config file: {'✅ EXISTS' if status['config_file_exists'] else '❌ NOT FOUND'}")
    click.echo(f"~/.kube/cache directory: {'✅ EXISTS' if status['cache_dir_exists'] else '❌ NOT FOUND'}")
    
    kubeconfig = status['kubeconfig_env']
    if kubeconfig:
        file_exists = status['kubeconfig_file_exists']
        click.echo(f"KUBECONFIG env var: {kubeconfig}")
        click.echo(f"KUBECONFIG file exists: {'✅ YES' if file_exists else '❌ NO (stale)'}")
    else:
        click.echo("KUBECONFIG env var: ❌ NOT SET")
    
    click.echo("=====================================\n")
