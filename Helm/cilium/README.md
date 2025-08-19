# Cilium CNI Helm Chart for NOAH

This Helm chart deploys Cilium CNI with SSO integration for the NOAH infrastructure automation platform.

## Overview

Cilium is a powerful Container Network Interface (CNI) that provides networking, security, and observability for Kubernetes clusters. This chart integrates Cilium with Authentik SSO for secure access to Hubble UI and enhanced networking capabilities.

## Features

- **Advanced CNI**: eBPF-based networking with high performance
- **SSO Integration**: Authentik-based authentication for Hubble UI
- **Observability**: Hubble for network monitoring and troubleshooting
- **Security**: Network policies and encryption support
- **Load Balancing**: Advanced load balancing with kube-proxy replacement

## Prerequisites

- Kubernetes 1.20+
- Helm 3.8+
- Age encryption configured (for NOAH secrets)
- Authentik deployed (for SSO features)

## Installation

### Using NOAH CLI (Recommended)

```bash
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com
```

### Using Helm Directly

```bash
# Update dependencies
helm dependency update

# Install Cilium
helm install cilium . \
  --namespace kube-system \
  --create-namespace \
  --values values.yaml
```

## Configuration

### Core Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `cilium.operator.replicas` | Number of operator replicas | `1` |
| `cilium.ipam.mode` | IPAM mode | `kubernetes` |
| `cilium.kubeProxyReplacement` | Kube-proxy replacement mode | `strict` |

### Hubble Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `cilium.hubble.enabled` | Enable Hubble observability | `true` |
| `cilium.hubble.ui.enabled` | Enable Hubble UI | `true` |
| `cilium.hubble.ui.ingress.enabled` | Enable ingress for Hubble UI | `true` |

### SSO Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `sso.enabled` | Enable SSO integration | `true` |
| `sso.provider` | SSO provider | `authentik` |
| `sso.config.issuer` | OIDC issuer URL | `https://auth.noah-infra.com/application/o/cilium/` |
| `sso.config.clientId` | OIDC client ID | `cilium` |

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kubernetes    │    │      Cilium      │    │    Authentik    │
│     Cluster     │◄──►│       CNI        │◄──►│      SSO        │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pod Network   │    │   Hubble UI      │    │   User Auth     │
│   (eBPF-based)  │    │ (Observability)  │    │  (OIDC/SAML)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Accessing Hubble UI

After deployment, Hubble UI will be available at:
- URL: `https://hubble.noah-infra.com`
- Authentication: Via Authentik SSO

## Monitoring

Cilium integrates with Prometheus for metrics collection:

```bash
# View Cilium metrics
kubectl port-forward -n kube-system svc/cilium-agent 9090:9090

# Access metrics at http://localhost:9090/metrics
```

## Troubleshooting

### Check Cilium Status

```bash
# Check overall status
kubectl -n kube-system exec ds/cilium -- cilium status

# Check connectivity
kubectl -n kube-system exec ds/cilium -- cilium connectivity test
```

### View Logs

```bash
# Cilium agent logs
kubectl -n kube-system logs ds/cilium

# Cilium operator logs
kubectl -n kube-system logs deployment/cilium-operator

# Hubble relay logs
kubectl -n kube-system logs deployment/hubble-relay
```

### Common Issues

1. **Pod Network Issues**: Check if Cilium DaemonSet is running on all nodes
2. **SSO Authentication**: Verify Authentik configuration and network connectivity
3. **Hubble UI Access**: Ensure ingress controller is deployed and configured

## Security

- **Encryption**: WireGuard-based encryption for pod-to-pod communication
- **Network Policies**: Kubernetes NetworkPolicy support with eBPF enforcement
- **SSO Integration**: Secure access to management interfaces

## Performance

Cilium provides high-performance networking:
- **eBPF**: Kernel-level packet processing
- **Direct Server Return**: Optimized load balancing
- **Bandwidth Management**: Traffic shaping and QoS

## License

This chart is part of the NOAH infrastructure automation project.

## Support

For support and documentation:
- NOAH Documentation: See main project README
- Cilium Documentation: https://docs.cilium.io/
- Issues: Report via the main NOAH project repository
