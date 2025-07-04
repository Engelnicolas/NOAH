# Samba4 Active Directory Helm Chart

This Helm chart deploys Samba4 as an Active Directory Domain Controller on a Kubernetes cluster using the Helm package manager.

## Overview

Samba4 provides a comprehensive Active Directory Domain Controller implementation that offers:

- **Active Directory Domain Services (AD DS)** with full LDAP support
- **Kerberos Key Distribution Center (KDC)** for secure authentication
- **DNS Server** with dynamic updates and AD integration
- **Group Policy** management and enforcement
- **File and Print Services** with SMB/CIFS protocol support
- **LDAP Directory Services** for user and computer management
- **Cross-platform compatibility** with Windows, Linux, and macOS clients

## Prerequisites

- Kubernetes 1.19+ cluster
- Helm 3.8+ package manager
- StorageClass for persistent volumes
- Sufficient cluster resources (CPU, memory, storage)
- Network policies support (optional)
- Ingress controller (optional, for LDAP over HTTP)

## Installation

### Basic Installation

```bash
# Add the repository (if using a Helm repository)
helm repo add noah https://your-repo-url

# Install Samba4 with default values
helm install samba4 noah/samba4
```

### Installation with Custom Values

```bash
# Install with custom configuration
helm install samba4 noah/samba4 -f values.yaml
```

### Installation with Inline Parameters

```bash
helm install samba4 noah/samba4 \
  --set samba.realm=EXAMPLE.COM \
  --set samba.workgroup=EXAMPLE \
  --set samba.adminPassword=SecurePassword123 \
  --set persistence.enabled=true \
  --set persistence.size=50Gi
```

## Configuration

### Required Configuration

The following configurations are required for Samba4 Active Directory:

```yaml
# Active Directory Domain Configuration
samba:
  realm: EXAMPLE.COM
  workgroup: EXAMPLE
  netbiosName: DC01
  adminPassword: "SecurePassword123"
  serverRole: active directory domain controller
  dnsForwarder: "8.8.8.8"

# Persistence Configuration
persistence:
  enabled: true
  size: 50Gi
  storageClass: fast-ssd
```

### Complete Domain Controller Configuration

```yaml
# Samba4 AD Configuration
samba:
  realm: COMPANY.LOCAL
  workgroup: COMPANY
  netbiosName: DC01
  adminPassword: "VerySecurePassword123!"
  serverRole: active directory domain controller
  
  # DNS Configuration
  dnsBackend: SAMBA_INTERNAL
  dnsForwarder: "8.8.8.8"
  
  # Security Settings
  minProtocol: SMB2_10
  maxProtocol: SMB3
  
  # TLS Configuration
  tls:
    enabled: true
    cert: |
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
    key: |
      -----BEGIN PRIVATE KEY-----
      ...
      -----END PRIVATE KEY-----

# DNS Service
dns:
  enabled: true
  zones:
    - name: company.local
      type: master

# Users and Groups
samba:
  users:
    - username: john.doe
      password: "UserPassword123"
      firstName: John
      lastName: Doe
      email: john.doe@company.local
      groups:
        - Domain Users
        - Accounting
  
  groups:
    - name: Accounting
      description: Accounting Department
    - name: IT Support
      description: IT Support Team
```

### File Shares Configuration

```yaml
samba:
  shares:
    - name: shared
      path: /srv/samba/shared
      comment: Shared Documents
      readOnly: false
      browseable: true
      validUsers:
        - "@Domain Users"
      createMask: "0664"
      directoryMask: "0775"
    
    - name: public
      path: /srv/samba/public
      comment: Public Files
      readOnly: true
      browseable: true
      guestOk: true
```

### High Availability Configuration

```yaml
replicaCount: 3

# Persistence with multiple volumes
persistence:
  enabled: true
  size: 100Gi
  storageClass: fast-ssd

# Auto-scaling
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70

# Pod Disruption Budget
podDisruptionBudget:
  enabled: true
  minAvailable: 1

# Resources
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Security Configuration

```yaml
# Network Security
networkPolicy:
  enabled: true
  ingress:
    allowedNamespaces:
      - default
      - noah

# Pod Security
podSecurityContext:
  fsGroup: 1000
  runAsNonRoot: false  # Samba requires root for some operations
  runAsUser: 0

securityContext:
  allowPrivilegeEscalation: true
  capabilities:
    add:
      - NET_ADMIN
      - SYS_ADMIN
    drop:
      - ALL
  readOnlyRootFilesystem: false
```

### Backup Configuration

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retentionDays: 30
  
  # S3 Backup Storage
  s3:
    enabled: true
    bucket: company-ad-backups
    region: us-east-1
    endpoint: s3.amazonaws.com
    accessKey: your-access-key
    secretKey: your-secret-key
  
  # Local backup storage
  persistence:
    enabled: true
    size: 50Gi
    storageClass: backup-storage
```

### Monitoring Configuration

```yaml
serviceMonitor:
  enabled: true
  interval: 60s
  scrapeTimeout: 30s
  labels:
    monitoring: prometheus

# Metrics configuration
metrics:
  enabled: true
  port: 9090
```

## Integration Examples

### Keycloak LDAP Integration

Configure Keycloak to use Samba4 as LDAP provider:

```yaml
# In Keycloak Helm values
keycloak:
  extraEnv: |
    - name: KEYCLOAK_LDAP_HOST
      value: "samba4.default.svc.cluster.local"
    - name: KEYCLOAK_LDAP_PORT
      value: "389"
    - name: KEYCLOAK_LDAP_BASE_DN
      value: "dc=company,dc=local"
    - name: KEYCLOAK_LDAP_BIND_DN
      value: "cn=Administrator,cn=Users,dc=company,dc=local"
```

### Application LDAP Authentication

Example LDAP configuration for applications:

```yaml
ldap:
  host: samba4.default.svc.cluster.local
  port: 389
  bindDN: "cn=Administrator,cn=Users,dc=company,dc=local"
  baseDN: "dc=company,dc=local"
  userFilter: "(objectClass=user)"
  groupFilter: "(objectClass=group)"
  userAttr:
    username: sAMAccountName
    email: mail
    firstName: givenName
    lastName: sn
```

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of Samba4 replicas | `1` |
| `image.repository` | Samba4 image repository | `samba4/samba` |
| `image.tag` | Samba4 image tag | `""` (uses appVersion) |
| `samba.realm` | Active Directory realm | `""` |
| `samba.workgroup` | Windows workgroup/domain | `""` |
| `samba.netbiosName` | NetBIOS name | `""` |
| `samba.adminPassword` | Administrator password | `""` |
| `samba.serverRole` | Samba server role | `active directory domain controller` |
| `samba.dnsForwarder` | DNS forwarder address | `8.8.8.8` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Storage size | `20Gi` |
| `dns.enabled` | Enable DNS service | `true` |
| `backup.enabled` | Enable automated backup | `false` |
| `serviceMonitor.enabled` | Enable ServiceMonitor for Prometheus | `false` |
| `networkPolicy.enabled` | Enable NetworkPolicy | `false` |

For a complete list of configurable parameters, see the `values.yaml` file.

## Domain Operations

### Domain Management

```bash
# List domain information
kubectl exec -n default statefulset/samba4 -- samba-tool domain info

# Check domain level
kubectl exec -n default statefulset/samba4 -- samba-tool domain level show

# Raise domain level (if needed)
kubectl exec -n default statefulset/samba4 -- samba-tool domain level raise --domain-level=2008_R2
```

### User Management

```bash
# Create a new user
kubectl exec -n default statefulset/samba4 -- samba-tool user create john.doe 'Password123!' --given-name=John --surname=Doe

# List all users
kubectl exec -n default statefulset/samba4 -- samba-tool user list

# Reset user password
kubectl exec -n default statefulset/samba4 -- samba-tool user setpassword john.doe

# Enable/disable user
kubectl exec -n default statefulset/samba4 -- samba-tool user enable john.doe
kubectl exec -n default statefulset/samba4 -- samba-tool user disable john.doe
```

### Group Management

```bash
# Create a new group
kubectl exec -n default statefulset/samba4 -- samba-tool group add "IT Support"

# List all groups
kubectl exec -n default statefulset/samba4 -- samba-tool group list

# Add user to group
kubectl exec -n default statefulset/samba4 -- samba-tool group addmembers "IT Support" john.doe

# Remove user from group
kubectl exec -n default statefulset/samba4 -- samba-tool group removemembers "IT Support" john.doe
```

### DNS Management

```bash
# List DNS zones
kubectl exec -n default statefulset/samba4 -- samba-tool dns zonelist localhost

# Add DNS record
kubectl exec -n default statefulset/samba4 -- samba-tool dns add localhost company.local server01 A 192.168.1.100

# Query DNS
kubectl exec -n default statefulset/samba4 -- samba-tool dns query localhost company.local server01 A
```

## Backup and Recovery

### Manual Backup

```bash
# Create manual backup
kubectl exec -n default statefulset/samba4 -- samba-tool domain backup offline --targetdir=/backup/manual_$(date +%Y%m%d)
```

### Restore from Backup

```bash
# Stop Samba service
kubectl scale statefulset samba4 --replicas=0

# Restore from backup
kubectl exec -n default job/restore-job -- samba-tool domain backup restore --backup-file=/backup/samba4_backup.tar.bz2 --targetdir=/var/lib/samba

# Start Samba service
kubectl scale statefulset samba4 --replicas=1
```

## Client Configuration

### Windows Client

1. Set DNS server to Samba4 service IP
2. Join domain using Computer Properties > Change Settings
3. Use domain credentials: `COMPANY\Administrator`

### Linux Client

```bash
# Install required packages
sudo apt-get install realmd sssd adcli

# Discover domain
sudo realm discover company.local

# Join domain
sudo realm join company.local -U Administrator

# Configure SSSD
sudo systemctl enable sssd
sudo systemctl start sssd
```

## Upgrading

To upgrade Samba4 to a new version:

```bash
# Update Helm repository
helm repo update

# Upgrade the release
helm upgrade samba4 noah/samba4 -f values.yaml
```

**Important**: Always backup your domain before upgrading!

## Uninstalling

To uninstall/delete the Samba4 deployment:

```bash
helm uninstall samba4
```

**Warning**: This will delete the Active Directory domain! Ensure you have backups.

To also delete persistent volumes:

```bash
kubectl delete pvc -l app.kubernetes.io/name=samba4
```

## Troubleshooting

### Common Issues

1. **Domain Controller Not Starting**
   ```bash
   kubectl describe pod -l app.kubernetes.io/name=samba4
   kubectl logs -l app.kubernetes.io/name=samba4
   ```

2. **DNS Issues**
   ```bash
   kubectl exec statefulset/samba4 -- nslookup company.local localhost
   kubectl exec statefulset/samba4 -- dig @localhost company.local
   ```

3. **LDAP Connection Issues**
   ```bash
   kubectl exec statefulset/samba4 -- ldapsearch -H ldap://localhost -x -b "dc=company,dc=local"
   ```

4. **Kerberos Issues**
   ```bash
   kubectl exec statefulset/samba4 -- kinit Administrator@COMPANY.LOCAL
   kubectl exec statefulset/samba4 -- klist
   ```

### Getting Support

- Check the [Samba Wiki](https://wiki.samba.org/) for configuration guidance
- Review pod logs for error messages
- Verify DNS and time synchronization
- Check resource limits and storage capacity

## Security Considerations

1. **Strong Passwords** - Use complex passwords for all accounts
2. **Network Security** - Enable NetworkPolicies and firewall rules
3. **TLS Encryption** - Enable TLS for LDAP communications
4. **Access Control** - Implement proper group policies and permissions
5. **Regular Backups** - Ensure automated backups are configured
6. **Monitoring** - Enable monitoring and alerting
7. **Updates** - Keep Samba4 updated with security patches
8. **Time Sync** - Ensure proper time synchronization for Kerberos

## Contributing

Please read the contribution guidelines before submitting pull requests or issues.

## License

This chart is licensed under the Apache License 2.0. See LICENSE file for details.
