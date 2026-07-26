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

"""Kubernetes cluster management module"""

import subprocess
import json
import time
import sys
from pathlib import Path
from typing import Any, Optional, List

# Optional imports with graceful fallbacks
client: Optional[Any] = None
config: Optional[Any] = None
ApiException: Optional[Any] = None

try:
    from kubernetes import client, config  # type: ignore
    from kubernetes.client.rest import ApiException  # type: ignore
except ImportError:
    # Attempt late import after adding virtualenv site-packages in _initialize_kubernetes
    client = None  # type: ignore
    config = None  # type: ignore
    ApiException = None  # type: ignore

class ClusterManager:
    def __init__(self, config_loader):
        self.config = config_loader
        self.k8s_client = None
        self.apps_v1 = None
        self.core_v1 = None
        self._initialize_kubernetes()
    
    def _initialize_kubernetes(self):
        """Initialize Kubernetes clients"""
        global client, config, ApiException

        if client is None or config is None:
            # Try to dynamically discover a local .venv if user forgot to activate it
            venv_candidates: List[Path] = []
            cwd = Path.cwd()
            venv_dir = cwd / '.venv'
            if venv_dir.exists():
                # Typical Linux/macOS path
                site_pkgs = venv_dir / 'lib'
                if site_pkgs.exists():
                    # Find python* directory then site-packages
                    for py_dir in site_pkgs.iterdir():
                        if py_dir.is_dir() and py_dir.name.startswith('python'):
                            sp = py_dir / 'site-packages'
                            if sp.exists():
                                venv_candidates.append(sp)
                # Windows layout fallback
                win_sp = venv_dir / 'Lib' / 'site-packages'
                if win_sp.exists():
                    venv_candidates.append(win_sp)
            # Deduplicate while preserving order
            added_paths = []
            for p in venv_candidates:
                p_str = str(p)
                if p_str not in sys.path:
                    sys.path.insert(0, p_str)
                    added_paths.append(p_str)
            if added_paths:
                try:
                    from kubernetes import client as k_client, config as k_config  # type: ignore
                    from kubernetes.client.rest import ApiException as KApiException  # type: ignore
                    client, config, ApiException = k_client, k_config, KApiException
                except Exception:
                    pass
        if client is None or config is None:
            print("Warning: Could not initialize Kubernetes client: kubernetes library not available (activate venv with 'source .venv/bin/activate')")
            return
        
        try:
            try:
                config.load_kube_config()
            except Exception:
                config.load_incluster_config()

            self.k8s_client = client.ApiClient()
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
        except Exception as e:
            print(f"Warning: Could not initialize Kubernetes client: {e}")
    
    def create_namespace(self, namespace: str) -> bool:
        """Create a Kubernetes namespace"""
        if self.core_v1 is None or client is None:
            print(f"⚠️  Warning: No Kubernetes cluster connected. Cannot create namespace {namespace}")
            print("💡 To connect to a cluster, ensure kubectl is configured or run: python noah.py cluster create")
            return False
        
        try:
            body = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace)
            )
            self.core_v1.create_namespace(body)
            return True
        except Exception as e:
            # Handle both ApiException and general exceptions
            if hasattr(e, 'status') and getattr(e, 'status', None) == 409:  # Already exists
                return True
            print(f"Error creating namespace: {e}")
            return False
    
    def delete_namespace(self, namespace: str) -> bool:
        """Delete a Kubernetes namespace"""
        if self.core_v1 is None:
            print(f"⚠️  Warning: No Kubernetes cluster connected. Cannot delete namespace {namespace}")
            print("💡 To connect to a cluster, ensure kubectl is configured or run: python noah.py cluster create")
            return False
        
        try:
            self.core_v1.delete_namespace(name=namespace)
            return True
        except Exception as e:
            print(f"Error deleting namespace: {e}")
            return False
    
    def wait_for_deployment(self, deployment_name: str, namespace: str, timeout: int = 300):
        """Wait for a deployment to be ready"""
        if self.apps_v1 is None:
            print(f"⚠️  Warning: No Kubernetes cluster connected. Skipping deployment wait for {deployment_name}")
            print("💡 To connect to a cluster, ensure kubectl is configured or run: python noah.py cluster create")
            return True  # Skip the wait if no cluster is available
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace
                )
                if deployment.status.ready_replicas == deployment.spec.replicas:
                    return True
                time.sleep(5)
            except Exception:
                time.sleep(5)
        return False
    
    def get_service_endpoint(self, service_name: str, namespace: str) -> Optional[str]:
        """Get the endpoint for a service"""
        if self.core_v1 is None:
            print(f"⚠️  Warning: No Kubernetes cluster connected. Cannot get endpoint for {service_name}")
            print("💡 To connect to a cluster, ensure kubectl is configured or run: python noah.py cluster create")
            return None
        
        try:
            service = self.core_v1.read_namespaced_service(
                name=service_name,
                namespace=namespace
            )
            if service.spec.type == "LoadBalancer":
                if service.status.load_balancer.ingress:
                    return service.status.load_balancer.ingress[0].ip
            elif service.spec.type == "NodePort":
                nodes = self.core_v1.list_node()
                if nodes.items:
                    node_ip = nodes.items[0].status.addresses[0].address
                    node_port = service.spec.ports[0].node_port
                    return f"{node_ip}:{node_port}"
            return service.spec.cluster_ip
        except Exception as e:
            print(f"Error getting service endpoint: {e}")
            return None
    
    def show_status(self):
        """Display enriched status of NOAH cluster and key namespaces.

        Sections:
          • Cluster Summary (context, nodes, version)
          • Namespace Deployments (identity, kube-system)
          • Pod Health Totals
        Falls back to 'kubectl' if Python client not initialized.
        """
        if self.apps_v1 is None or self.core_v1 is None:
            # Fallback: attempt kubectl basic summary
            print("⚠️  Warning: No Kubernetes Python client. Attempting kubectl fallback...")
            if not self._kubectl_exists():
                print("❌ Neither Kubernetes client library nor kubectl available; cannot show status.")
                print("💡 Install client: pip install kubernetes OR configure kubectl context.")
                return
            self._kubectl_fallback_summary()
            return

        # --- Cluster summary ---
        try:
            nodes = self.core_v1.list_node().items
            node_count = len(nodes)
            versions = {n.status.node_info.kubelet_version for n in nodes if n.status and n.status.node_info}
            contexts = self._current_kube_context()
            print("Cluster Summary")
            print("  Context:    " + (contexts or "(unknown)"))
            print(f"  Nodes:      {node_count}")
            print(f"  Kubelets:   {', '.join(sorted(versions)) if versions else 'n/a'}")
        except Exception as e:
            print(f"  (Cluster summary unavailable: {e})")

        # --- Namespace deployments ---
        namespaces = ['identity', 'kube-system']
        total_ready = 0
        total_replicas = 0
        for ns in namespaces:
            print(f"\nNamespace: {ns}")
            try:
                deployments = self.apps_v1.list_namespaced_deployment(namespace=ns)
                if not deployments.items:
                    print("  (no deployments)")
                for dep in deployments.items:
                    ready = dep.status.ready_replicas or 0
                    total = dep.spec.replicas or 0
                    total_ready += ready
                    total_replicas += total
                    status = "✓" if ready == total and total > 0 else ("…" if ready > 0 else "✗")
                    print(f"  {status} {dep.metadata.name}: {ready}/{total} ready")
            except Exception as e:
                print(f"  Error reading namespace: {e}")

        # --- Pod health aggregate ---
        if total_replicas > 0:
            pct = (total_ready / total_replicas) * 100 if total_replicas else 0
            print(f"\nDeployment Readiness: {total_ready}/{total_replicas} ({pct:.1f}%)")
        else:
            print("\nDeployment Readiness: (no replicas defined)")

    # ----------------- Helpers -----------------
    def _kubectl_exists(self) -> bool:
        return subprocess.run(['which', 'kubectl'], capture_output=True).returncode == 0

    def _current_kube_context(self) -> Optional[str]:
        try:
            result = subprocess.run(['kubectl', 'config', 'current-context'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            return None
        return None

    def _kubectl_fallback_summary(self):
        # Basic info via kubectl if python client missing
        try:
            ctx = self._current_kube_context() or "(unknown)"
            print("Cluster Summary (kubectl)")
            print(f"  Context:    {ctx}")
            nodes = subprocess.run(['kubectl', 'get', 'nodes', '-o', 'json'], capture_output=True, text=True)
            node_count = 0
            versions = set()
            if nodes.returncode == 0:
                data = json.loads(nodes.stdout)
                for item in data.get('items', []):
                    node_count += 1
                    v = item.get('status', {}).get('nodeInfo', {}).get('kubeletVersion')
                    if v:
                        versions.add(v)
            print(f"  Nodes:      {node_count}")
            print(f"  Kubelets:   {', '.join(sorted(versions)) if versions else 'n/a'}")
            # Namespaces quick list
            for ns in ['identity', 'kube-system']:
                print(f"\nNamespace: {ns}")
                dep_proc = subprocess.run(['kubectl', 'get', 'deploy', '-n', ns, '-o', 'json'], capture_output=True, text=True)
                if dep_proc.returncode != 0:
                    print("  (unavailable)")
                    continue
                ddata = json.loads(dep_proc.stdout)
                items = ddata.get('items', [])
                if not items:
                    print("  (no deployments)")
                    continue
                for dep in items:
                    spec = dep.get('spec', {})
                    replicas = spec.get('replicas', 0) or 0
                    status_d = dep.get('status', {})
                    ready = status_d.get('readyReplicas', 0) or 0
                    status_flag = '✓' if replicas and ready == replicas else ('…' if ready > 0 else '✗')
                    print(f"  {status_flag} {dep['metadata']['name']}: {ready}/{replicas} ready")
        except Exception as e:
            print(f"(kubectl fallback failed: {e})")
