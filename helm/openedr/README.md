# OpenEDR helm Chart

This helm chart deploys OpenEDR (Open Endpoint Detection and Response) on a Kubernetes cluster using the helm package manager.

## Overview

OpenEDR is a comprehensive endpoint detection and response platform that provides:

- **Real-time threat detection** and response capabilities
- **Advanced behavioral analysis** and machine learning-based detection
- **Incident response** automation and forensic capabilities
- **Compliance reporting** for multiple frameworks (PCI-DSS, SOX, HIPAA, etc.)
- **Centralized management** for endpoint security across your infrastructure
- **Integration capabilities** with external threat intelligence feeds

## Prerequisites

- Kubernetes 1.19+ cluster
- helm 3.8+ package manager
- StorageClass for persistent volumes (if persistence is enabled)
- Ingress controller (if ingress is enabled)
- cert-manager (if TLS certificates are managed automatically)

## Installation

### Basic Installation

```bash
# Add the repository (if using a helm repository)
helm repo add noah https://your-repo-url

# Install OpenEDR with default values
helm install openedr noah/openedr
```

### Installation with Custom Values

```bash
# Install with custom configuration
helm install openedr noah/openedr -f values.yaml
```

### Installation with Inline Parameters

```bash
helm install openedr noah/openedr \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=openedr.example.com \
  --set persistence.enabled=true \
  --set persistence.size=50Gi
```

## Configuration

### Required Configuration

The following configurations are typically required for a production deployment:

```yaml
# Admin credentials
admin:
  username: admin
  password: "your-secure-password"

# Database configuration
postgresql:
  enabled: true
  auth:
    database: openedr
    username: openedr
    password: "your-db-password"

# Ingress configuration
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: openedr.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: openedr-tls
      hosts:
        - openedr.example.com

# Persistence
persistence:
  enabled: true
  size: 50Gi
  storageClass: fast-ssd
```

### LDAP/Active Directory Integration

```yaml
ldap:
  enabled: true
  host: ldap.example.com
  port: 389
  baseDN: "dc=example,dc=com"
  userDN: "ou=users,dc=example,dc=com"
  groupDN: "ou=groups,dc=example,dc=com"
  bindDN: "cn=admin,dc=example,dc=com"
  bindPassword: "your-ldap-password"
  tlsEnabled: true
  userFilter: "(objectClass=person)"
  groupFilter: "(objectClass=group)"
```

### High Availability Configuration

```yaml
replicaCount: 3

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

podDisruptionBudget:
  enabled: true
  minAvailable: 1

persistence:
  enabled: true
  size: 100Gi
  storageClass: fast-ssd

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### External Database Configuration

To use an external PostgreSQL database:

```yaml
postgresql:
  enabled: false

externalDatabase:
  host: postgres.example.com
  port: 5432
  database: openedr
  username: openedr
  password: "your-external-db-password"
```

### Monitoring Configuration

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
  labels:
    monitoring: prometheus

metrics:
  enabled: true
  port: 9090
```

### Backup Configuration

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retentionDays: 30
  s3:
    enabled: true
    bucket: openedr-backups
    region: us-east-1
    endpoint: s3.amazonaws.com
```

### Security Configuration

```yaml
networkPolicy:
  enabled: true

podSecurityContext:
  fsGroup: 1000
  runAsNonRoot: true
  runAsUser: 1000

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
```

## Advanced Configuration

### Threat Intelligence Integration

```yaml
threatIntelligence:
  enabled: true
  feeds:
    - name: alienvault
      url: https://reputation.alienvault.com/reputation.data
      format: alienvault
      updateInterval: 1h
    - name: custom-feed
      url: https://your-feed.example.com/indicators
      format: json
      updateInterval: 30m
```

### Custom Detection Rules

```yaml
detectionRules:
  enabled: true
  rules:
    - name: suspicious-powershell
      type: behavioral
      description: "Detect suspicious PowerShell activity"
      conditions:
        - process: powershell.exe
          args: "*-EncodedCommand*"
      severity: high
      action: alert
```

### Agent Configuration

```yaml
agent:
  enabled: true
  config:
    scanInterval: 300  # 5 minutes
    networkMonitoring: true
    fileIntegrityMonitoring: true
    registryMonitoring: true
    processMonitoring: true
  deployment:
    type: DaemonSet  # Deploy on all nodes
    nodeSelector:
      kubernetes.io/os: linux
```

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of OpenEDR replicas | `1` |
| `image.repository` | OpenEDR image repository | `openedr/openedr` |
| `image.tag` | OpenEDR image tag | `"latest"` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `admin.username` | Admin username | `admin` |
| `admin.password` | Admin password | `""` (auto-generated) |
| `postgresql.enabled` | Enable PostgreSQL dependency | `true` |
| `redis.enabled` | Enable Redis dependency | `true` |
| `elasticsearch.enabled` | Enable Elasticsearch dependency | `false` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Storage size | `20Gi` |
| `ingress.enabled` | Enable ingress | `false` |
| `serviceMonitor.enabled` | Enable ServiceMonitor for Prometheus | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `networkPolicy.enabled` | Enable NetworkPolicy | `false` |
| `backup.enabled` | Enable automated backup | `false` |

For a complete list of configurable parameters, see the `values.yaml` file.

## Upgrading

To upgrade OpenEDR to a new version:

```bash
# Update helm repository
helm repo update

# Upgrade the release
helm upgrade openedr noah/openedr -f values.yaml
```

## Uninstalling

To uninstall/delete the OpenEDR deployment:

```bash
helm uninstall openedr
```

**Note**: This will not delete persistent volumes. To delete them:

```bash
kubectl delete pvc -l app.kubernetes.io/name=openedr
```

## Troubleshooting

### Common Issues

1. **Pod fails to start**
   ```bash
   kubectl describe pod -l app.kubernetes.io/name=openedr
   kubectl logs -l app.kubernetes.io/name=openedr
   ```

2. **Database connection issues**
   ```bash
   kubectl exec deployment/openedr -- pg_isready -h postgresql
   ```

3. **Storage issues**
   ```bash
   kubectl get pvc
   kubectl describe pvc openedr
   ```

4. **Ingress not working**
   ```bash
   kubectl get ingress
   kubectl describe ingress openedr
   ```

### Getting Support

- Check the [OpenEDR documentation](https://docs.openedr.com)
- Review pod logs for error messages
- Verify resource quotas and limits
- Check network policies and security contexts

## Security Considerations

1. **Change default passwords** immediately after deployment
2. **Enable TLS** for all communications
3. **Configure RBAC** with minimal required permissions
4. **Enable NetworkPolicies** to restrict network access
5. **Use external secrets management** for sensitive data
6. **Regularly update** the OpenEDR image and dependencies
7. **Monitor and audit** system access and activities

## Contributing

Please read the contribution guidelines before submitting pull requests or issues.

## License

This chart is licensed under the Apache License 2.0. See LICENSE file for details.
