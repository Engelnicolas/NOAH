# Helm Charts Documentation

This section contains documentation for all Helm charts included in the N.O.A.H project.

## Available Charts

### Core Infrastructure
- **[GitLab](../Helm/gitlab/README.md)** - Git repository and CI/CD platform
- **[Keycloak](../Helm/keycloak/README.md)** - Identity and access management
- **[Samba4](../Helm/samba4/README.md)** - Active Directory domain controller

### Collaboration Platforms
- **[Nextcloud](../Helm/nextcloud/README.md)** - File sharing and collaboration
- **[Mattermost](../Helm/mattermost/README.md)** - Team communication

### Security & Monitoring
- **[Wazuh](../Helm/wazuh/README.md)** - Security information and event management
- **[OpenEDR](../Helm/openedr/README.md)** - Endpoint detection and response
- **[OAuth2 Proxy](../Helm/oauth2-proxy/README.md)** - Authentication proxy

### Observability
- **[Prometheus](../Helm/prometheus/README.md)** - Metrics collection and alerting
- **[Grafana](../Helm/grafana/README.md)** - Metrics visualization and dashboards

## Chart Development Guidelines

### Structure
All charts follow the standard Helm chart structure:
```
chart-name/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default configuration values
├── templates/          # Kubernetes manifests
├── charts/             # Dependencies (auto-generated)
└── README.md           # Chart documentation
```

### Best Practices
- Use semantic versioning for chart versions
- Include comprehensive values.yaml documentation
- Implement proper resource limits and requests
- Use ConfigMaps and Secrets appropriately
- Follow Kubernetes security best practices

### Testing
- Validate with `helm lint`
- Test installation with `helm template`
- Include integration tests where applicable

For detailed information about each chart, click on the links above or browse the individual chart directories.
