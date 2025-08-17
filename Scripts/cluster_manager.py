"""Kubernetes cluster management module"""

import subprocess
import json
import time
from typing import Dict, Any, Optional
import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException

class ClusterManager:
    def __init__(self, config_loader):
        self.config = config_loader
        self.k8s_client = None
        self.apps_v1 = None
        self.core_v1 = None
        self._initialize_kubernetes()
    
    def _initialize_kubernetes(self):
        """Initialize Kubernetes clients"""
        try:
            config.load_kubeconfig()
            self.k8s_client = client.ApiClient()
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
        except Exception as e:
            print(f"Warning: Could not initialize Kubernetes client: {e}")
    
    def create_namespace(self, namespace: str) -> bool:
        """Create a Kubernetes namespace"""
        try:
            body = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace)
            )
            self.core_v1.create_namespace(body)
            return True
        except ApiException as e:
            if e.status == 409:  # Already exists
                return True
            print(f"Error creating namespace: {e}")
            return False
    
    def delete_namespace(self, namespace: str) -> bool:
        """Delete a Kubernetes namespace"""
        try:
            self.core_v1.delete_namespace(name=namespace)
            return True
        except ApiException as e:
            print(f"Error deleting namespace: {e}")
            return False
    
    def wait_for_deployment(self, deployment_name: str, namespace: str, timeout: int = 300):
        """Wait for a deployment to be ready"""
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
            except ApiException:
                time.sleep(5)
        return False
    
    def get_service_endpoint(self, service_name: str, namespace: str) -> Optional[str]:
        """Get the endpoint for a service"""
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
        except ApiException as e:
            print(f"Error getting service endpoint: {e}")
            return None
    
    def show_status(self):
        """Display status of all NOAH components"""
        namespaces = ['identity', 'kube-system']
        for ns in namespaces:
            print(f"\nNamespace: {ns}")
            try:
                deployments = self.apps_v1.list_namespaced_deployment(namespace=ns)
                for dep in deployments.items:
                    ready = dep.status.ready_replicas or 0
                    total = dep.spec.replicas or 0
                    status = "✓" if ready == total else "✗"
                    print(f"  {status} {dep.metadata.name}: {ready}/{total} replicas ready")
            except ApiException as e:
                print(f"  Error reading namespace: {e}")
