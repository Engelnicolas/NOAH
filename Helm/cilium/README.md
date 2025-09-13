# NOAH Cilium CNI Configuration

This Helm chart is a **wrapper chart** that deploys the official Cilium CNI with NOAH-specific configuration including Hubble UI and SSO integration.

## Architecture

- **Wrapper Chart**: Uses Cilium official chart as dependency
- **Minimal Templates**: Only essential helper functions  
- **Configuration-Focused**: All functionality via values.yaml

## Domain Configuration

**IMPORTANT**: Before deploying, you MUST customize the domain settings for your environment.

### Required Changes

1. **Update `values.yaml`** and replace all instances of `noah-infra.com` with your actual domain:

   ```yaml
   # Global NOAH configuration - CUSTOMIZE FOR YOUR ENVIRONMENT
   global:
     domain: your-domain.com  # CHANGE THIS to your domain
   ```

2. **Update Hubble UI domain**:
   - Find the `hubble:` section in `values.yaml`
   - Replace `hubble.noah-infra.com` with `hubble.your-domain.com`

3. **Update SSO auth URLs**:
   - Find the `nginx.ingress.kubernetes.io/auth-url` annotation
   - Replace `auth.noah-infra.com` with `auth.your-domain.com`
   - Update the `auth-signin` URL similarly

### Example Customization

For domain `example.com`, you would change:

```yaml
# Before (default):
hosts:
  - hubble.noah-infra.com

# After (customized):
hosts:
  - hubble.example.com
```

```yaml
# Before (default):
nginx.ingress.kubernetes.io/auth-url: "https://auth.noah-infra.com/outpost.goauthentik.io/auth/nginx"

# After (customized):
nginx.ingress.kubernetes.io/auth-url: "https://auth.example.com/outpost.goauthentik.io/auth/nginx"
```

## Deployment

1. Customize domains in `values.yaml`
2. Install dependencies: `helm dependency update`
3. Deploy with: `helm install cilium . --namespace kube-system`

## Features

- ✅ Cilium v1.18.1 (latest stable) via official chart dependency
- ✅ Hubble UI with SSO integration  
- ✅ Network policy enforcement
- ✅ Prometheus monitoring (without ServiceMonitor CRDs)
- ✅ Configurable domain support
- ✅ Clean wrapper chart architecture

## Chart Structure

```
├── Chart.yaml          # Chart metadata with Cilium dependency
├── values.yaml         # NOAH-specific configuration
├── templates/
│   └── _helpers.tpl     # Helper functions only
└── charts/              # Downloaded dependencies (auto-generated)
```

This minimal structure ensures the chart remains maintainable and focused on configuration rather than reimplementing Cilium functionality.