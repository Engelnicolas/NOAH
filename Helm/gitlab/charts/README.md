# Helm Dependencies

This directory contains the chart dependencies for the GitLab chart.

## Current Dependencies

### PostgreSQL (13.2.24)
- **Purpose**: Database backend for GitLab
- **Repository**: Bitnami Charts (https://charts.bitnami.com/bitnami)
- **Condition**: `postgresql.enabled` (default: true)

### Redis (18.4.0)
- **Purpose**: Cache and session storage for GitLab
- **Repository**: Bitnami Charts (https://charts.bitnami.com/bitnami)
- **Condition**: `redis.enabled` (default: true)

## Managing Dependencies

### Automatic Management
Use the provided script for easy dependency management:
```bash
# Update all chart dependencies
./Script/manage_helm_dependencies.sh

# Update only GitLab chart dependencies
./Script/manage_helm_dependencies.sh -c gitlab
```

### Manual Management
```bash
# From the chart directory
cd Helm/gitlab

# Add Bitnami repository (if not already added)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Update dependencies
helm dependency update

# Verify dependencies
helm dependency list
```

## Dependency Files

- **Chart.yaml**: Defines dependencies with versions and conditions
- **Chart.lock**: Locks specific versions for reproducible builds
- **charts/**: Contains downloaded dependency charts

## Troubleshooting

If you encounter dependency issues:

1. **Clean and rebuild**:
   ```bash
   rm -rf charts/ Chart.lock
   helm dependency update
   ```

2. **Verify repository access**:
   ```bash
   helm repo list
   helm search repo bitnami/postgresql
   helm search repo bitnami/redis
   ```

3. **Check versions**:
   ```bash
   helm dependency list
   ```

Dependencies are automatically downloaded when using `helm dependency update` and will be stored in this directory.
