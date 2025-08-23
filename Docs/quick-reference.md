# NOAH Quick Reference Guide

## 🆕 Latest Enhancements

### Complete Infrastructure Management
```bash
# NEW: Complete infrastructure redeployment (recommended)
ansible-playbook Ansible/cluster-redeploy.yml \
  -e cluster_name=noah-production \
  -e domain_name=noah-infra.com

# Enhanced SSO testing with network validation
python noah.py test sso

# Optimized deployment order: Cilium → Samba4 → Authentik
```

## Essential Commands

### Cluster Management
```bash
# Create fresh cluster (enhanced validation)
python noah.py cluster create --name noah-cluster --domain noah-infra.com

# Destroy cluster completely (with cache cleanup)
python noah.py cluster destroy --force

# Complete infrastructure redeployment (NEW - recommended approach)
ansible-playbook Ansible/cluster-redeploy.yml \
  -e cluster_name=noah-production \
  -e domain_name=noah-infra.com

# Check cluster status
python noah.py status --all
```

### Component Deployment (Optimized Order)
```bash
# 1. Deploy core networking first (SSO-ready configuration)
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com

# 2. Deploy directory services second (LDAP backend)
python noah.py deploy samba4 --namespace identity --domain noah-infra.com

# 3. Deploy authentication third (connects to Samba4)
python noah.py deploy authentik --namespace identity --domain noah-infra.com

# Alternative: Deploy all components (follows optimized order internally)
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

### Testing & Validation (Enhanced)
```bash
# Comprehensive SSO + network validation (NEW - replaces separate tests)
python noah.py test sso

# Component status checking
python noah.py status --all

# Network troubleshooting
kubectl exec -n kube-system ds/cilium -- cilium status --brief
kubectl get networkpolicies -n identity
kubectl get pods -n identity -o wide

# Service connectivity testing
kubectl exec -n identity deployment/authentik-server -- nc -zv samba4.identity.svc.cluster.local 389
```

### Ansible Automation (Enhanced)
```bash
# Complete infrastructure redeployment (preferred method)
ansible-playbook Ansible/cluster-redeploy.yml -e cluster_name=noah-prod -e domain_name=noah-infra.com

# Individual component deployments
ansible-playbook Ansible/deploy-cilium.yml -e domain_name=noah-infra.com    # SSO-ready networking
ansible-playbook Ansible/deploy-samba4.yml -e domain_name=noah-infra.com    # Active Directory
ansible-playbook Ansible/deploy-authentik.yml -e domain_name=noah-infra.com # SSO integration

# Cluster lifecycle management
ansible-playbook Ansible/cluster-create.yml -e cluster_name=noah-test -e domain_name=noah-infra.com
ansible-playbook Ansible/cluster-destroy.yml
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
