# OAuth2 Proxy Helm Chart

This Helm chart deploys OAuth2 Proxy on a Kubernetes cluster using the Helm package manager.

## Overview

OAuth2 Proxy is a reverse proxy and static file server that provides authentication using Providers (Google, GitHub, Keycloak, and others) to validate accounts by email, domain, or group.

Key features include:
- **Multiple OAuth providers** support (OIDC, Google, GitHub, Keycloak, etc.)
- **Session management** with cookie or Redis-based storage
- **Upstream protection** for multiple applications
- **High availability** with multiple replicas and session sharing
- **Comprehensive logging** and monitoring capabilities
- **Flexible configuration** for various authentication scenarios

## Prerequisites

- Kubernetes 1.19+ cluster
- Helm 3.8+ package manager
- An OAuth2 provider configured (Keycloak, Google, GitHub, etc.)
- Ingress controller (if ingress is enabled)
- Redis (optional, for session storage)

## Installation

### Basic Installation

```bash
# Add the repository (if using a Helm repository)
helm repo add noah https://your-repo-url

# Install OAuth2 Proxy with default values
helm install oauth2-proxy noah/oauth2-proxy
```

### Installation with Custom Values

```bash
# Install with custom configuration
helm install oauth2-proxy noah/oauth2-proxy -f values.yaml
```

### Installation with Inline Parameters

```bash
helm install oauth2-proxy noah/oauth2-proxy \
  --set config.oidcIssuerUrl=https://keycloak.example.com/realms/master \
  --set config.clientId=oauth2-proxy \
  --set config.cookieDomain=.example.com \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=auth.example.com
```

## Configuration

### Required Configuration

The following configurations are required for OAuth2 Proxy to function:

```yaml
# OAuth2 Provider Configuration
config:
  provider: oidc
  oidcIssuerUrl: https://keycloak.example.com/realms/master
  clientId: oauth2-proxy
  cookieDomain: .example.com

# OAuth2 Client Secret
secrets:
  clientSecret: your-oauth2-client-secret
  cookieSecret: your-32-char-cookie-secret

# Ingress Configuration
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: auth.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: oauth2-proxy-tls
      hosts:
        - auth.example.com
```

### Keycloak Integration

For Keycloak integration:

```yaml
config:
  provider: oidc
  oidcIssuerUrl: https://keycloak.example.com/realms/master
  clientId: oauth2-proxy
  scope: "openid email profile"
  emailDomains:
    - "*"
  cookieDomain: .example.com
  
  # Optional: Additional OIDC claims
  oidcExtraAudiences:
    - oauth2-proxy
  
secrets:
  clientSecret: keycloak-client-secret
```

### Redis Session Storage

For high availability with multiple replicas:

```yaml
replicaCount: 3

sessionStorage:
  type: redis
  redis:
    connectionUrl: redis://redis-master:6379
    # Optional: For Redis with auth
    password: redis-password

redis:
  enabled: true
  auth:
    enabled: true
    password: redis-password
```

### Upstream Protection

Configure the applications to protect:

```yaml
config:
  upstreams:
    - http://nextcloud.default.svc.cluster.local:80
    - http://grafana.monitoring.svc.cluster.local:3000
    - http://gitlab.default.svc.cluster.local:80
  
  # Email domain restrictions
  emailDomains:
    - example.com
    - company.org
  
  # Skip authentication for certain paths
  skipAuthRegex:
    - "^/health$"
    - "^/metrics$"
    - "^/api/public/"
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

sessionStorage:
  type: redis
  redis:
    connectionUrl: redis://redis-cluster:6379

resources:
  requests:
    memory: 128Mi
    cpu: 100m
  limits:
    memory: 256Mi
    cpu: 200m
```

### Security Configuration

```yaml
config:
  cookieSecure: true
  cookieHttpOnly: true
  cookieSameSite: lax
  cookieExpire: 168h0m0s  # 1 week
  cookieRefresh: 1h0m0s   # 1 hour
  
  # SSL settings
  sslInsecureSkipVerify: false
  
  # Headers
  setAuthorizationHeader: true
  setXAuthRequestHeaders: true
  passUserHeaders: true

networkPolicy:
  enabled: true

podSecurityContext:
  fsGroup: 65532
  runAsNonRoot: true

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 65532
```

### Monitoring Configuration

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
  labels:
    monitoring: prometheus

config:
  metricsAddress: 0.0.0.0:44180
```

## Application Integration

### Nginx Ingress Integration

To protect applications with OAuth2 Proxy using Nginx Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: protected-app
  annotations:
    nginx.ingress.kubernetes.io/auth-url: "https://auth.example.com/oauth2/auth"
    nginx.ingress.kubernetes.io/auth-signin: "https://auth.example.com/oauth2/start?rd=$escaped_request_uri"
    nginx.ingress.kubernetes.io/auth-response-headers: "X-Auth-Request-User,X-Auth-Request-Email,X-Auth-Request-Access-Token"
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  number: 80
```

### Traefik Integration

For Traefik ingress controller:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: protected-app
  annotations:
    traefik.ingress.kubernetes.io/router.middlewares: default-oauth2-proxy@kubernetescrd
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  number: 80
```

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of OAuth2 Proxy replicas | `1` |
| `image.repository` | OAuth2 Proxy image repository | `quay.io/oauth2-proxy/oauth2-proxy` |
| `image.tag` | OAuth2 Proxy image tag | `""` (uses appVersion) |
| `config.provider` | OAuth2 provider | `oidc` |
| `config.oidcIssuerUrl` | OIDC issuer URL | `""` |
| `config.clientId` | OAuth2 client ID | `""` |
| `config.cookieDomain` | Cookie domain | `""` |
| `secrets.clientSecret` | OAuth2 client secret | `""` |
| `secrets.cookieSecret` | Cookie secret (32 chars) | `""` |
| `sessionStorage.type` | Session storage type | `cookie` |
| `ingress.enabled` | Enable ingress | `false` |
| `serviceMonitor.enabled` | Enable ServiceMonitor for Prometheus | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `networkPolicy.enabled` | Enable NetworkPolicy | `false` |

For a complete list of configurable parameters, see the `values.yaml` file.

## Provider-Specific Configuration

### Google

```yaml
config:
  provider: google
  clientId: your-google-client-id.apps.googleusercontent.com
  scope: "profile email"
  emailDomains:
    - yourdomain.com

secrets:
  clientSecret: your-google-client-secret
```

### GitHub

```yaml
config:
  provider: github
  clientId: your-github-client-id
  scope: "user:email"
  gitHubOrg: your-organization
  gitHubTeam: your-team

secrets:
  clientSecret: your-github-client-secret
```

### Azure AD

```yaml
config:
  provider: azure
  clientId: your-azure-client-id
  azureTenant: your-tenant-id
  scope: "openid email profile"

secrets:
  clientSecret: your-azure-client-secret
```

## Upgrading

To upgrade OAuth2 Proxy to a new version:

```bash
# Update Helm repository
helm repo update

# Upgrade the release
helm upgrade oauth2-proxy noah/oauth2-proxy -f values.yaml
```

## Uninstalling

To uninstall/delete the OAuth2 Proxy deployment:

```bash
helm uninstall oauth2-proxy
```

**Note**: This will not delete persistent volumes. To delete them:

```bash
kubectl delete pvc -l app.kubernetes.io/name=oauth2-proxy
```

## Troubleshooting

### Common Issues

1. **Authentication Loop**
   - Check that `cookieDomain` is correctly set
   - Verify that the OAuth2 client redirect URIs include your auth URL
   - Ensure the ingress annotations are correct

2. **Cookie Issues**
   - Verify `cookieSecret` is exactly 32 characters
   - Check that `cookieSecure` matches your TLS configuration
   - Ensure time synchronization between proxy and browser

3. **Provider Configuration**
   ```bash
   # Test OIDC discovery
   curl https://your-keycloak.com/realms/master/.well-known/openid-configuration
   
   # Check OAuth2 Proxy logs
   kubectl logs -l app.kubernetes.io/name=oauth2-proxy
   ```

4. **Session Storage Issues**
   ```bash
   # Test Redis connectivity
   kubectl exec deployment/oauth2-proxy -- redis-cli -h redis-master ping
   ```

### Getting Support

- Check the [OAuth2 Proxy documentation](https://oauth2-proxy.github.io/oauth2-proxy/)
- Review pod logs for error messages
- Verify OAuth2 provider configuration
- Test with curl commands

## Security Considerations

1. **Use HTTPS everywhere** - OAuth2 requires secure transport
2. **Secure cookie secrets** - Use strong, random 32-character secrets
3. **Limit email domains** - Restrict access to specific domains/groups
4. **Enable network policies** - Restrict network access
5. **Use Redis for sessions** - More secure than cookie storage for production
6. **Regular updates** - Keep OAuth2 Proxy and dependencies updated
7. **Audit logs** - Monitor authentication events

## Contributing

Please read the contribution guidelines before submitting pull requests or issues.

## License

This chart is licensed under the Apache License 2.0. See LICENSE file for details.
