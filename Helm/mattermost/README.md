# Mattermost Helm Chart

This Helm chart deploys Mattermost on a Kubernetes cluster using the Helm package manager.

## Overview

Mattermost is an open-source, self-hostable online chat service with file sharing, search, and integrations. It serves as an alternative to proprietary SaaS messaging services.

Key features include:
- **Team messaging** with channels, direct messages, and group messaging
- **File sharing** with drag-and-drop uploads and image previews
- **Search functionality** across messages and files
- **Integrations** with external tools and services
- **Mobile applications** for iOS and Android
- **Enterprise features** including LDAP/AD integration, compliance, and advanced security
- **Plugin system** for extending functionality
- **Webhook support** for custom integrations

## Prerequisites

- Kubernetes 1.19+ cluster
- Helm 3.8+ package manager
- StorageClass for persistent volumes (if persistence is enabled)
- PostgreSQL database (can be deployed as dependency)
- Ingress controller (if ingress is enabled)
- Redis (optional, for caching and session storage)

## Installation

### Basic Installation

```bash
# Add the repository (if using a Helm repository)
helm repo add noah https://your-repo-url

# Install Mattermost with default values
helm install mattermost noah/mattermost
```

### Installation with Custom Values

```bash
# Install with custom configuration
helm install mattermost noah/mattermost -f values.yaml
```

### Installation with Inline Parameters

```bash
helm install mattermost noah/mattermost \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=chat.example.com \
  --set postgresql.enabled=true \
  --set persistence.enabled=true
```

## Configuration

### Basic Configuration

```yaml
# Ingress Configuration
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: chat.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: mattermost-tls
      hosts:
        - chat.example.com

# Database Configuration
postgresql:
  enabled: true
  auth:
    database: mattermost
    username: mattermost
    password: mattermost-password

# Persistence
persistence:
  enabled: true
  size: 50Gi
  storageClass: fast-ssd
```

### LDAP/Active Directory Integration

```yaml
mattermost:
  ldap:
    enabled: true
    server: samba4.default.svc.cluster.local
    port: 389
    connectionSecurity: "STARTTLS"
    baseDN: "dc=company,dc=local"
    bindUsername: "cn=Administrator,cn=Users,dc=company,dc=local"
    bindPassword: "admin-password"
    userFilter: "(objectClass=user)"
    groupFilter: "(objectClass=group)"
    userAttribute: sAMAccountName
    firstNameAttribute: givenName
    lastNameAttribute: sn
    emailAttribute: mail
    usernameAttribute: sAMAccountName
    nicknameAttribute: displayName
    idAttribute: objectGUID
    positionAttribute: title
    syncIntervalMinutes: 60
    maxPageSize: 2000
    loginFieldName: "Username"
```

### OAuth2/OIDC Integration

```yaml
mattermost:
  oauth:
    enabled: true

    # GitLab OAuth
    gitlab:
      enabled: true
      id: "mattermost-gitlab-client"
      secret: "gitlab-client-secret"
      authEndpoint: "https://gitlab.example.com/oauth/authorize"
      tokenEndpoint: "https://gitlab.example.com/oauth/token"
      userApiEndpoint: "https://gitlab.example.com/api/v4/user"

    # Generic OpenID Connect (Keycloak)
    openid:
      enabled: true
      buttonText: "Login with Keycloak"
      buttonColor: "#3f51b5"
      discoveryEndpoint: "https://keycloak.example.com/realms/master/.well-known/openid-configuration"
      clientId: "mattermost"
      clientSecret: "keycloak-client-secret"
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

# Redis for session storage and caching
redis:
  enabled: true
  auth:
    enabled: true
    password: redis-password

# External file storage (S3)
mattermost:
  fileStorage:
    driver: amazons3
    amazons3:
      accessKeyId: your-access-key
      secretAccessKey: your-secret-key
      bucket: mattermost-files
      region: us-east-1
      endpoint: s3.amazonaws.com
      ssl: true
```

### Elasticsearch Integration

```yaml
elasticsearch:
  enabled: true

mattermost:
  elasticsearch:
    enabled: true
    host: elasticsearch-master.default.svc.cluster.local
    port: 9200
    username: elastic
    password: elastic-password
    indexPrefix: mattermost
    sniff: false
    enableIndexing: true
    enableSearching: true
    enableAutocomplete: true
```

### Email Configuration

```yaml
mattermost:
  smtp:
    enabled: true
    server: smtp.gmail.com
    port: 587
    username: your-email@gmail.com
    password: your-app-password
    fromAddress: noreply@company.com
    fromName: "Mattermost"
    requireTLS: true
    skipServerCertificateVerification: false
```

### Plugin Configuration

```yaml
mattermost:
  plugins:
    enabled: true
    directory: /mattermost/plugins
    clientDirectory: /mattermost/client/plugins
    install:
      - name: github
        version: "2.0.0"
        url: "https://github.com/mattermost/mattermost-plugin-github/releases/download/v2.0.0/github-2.0.0.tar.gz"
      - name: jira
        version: "3.0.0"
        url: "https://github.com/mattermost/mattermost-plugin-jira/releases/download/v3.0.0/jira-3.0.0.tar.gz"
```

### Security Configuration

```yaml
networkPolicy:
  enabled: true

mattermost:
  security:
    enableTLS: true
    tlsCertFile: /etc/ssl/certs/tls.crt
    tlsKeyFile: /etc/ssl/private/tls.key
    readTimeout: 300
    writeTimeout: 300
    idleTimeout: 60
    maxHeaderSize: 1048576
    useStrictTransportSecurity: true

  # Password requirements
  passwordSettings:
    minimumLength: 8
    lowercase: true
    uppercase: true
    number: true
    symbol: true
```

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of Mattermost replicas | `1` |
| `image.repository` | Mattermost image repository | `mattermost/mattermost-team-edition` |
| `image.tag` | Mattermost image tag | `""` (uses appVersion) |
| `mattermost.siteName` | Site name | `Mattermost` |
| `mattermost.siteUrl` | Site URL | `""` |
| `postgresql.enabled` | Enable PostgreSQL dependency | `true` |
| `redis.enabled` | Enable Redis dependency | `false` |
| `elasticsearch.enabled` | Enable Elasticsearch dependency | `false` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Storage size | `20Gi` |
| `ingress.enabled` | Enable ingress | `false` |
| `serviceMonitor.enabled` | Enable ServiceMonitor for Prometheus | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `networkPolicy.enabled` | Enable NetworkPolicy | `false` |

For a complete list of configurable parameters, see the `values.yaml` file.

## Team and Channel Management

### Creating Teams and Channels

After installation, you can:

1. **Create teams** through the web interface or API
2. **Set up channels** for different purposes (public, private, direct messages)
3. **Configure permissions** for team and channel creation
4. **Integrate with external tools** using webhooks and slash commands

### System Administration

Access the System Console at `/admin_console` to configure:

- User management and authentication
- Team and channel settings
- Integration and plugin management
- Compliance and security policies
- Performance monitoring and analytics

## Integration Examples

### Webhook Integration

```bash
# Incoming webhook example
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello, world!","channel":"town-square","username":"webhookbot"}' \
  https://chat.example.com/hooks/your-webhook-id
```

### Slash Command Integration

```yaml
# Custom slash command configuration
mattermost:
  integrations:
    slashCommands:
      - trigger: weather
        url: https://api.weather.com/webhook
        method: POST
        username: weatherbot
        iconUrl: https://example.com/weather-icon.png
```

## Backup and Recovery

### Database Backup

```bash
# Manual database backup
kubectl exec -n default deployment/mattermost -- pg_dump -h postgresql -U mattermost mattermost > mattermost-backup.sql
```

### File Storage Backup

```bash
# Backup local files (if not using S3)
kubectl exec -n default deployment/mattermost -- tar -czf /tmp/files-backup.tar.gz /mattermost/data
```

### Automated Backup Configuration

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retentionDays: 30

  s3:
    enabled: true
    bucket: mattermost-backups
    region: us-east-1
```

## Monitoring and Observability

### Prometheus Integration

```yaml
serviceMonitor:
  enabled: true
  labels:
    monitoring: prometheus

mattermost:
  metrics:
    enabled: true
    port: 8067
```

### Health Checks

```bash
# Check application health
curl http://chat.example.com/api/v4/system/ping

# Check specific endpoints
curl http://chat.example.com/api/v4/system/status
```

## Upgrading

To upgrade Mattermost to a new version:

```bash
# Update Helm repository
helm repo update

# Upgrade the release
helm upgrade mattermost noah/mattermost -f values.yaml
```

**Important**: Always backup your data before upgrading!

## Uninstalling

To uninstall/delete the Mattermost deployment:

```bash
helm uninstall mattermost
```

**Note**: This will not delete persistent volumes. To delete them:

```bash
kubectl delete pvc -l app.kubernetes.io/name=mattermost
```

## Troubleshooting

### Common Issues

1. **Pod fails to start**
   ```bash
   kubectl describe pod -l app.kubernetes.io/name=mattermost
   kubectl logs -l app.kubernetes.io/name=mattermost
   ```

2. **Database connection issues**
   ```bash
   kubectl exec deployment/mattermost -- pg_isready -h postgresql
   ```

3. **File upload issues**
   - Check storage permissions and available space
   - Verify S3 credentials and bucket access (if using S3)

4. **Authentication problems**
   - Verify LDAP/OAuth configuration
   - Check network connectivity to auth providers
   - Review Mattermost logs for auth errors

### Performance Tuning

1. **Enable Redis caching** for better performance
2. **Configure Elasticsearch** for faster search
3. **Use S3 storage** for file uploads in multi-replica deployments
4. **Adjust resource limits** based on usage patterns

### Getting Support

- Check the [Mattermost documentation](https://docs.mattermost.com/)
- Review application logs for error messages
- Verify database and storage configuration
- Test network connectivity between components

## Security Best Practices

1. **Enable TLS** for all communications
2. **Use strong passwords** and enforce password policies
3. **Configure LDAP/SSO** for centralized authentication
4. **Enable network policies** to restrict access
5. **Regular backups** and disaster recovery planning
6. **Monitor and audit** user activities
7. **Keep software updated** with security patches
8. **Implement rate limiting** and DDoS protection

## Contributing

Please read the contribution guidelines before submitting pull requests or issues.

## License

This chart is licensed under the Apache License 2.0. See LICENSE file for details.
