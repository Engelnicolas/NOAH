# Headlamp Kubernetes Dashboard Integration

This document summarizes the Headlamp integration into the NOAH infrastructure stack with Authentik SSO authentication.

## Overview

Headlamp is a Kubernetes web UI that has been integrated into NOAH with full Authentik SSO support. Users authenticate via Authentik OIDC and can manage the Kubernetes cluster through a modern web interface.

## What Was Added

### 1. Helm Chart (`Helm/headlamp/`)

A complete Helm chart for deploying Headlamp with Authentik OIDC integration:

- **Chart.yaml**: Chart metadata and version information
- **values.yaml**: Configuration including OIDC settings, ingress, resources
- **templates/**:
  - `deployment.yaml`: Headlamp deployment with OIDC environment variables
  - `service.yaml`: ClusterIP service
  - `serviceaccount.yaml`: Service account for Headlamp
  - `clusterrolebinding.yaml`: Optional cluster role binding (disabled by default for security)
  - `ingress.yaml`: Nginx ingress with TLS support
  - `secret.yaml`: OIDC credentials secret
  - `pvc.yaml`: Optional persistent volume for plugins
  - `_helpers.tpl`: Helm template helpers

**Key Features**:
- OIDC client credentials managed via Kubernetes secrets
- Nginx ingress with TLS termination
- Security contexts (non-root, read-only filesystem)
- Resource limits configured
- Plugin support (optional)

### 2. Ansible Playbook (`Ansible/deploy-headlamp.yml`)

Automated deployment playbook that:

1. Exports canonical Headlamp secrets (OIDC client ID and secret)
2. Creates TLS secrets for ingress
3. Generates Helm values file with domain-specific configuration
4. Deploys Headlamp via Helm chart
5. Validates deployment status

**Variables**:
- `headlamp_namespace`: Kubernetes namespace (default: `kube-system`)
- `domain_name`: Domain for services
- `headlamp_helm_timeout`: Helm deployment timeout

### 3. Cluster Deployment Integration (`Ansible/cluster-deploy.yml`)

**PHASE 4** added to the deployment pipeline:

- Deployment order: **Cilium → Authentik → Headlamp → Validation**
- Headlamp deployment after Authentik (requires SSO to be ready)
- Pod readiness checks with retries
- TLS secret validation
- Integrated into phase duration tracking
- Added to critical component validation

### 4. Security Manager Updates (`Scripts/security/security_manager.py`)

Headlamp secret generation (unchanged) plus new **Hubble UI** service (v0.0.7):

```python
elif service_name == 'headlamp':
    required = {
        'oidc_client_id': lambda: 'headlamp',  # Fixed client ID
        'oidc_client_secret': lambda: self.generate_secure_password(40, include_special=False),
    }
elif service_name == 'hubble-ui':
    required = {
        'proxy_client_id': lambda: 'hubble-ui',
        'proxy_client_secret': lambda: self.generate_secure_password(40, include_special=False),
        'cookie_secret': lambda: self.generate_secure_password(32, include_special=False),
    }
```

Secrets are stored in the canonical encrypted secrets store with versioning and rotation support.

### 5. CLI Commands (`noah.py`)

**Bootstrap full stack (GitOps — recommended)**:
```bash
python3 noah.py cluster bootstrap --node <IP> --domain your-domain.com --flux-repo <url> ...
```
FluxCD reconciles: Cilium → Authentik → Headlamp

**Redeploy Headlamp standalone**:
```bash
python noah.py deploy headlamp --namespace kube-system --domain your-domain.com
```

**Test command**:
```bash
python noah.py test headlamp --domain your-domain.com
```

### 6. Testing (`Tests/test_headlamp_sso.py`)

Comprehensive test suite that validates:

- Headlamp deployment exists and is ready
- Pods are running
- Service is configured correctly
- Ingress is set up with proper host and TLS
- OIDC secrets are present and complete

Can be run standalone:
```bash
python Tests/test_headlamp_sso.py --domain your-domain.com
```

Or via NOAH CLI:
```bash
python noah.py test headlamp
```

### 7. GitHub Workflows

**Updated `.github/workflows/test.yml`**:
- Added Headlamp CLI command tests
- Tests `deploy headlamp` and `test headlamp` commands

**Updated `.github/workflows/deploy.yml`**:
- Updated deployment workflow to use `cluster bootstrap`
- Added Headlamp test to deployment validation

### 8. Documentation

**Updated `docs/README.md`**:
- Added Headlamp to stack features list
- Updated deployment order documentation
- Added Headlamp access information with SSO note
- Updated architecture principles

**Updated `docs/troubleshooting-guide.md`**:
- Added Headlamp-specific troubleshooting section
- Included SSO debugging steps
- Added Headlamp to DNS and logging sections

## Access and Usage

### Accessing Headlamp

After deployment, access Headlamp at:
```
https://headlamp.your-domain.com
```

### Authentication

Headlamp uses Authentik for SSO authentication:

1. Navigate to `https://headlamp.your-domain.com`
2. You'll be redirected to Authentik for login
3. Use your Authentik credentials (retrieve with `python noah.py password show-password`)
4. After authentication, you'll be redirected back to Headlamp with full cluster access

### Authentik Configuration — Automatic

The Headlamp OIDC provider and application are **automatically provisioned** in Authentik at the end of `deploy-headlamp.yml` via `AuthentikProvisioner`:

```bash
python Scripts/security/authentik_provisioner.py provision-headlamp --domain your-domain.com
```

The provisioner creates (idempotently):
- **OAuth2/OIDC provider** `Headlamp Provider` with `client_id=headlamp`
- **Redirect URI**: `https://headlamp.your-domain.com/oidc-callback`
- **Scopes**: `openid profile email offline_access`
- **Application** `Headlamp` (slug `headlamp`)

If automatic provisioning fails (e.g. Authentik not yet reachable), the deployment continues and you can re-run the provisioner manually once Authentik is up.

## Testing

### Test Deployment
```bash
# Test Headlamp deployment
python noah.py test headlamp --domain your-domain.com

# Test full stack including Headlamp (after cluster bootstrap)
python noah.py flux status
python noah.py test sso
python noah.py test headlamp
```

### Manual Verification
```bash
# Check Headlamp pods
kubectl get pods -n kube-system -l app.kubernetes.io/name=headlamp

# Check Headlamp service
kubectl get svc -n kube-system -l app.kubernetes.io/name=headlamp

# Check Headlamp ingress
kubectl get ingress -n kube-system -l app.kubernetes.io/name=headlamp

# View Headlamp logs
kubectl logs -n kube-system deployment/headlamp --tail=50

# Check OIDC configuration
kubectl get secret -n kube-system headlamp-oidc -o yaml
```

## Troubleshooting

### Headlamp Not Accessible

1. **Check deployment**:
   ```bash
   kubectl get deployment -n kube-system headlamp
   kubectl describe deployment -n kube-system headlamp
   ```

2. **Check pods**:
   ```bash
   kubectl get pods -n kube-system -l app.kubernetes.io/name=headlamp
   kubectl logs -n kube-system deployment/headlamp
   ```

3. **Check ingress**:
   ```bash
   kubectl get ingress -n kube-system
   kubectl describe ingress -n kube-system headlamp
   ```

### SSO Not Working

1. **Verify OIDC secrets**:
   ```bash
   kubectl get secret -n kube-system headlamp-oidc
   ```

2. **Check environment variables**:
   ```bash
   kubectl exec -n kube-system deployment/headlamp -- env | grep OIDC
   ```

3. **Verify Authentik provider**:
   - Log into Authentik admin interface
   - Check that the Headlamp provider exists
   - Verify redirect URIs match `https://headlamp.your-domain.com/oidc-callback`
   - Ensure client ID is `headlamp`
   - Verify issuer URL is correct

4. **Test Authentik OIDC endpoint**:
   ```bash
   curl https://auth.your-domain.com/application/o/headlamp/.well-known/openid-configuration
   ```

### "Forbidden" Errors

This is expected behavior. Headlamp uses OIDC for authentication, not service account tokens. Users must authenticate via Authentik SSO to access the cluster.

## Architecture

### Deployment Flow

```
python3 noah.py cluster bootstrap
   ↓
FluxCD reconciles GitOps repository
   ↓
1. Cilium CNI (network foundation)
   ↓
2. Authentik SSO (identity provider)
   ↓
3. Headlamp Dashboard (OIDC config pointing to Authentik)
   ↓
4. Validation (all components checked)
```

### Authentication Flow

```
User → Headlamp UI → Redirect to Authentik → User Login →
Authentik Issues Token → Redirect to Headlamp → Headlamp Validates Token →
Access Granted
```

### Network Architecture

```
Internet
  ↓
Nginx Ingress (TLS termination)
  ↓
Headlamp Service (ClusterIP)
  ↓
Headlamp Pod (OIDC enabled)
  ↓
Kubernetes API (authenticated via OIDC token)
```

## Configuration

### Helm Values

Key configuration options in `values.yaml`:

```yaml
config:
  oidc:
    clientID: "headlamp"
    clientSecret: "<from-canonical-secrets>"
    issuerURL: "https://auth.your-domain.com/application/o/headlamp/"
    scopes: "openid profile email groups"
    callbackURL: "https://headlamp.your-domain.com/oidc-callback"

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: "headlamp.your-domain.com"
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: headlamp-tls
      hosts:
        - "headlamp.your-domain.com"
```

### Environment Variables

Headlamp deployment receives:

- `OIDC_CLIENT_ID`: From Kubernetes secret
- `OIDC_CLIENT_SECRET`: From Kubernetes secret
- `OIDC_ISSUER_URL`: From Kubernetes secret
- `OIDC_SCOPES`: From values.yaml
- `OIDC_CALLBACK_URL`: Constructed from domain

## Security Considerations

1. **No Cluster Admin by Default**: The `clusterRoleBinding.create` is set to `false` for better security. Users authenticate via OIDC with their own permissions.

2. **Read-Only Filesystem**: Headlamp runs with `readOnlyRootFilesystem: true` for security.

3. **Non-Root User**: Runs as user 100 with fsGroup 101.

4. **Secret Management**: OIDC credentials stored in Kubernetes secrets, generated from canonical encrypted store.

5. **TLS Enabled**: All traffic encrypted via Nginx ingress with TLS termination.

## Future Enhancements

1. **Plugin Management**: Add support for Headlamp plugins via the deployment
2. **Multi-Tenancy**: Support for multiple Headlamp instances with different RBAC configurations
3. **Monitoring Integration**: Prometheus metrics and Grafana dashboards for Headlamp usage

## References

- Headlamp Documentation: https://headlamp.dev
- Headlamp GitHub: https://github.com/kubernetes-sigs/headlamp
- Authentik OIDC: https://docs.goauthentik.io/docs/providers/oauth2/
- NOAH Documentation: docs/README.md
