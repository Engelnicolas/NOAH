# Wazuh Helm Chart

A comprehensive Helm chart for deploying Wazuh SIEM platform on Kubernetes with production-ready configurations.

## Description

This Helm chart deploys a complete Wazuh SIEM platform including:
- **Wazuh Manager**: Central management server for agents and security analysis
- **Wazuh Dashboard**: Web interface for security monitoring and analysis
- **Wazuh Indexer**: Alternative to Elasticsearch for data storage
- **Wazuh Agents**: Optional agents for host monitoring
- **Elasticsearch Integration**: Support for both internal and external Elasticsearch

## Features

- **High Availability**: Multi-replica deployments with clustering support
- **Security**: RBAC, Network Policies, Pod Security Contexts, TLS encryption
- **Monitoring**: Prometheus metrics, Grafana dashboards, health checks
- **Scalability**: Horizontal Pod Autoscaler, resource management
- **Backup**: Automated backup with S3 support
- **LDAP Integration**: Authentication via LDAP/Active Directory
- **OAuth2 Proxy**: Integration with OAuth2 authentication
- **Production Ready**: Comprehensive configuration options

## Prerequisites

- Kubernetes 1.20+
- Helm 3.8+
- Persistent Volume support
- LoadBalancer support (for ingress)
- Certificate Manager (for TLS certificates)

### Optional Dependencies

- Prometheus Operator (for monitoring)
- Grafana (for dashboards)
- LDAP/Samba4 (for authentication)
- OAuth2 Proxy (for SSO)

## Installation

### Add Helm Repository

```bash
helm repo add noah https://noah.local/helm
helm repo update
```

### Basic Installation

```bash
helm install wazuh noah/wazuh
```

### Production Installation

```bash
helm install wazuh noah/wazuh \
  --namespace wazuh \
  --create-namespace \
  --set ingress.dashboard.enabled=true \
  --set ingress.dashboard.hosts[0].host=wazuh.example.com \
  --set ingress.manager.enabled=true \
  --set ingress.manager.hosts[0].host=wazuh-api.example.com \
  --set persistence.manager.enabled=true \
  --set persistence.manager.size=50Gi \
  --set monitoring.enabled=true \
  --set backup.enabled=true
```

### Custom Configuration

```bash
helm install wazuh noah/wazuh -f custom-values.yaml
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `manager.replicaCount` | Number of manager replicas | `2` |
| `dashboard.enabled` | Enable Wazuh Dashboard | `true` |
| `indexer.enabled` | Enable Wazuh Indexer | `false` |
| `elasticsearch.enabled` | Enable internal Elasticsearch | `true` |
| `agent.enabled` | Enable Wazuh Agent DaemonSet | `false` |
| `persistence.manager.enabled` | Enable persistent storage | `true` |
| `persistence.manager.size` | Manager storage size | `20Gi` |
| `ingress.dashboard.enabled` | Enable dashboard ingress | `true` |
| `ingress.manager.enabled` | Enable manager API ingress | `true` |
| `monitoring.enabled` | Enable monitoring | `true` |
| `backup.enabled` | Enable automated backup | `true` |

### Authentication Configuration

```yaml
# LDAP Authentication
manager:
  config:
    auth:
      auth_provider: "ldap"
      ldap_url: "ldap://ldap.example.com:389"
      ldap_base_dn: "dc=example,dc=com"
      ldap_bind_dn: "cn=admin,dc=example,dc=com"

# OAuth2 Proxy Integration
ingress:
  dashboard:
    annotations:
      nginx.ingress.kubernetes.io/auth-url: "https://oauth2-proxy.example.com/oauth2/auth"
      nginx.ingress.kubernetes.io/auth-signin: "https://oauth2-proxy.example.com/oauth2/start"
```

### High Availability Configuration

```yaml
# Manager HA
manager:
  replicaCount: 3
  config:
    cluster:
      enabled: true
      node_type: "master"

# Dashboard HA
dashboard:
  replicaCount: 2

# Pod Disruption Budgets
podDisruptionBudget:
  manager:
    enabled: true
    minAvailable: "50%"
  dashboard:
    enabled: true
    minAvailable: 1

# Autoscaling
autoscaling:
  manager:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
  dashboard:
    enabled: true
    minReplicas: 2
    maxReplicas: 6
```

### Security Configuration

```yaml
# Network Policies
networkPolicy:
  enabled: true

# Pod Security Context
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

# TLS Configuration
secrets:
  tls:
    create: true
    manager:
      cert: ""  # Provide custom certificate
      key: ""   # Provide custom key
```

### Monitoring Configuration

```yaml
# Prometheus Monitoring
serviceMonitor:
  enabled: true
  namespace: monitoring
  interval: 30s

# Grafana Dashboard
monitoring:
  grafana_dashboard:
    enabled: true
    folder: "Security"

# Health Checks
healthCheck:
  enabled: true
  livenessProbe:
    initialDelaySeconds: 60
    periodSeconds: 30
  readinessProbe:
    initialDelaySeconds: 30
    periodSeconds: 10
```

### Backup Configuration

```yaml
# S3 Backup
backup:
  enabled: true
  schedule: "0 2 * * *"
  retention: "30d"
  storage:
    type: "s3"
    s3:
      bucket: "wazuh-backups"
      region: "us-east-1"
      accessKey: "YOUR_ACCESS_KEY"
      secretKey: "YOUR_SECRET_KEY"
```

## Upgrading

### Upgrade to Latest Version

```bash
helm upgrade wazuh noah/wazuh
```

### Upgrade with Custom Values

```bash
helm upgrade wazuh noah/wazuh -f custom-values.yaml
```

## Uninstallation

```bash
helm uninstall wazuh --namespace wazuh
```

**Note**: Persistent volumes are not automatically deleted. Remove them manually if needed.

## Troubleshooting

### Common Issues

1. **Pods not starting**: Check resource limits and node capacity
2. **Ingress not working**: Verify ingress controller and DNS configuration
3. **Authentication failing**: Check LDAP configuration and connectivity
4. **Backup failing**: Verify S3 credentials and permissions

### Debugging Commands

```bash
# Check pod status
kubectl get pods -n wazuh -l app.kubernetes.io/name=wazuh

# View logs
kubectl logs -n wazuh -l app.kubernetes.io/name=wazuh -f

# Describe resources
kubectl describe deployment,statefulset,service -n wazuh

# Check ingress
kubectl get ingress -n wazuh

# Check secrets
kubectl get secrets -n wazuh
```

### Performance Tuning

```yaml
# Resource optimization
manager:
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"

# JVM tuning for Elasticsearch
elasticsearch:
  esJavaOpts: "-Xmx4g -Xms4g"

# Indexer tuning
indexer:
  config:
    indices.fielddata.cache.size: "40%"
    indices.requests.cache.size: "2%"
```

## Security Considerations

1. **Change default passwords** before production deployment
2. **Use TLS certificates** from a trusted CA
3. **Enable network policies** to restrict traffic
4. **Configure RBAC** with least privilege principle
5. **Regular security updates** of container images
6. **Monitor security logs** and alerts

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Wazuh Agent   │    │   Wazuh Agent   │    │   Wazuh Agent   │
│   (DaemonSet)   │    │   (DaemonSet)   │    │   (DaemonSet)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────┐     │     ┌─────────────────┐
         │ Wazuh Manager 1 │◀────┴────▶│ Wazuh Manager 2 │
         │ (StatefulSet)   │           │ (StatefulSet)   │
         └─────────────────┘           └─────────────────┘
                   │                             │
                   └─────────────┬───────────────┘
                                 │
         ┌─────────────────┐     │     ┌─────────────────┐
         │ Wazuh Dashboard │◀────┴────▶│ Wazuh Dashboard │
         │  (Deployment)   │           │  (Deployment)   │
         └─────────────────┘           └─────────────────┘
                   │                             │
                   └─────────────┬───────────────┘
                                 │
              ┌─────────────────────────────────┐
              │        Elasticsearch            │
              │       (StatefulSet)             │
              └─────────────────────────────────┘
```

## Support

- **Documentation**: [Wazuh Official Documentation](https://documentation.wazuh.com/)
- **Community**: [Wazuh Community Forum](https://wazuh.com/community/)
- **Issues**: [GitHub Issues](https://github.com/wazuh/wazuh/issues)
- **Security**: Report security issues to security@wazuh.com

## License

This Helm chart is licensed under the Apache License 2.0. See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

Please read CONTRIBUTING.md for detailed contribution guidelines.
