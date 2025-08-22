# NOAH Quick Reference Guide

## Essential Commands

### Cluster Management
```bash
# Create fresh cluster
python noah.py cluster create --name noah-cluster --domain noah-infra.com

# Destroy cluster completely
python noah.py cluster destroy --force

# Complete redeploy (cluster + all services) - NEW!
python noah.py cluster redeploy --name noah-production --domain noah-infra.com

# Check cluster status
python noah.py status --all
```

### Component Deployment
```bash
# Deploy core networking (required first)
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com

# Deploy authentication (12-min timeout)
python noah.py deploy authentik --namespace identity --domain noah-infra.com

# Deploy directory services (15-min timeout)
python noah.py deploy samba4 --namespace identity --domain noah-infra.com

# Deploy complete stack (alternative to individual deployments)
python noah.py deploy all --namespace identity --domain noah-infra.com
```

### Secret Management
```bash
# Edit encrypted secrets
python noah.py secrets edit authentik
python noah.py secrets edit samba4

# View secret status
python noah.py secrets list

# Regenerate encryption keys
python noah.py secrets regenerate-keys
```

### Certificate Management
```bash
# Regenerate TLS certificates
python noah.py certificates regenerate --domain noah-infra.com

# View certificate information
python noah.py certificates info

# Check certificate expiration
python noah.py certificates check
```

### Testing and Validation
```bash
# Test SSO functionality
python noah.py test sso --domain noah-infra.com

# Test network connectivity
python noah.py test network

# Test LDAP integration
python noah.py test ldap --domain noah-infra.com
```

## Standard Deployment Order

1. **Prerequisites** → `python noah.py cluster destroy --force` (if needed)
2. **Cluster** → `python noah.py cluster create --name noah-cluster --domain noah-infra.com`
3. **Networking** → `python noah.py deploy cilium --namespace kube-system --domain noah-infra.com`
4. **Authentication** → `python noah.py deploy authentik --namespace identity --domain noah-infra.com`
5. **Directory** → `python noah.py deploy samba4 --namespace identity --domain noah-infra.com` (optional)
6. **Validation** → `python noah.py status --all`

**Alternative 1**: Use `python noah.py deploy all` for steps 3-5 combined
**Alternative 2**: Use `python noah.py cluster redeploy` for steps 1-5 combined

## Component Timeouts

- **Cilium**: 10 minutes (CNI deployment)
- **Authentik**: 12 minutes (DB + App initialization)
- **Samba4**: 15 minutes (AD domain setup)
- **Others**: 10 minutes (default)

## Default Service URLs

- **Authentik SSO**: https://auth.noah-infra.com
- **Hubble UI**: https://hubble.noah-infra.com

## Troubleshooting Quick Fixes

### Pod Issues
```bash
kubectl get pods --all-namespaces | grep -v Running
kubectl logs -n <namespace> <pod-name>
kubectl delete pod -n <namespace> <pod-name>  # Force restart
```

### Helm Issues
```bash
helm list --all-namespaces
helm uninstall <release> -n <namespace>
python noah.py deploy <component> --namespace <namespace> --domain noah-infra.com
```

### Network Issues
```bash
kubectl exec -n kube-system <cilium-pod> -- cilium status
kubectl exec -n kube-system <cilium-pod> -- cilium endpoint list
```

### Storage Issues
```bash
kubectl get pv,pvc --all-namespaces
kubectl describe pvc -n <namespace> <pvc-name>
```

## File Locations

### Configuration
- **Helm Charts**: `Helm/*/`
- **Ansible Playbooks**: `Ansible/`
- **Scripts**: `Scripts/`

### Secrets and Certificates
- **Encrypted Secrets**: `Helm/*/secrets/*.enc.yaml`
- **Age Keys**: `Age/keys.txt`
- **TLS Certificates**: `Certificates/`
- **SOPS Config**: `.sops.yaml`

### Logs and State
- **Helm State**: `helm list --all-namespaces`
- **Kubernetes State**: `kubectl get all --all-namespaces`
- **NOAH State**: `python noah.py status --all`

## Emergency Procedures

### Complete Reset
```bash
python noah.py cluster destroy --force
rm -rf Age/ Certificates/ .sops.yaml  # Optional: remove all local state
python noah.py cluster create --name noah-cluster --domain noah-infra.com
```

### Quick Redeploy (NEW!)
```bash
# One command for complete infrastructure redeploy
python noah.py cluster redeploy --name noah-production --domain noah-infra.com --force

# With configuration export
python noah.py cluster redeploy --name noah-production --domain noah-infra.com --config-file redeploy-config.yaml
```

### Backup Before Changes
```bash
# Backup secrets
cp -r Age/ Age.backup/
cp -r Certificates/ Certificates.backup/
cp .sops.yaml .sops.yaml.backup

# Backup Helm state
helm list --all-namespaces > helm-state.backup
kubectl get all --all-namespaces > k8s-state.backup
```

### Recovery
```bash
# Restore from backup
cp -r Age.backup/ Age/
cp -r Certificates.backup/ Certificates/
cp .sops.yaml.backup .sops.yaml
```
