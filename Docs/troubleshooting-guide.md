# NOAH Troubleshooting Guide

## 🆕 Recent Enhancements

### Enhanced Diagnostic Tools
- **Integrated SSO Testing**: `python noah.py test sso` now includes network validation
- **Optimized Deployment Order**: Ensures proper service dependencies
- **Enhanced kubectl Cache Management**: Automatic cleanup prevents connection issues
- **Comprehensive Status Checking**: Improved validation in all phases

## Common Issues and Solutions

### 1. Deployment Order Issues (NEW)

#### Symptom
```
Authentik cannot connect to Samba4 LDAP
Network policies blocking service communication
```

#### Solutions
1. **Use the correct deployment order** (Cilium → Samba4 → Authentik):
   ```bash
   # Recommended: Use complete redeployment
   ansible-playbook Ansible/cluster-redeploy.yml \
     -e cluster_name=noah-cluster \
     -e domain_name=noah-infra.com
   ```

2. **Verify network foundation is ready**:
   ```bash
   # Check Cilium is fully operational before proceeding
   kubectl exec -n kube-system ds/cilium -- cilium status --brief
   kubectl get networkpolicies -n identity
   ```

3. **Test service connectivity**:
   ```bash
   # Test Authentik → Samba4 connection
   kubectl exec -n identity deployment/authentik-server -- \
     nc -zv samba4.identity.svc.cluster.local 389
   ```

### 2. Network Policy Issues (ENHANCED)

#### Symptom
```
Services cannot communicate despite being deployed
Authentik LDAP connection failures
```

#### Solutions
1. **Validate SSO network policies**:
   ```bash
   kubectl get networkpolicies -n identity
   kubectl describe networkpolicy -n identity authentik-to-samba4-ldap
   ```

2. **Check Cilium policy enforcement**:
   ```bash
   kubectl exec -n kube-system ds/cilium -- cilium policy get
   kubectl exec -n kube-system ds/cilium -- cilium endpoint list
   ```

3. **Use enhanced SSO testing**:
   ```bash
   # Comprehensive network + SSO validation
   python noah.py test sso
   ```

### 3. Deployment Timeouts

#### Symptom
```
Failed to deploy cilium: Error: UPGRADE FAILED: context deadline exceeded
```

#### Solutions
1. **Check timeout settings** (already optimized):
   - Cilium: 10 minutes
   - Authentik: 12 minutes  
   - Samba4: 15 minutes

2. **Verify cluster resources**:
   ```bash
   kubectl top nodes
   kubectl top pods --all-namespaces
   ```

3. **Check for stuck resources**:
   ```bash
   kubectl get pods --all-namespaces | grep -E "(Pending|ImagePullBackOff|CrashLoopBackOff)"
   ```

4. **Use complete redeployment** (often resolves complex issues):
   ```bash
   ansible-playbook Ansible/cluster-redeploy.yml \
     -e cluster_name=noah-cluster \
     -e domain_name=noah-infra.com
   ```

### 4. Pod Startup Failures (ENHANCED)

#### Cilium Pod Issues
```bash
# Check Cilium status (enhanced diagnostics)
kubectl get pods -n kube-system | grep cilium
kubectl describe pod -n kube-system <cilium-pod>

# Enhanced Cilium diagnostics
kubectl exec -n kube-system ds/cilium -- cilium status --brief
kubectl exec -n kube-system ds/cilium -- cilium connectivity test --help

# Common fixes
kubectl delete pod -n kube-system <stuck-cilium-pod>
```

#### Samba4 Pod Issues (NEW)
```bash
# Check Samba4 deployment
kubectl get pods -n identity | grep samba4
kubectl logs -n identity deployment/samba4 --tail=50

# Test LDAP service
kubectl exec -n identity deployment/samba4 -- \
  ldapsearch -x -H ldap://localhost:389 -s base

# Check persistent volume
kubectl get pvc -n identity | grep samba4
```

#### Authentik Pod Issues (ENHANCED)
```bash
# Check Authentik components
kubectl get pods -n identity | grep authentik

# Check database connectivity and LDAP integration
kubectl logs -n identity deployment/authentik-server --tail=50
kubectl logs -n identity deployment/authentik-worker --tail=50
kubectl logs -n identity statefulset/authentik-postgresql

# Test LDAP connectivity to Samba4
kubectl exec -n identity deployment/authentik-server -- \
  nc -zv samba4.identity.svc.cluster.local 389

# Common fixes
kubectl delete pod -n identity <stuck-authentik-pod>
```

### 5. kubectl Connection Issues (ENHANCED)

#### Symptom
```
The connection to the server localhost:6443 was refused
kubectl cache-related errors after cluster operations
```

#### Solutions (Automatic cleanup now included)
```bash
# NOAH now includes automatic kubectl cache cleanup
python noah.py cluster destroy --force  # Includes cache cleanup

# Manual cache cleanup (if needed)
kubectl config unset clusters.default
kubectl config unset users.default
kubectl config unset contexts.default
rm -rf ~/.kube/cache/
rm -rf ~/.kube/http-cache/

# Verify disconnection (expected after destroy)
kubectl get nodes  # Should show connection error - this is normal
```

#### Enhanced kubeconfig Management
```bash
# Check persistent kubeconfig setup
echo $KUBECONFIG
cat ~/.bashrc | grep KUBECONFIG

# Verify cluster connectivity
kubectl cluster-info
kubectl get nodes
```

### 6. SSO and LDAP Integration Issues (NEW)

#### Symptom
```
Authentik cannot authenticate users
LDAP connection errors
SSO login failures
```

#### Enhanced Diagnostic Commands
```bash
# Comprehensive SSO + network testing (NEW)
python noah.py test sso

# Individual component testing
kubectl exec -n identity deployment/samba4 -- \
  ldapsearch -x -H ldap://localhost:389 -s base

kubectl exec -n identity deployment/authentik-server -- \
  nc -zv samba4.identity.svc.cluster.local 389

# Check Authentik API
kubectl exec -n identity deployment/authentik-server -- \
  wget -q -O- http://localhost:9000/api/v3/core/tenants/
```

#### Network Policy Validation
```bash
# Check SSO-specific network policies
kubectl get networkpolicies -n identity
kubectl describe networkpolicy -n identity authentik-to-samba4-ldap

# Verify Cilium policy enforcement
kubectl exec -n kube-system ds/cilium -- cilium policy get
```

### 7. Validation and Status Checking (ENHANCED)

#### Comprehensive Status Check
```bash
# Enhanced overall status (includes SSO validation)
python noah.py status --all

# Component-specific status
kubectl get pods -n identity -o wide
kubectl get svc -n identity
kubectl get ingress -n identity
```

#### Network Troubleshooting
```bash
# Cilium network status
kubectl exec -n kube-system ds/cilium -- cilium status --brief
kubectl exec -n kube-system ds/cilium -- cilium connectivity test

# Service discovery testing
kubectl exec -n identity deployment/authentik-server -- nslookup samba4.identity.svc.cluster.local
```

# Check Cilium connectivity
kubectl exec -n kube-system <cilium-pod> -- cilium endpoint list
kubectl exec -n kube-system <cilium-pod> -- cilium status --verbose
```

#### Ingress Issues
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller

# Check ingress resources
kubectl get ingress --all-namespaces
kubectl describe ingress -n <namespace> <ingress-name>

# Test ingress connectivity
curl -k https://<service-url>
```

### 4. Secret Management Issues

#### SOPS Decryption Failures
```bash
# Check Age key
cat Age/keys.txt
echo $SOPS_AGE_KEY_FILE

# Test SOPS functionality
sops --decrypt Helm/authentik/secrets/authentik-secrets.enc.yaml

# Regenerate if corrupted
python noah.py secrets regenerate-keys
```

#### Secret Not Found Errors
```bash
# Check secret existence
kubectl get secrets --all-namespaces | grep <secret-name>

# Recreate secret
python noah.py secrets edit <component>
python noah.py deploy <component> --namespace <namespace> --domain noah-infra.com
```

### 5. Database Issues

#### PostgreSQL Connection Problems
```bash
# Check PostgreSQL status
kubectl get pods -n identity | grep postgresql
kubectl logs -n identity statefulset/authentik-postgresql

# Check database connectivity from Authentik
kubectl exec -n identity deployment/authentik-server -- pg_isready -h authentik-postgresql

# Reset database (WARNING: Data loss)
kubectl delete statefulset -n identity authentik-postgresql
kubectl delete pvc -n identity data-authentik-postgresql-0
python noah.py deploy authentik --namespace identity --domain noah-infra.com
```

#### Redis Connection Problems
```bash
# Check Redis status
kubectl get pods -n identity | grep redis
kubectl logs -n identity statefulset/authentik-redis-master

# Test Redis connectivity
kubectl exec -n identity statefulset/authentik-redis-master -- redis-cli ping
```

### 6. Certificate Issues

#### TLS Certificate Problems
```bash
# Check certificate validity
openssl x509 -in Certificates/*.noah-infra.com.crt -text -noout

# Check certificate in cluster
kubectl get secrets --all-namespaces | grep tls
kubectl describe secret -n <namespace> <tls-secret>

# Regenerate certificates
python noah.py certificates regenerate --domain noah-infra.com
```

#### Certificate Authority Issues
```bash
# Verify CA certificate
openssl x509 -in Certificates/ca.crt -text -noout

# Check CA in configmap
kubectl get configmap --all-namespaces | grep ca
kubectl describe configmap -n <namespace> <ca-configmap>
```

### 7. Storage Issues

#### Persistent Volume Problems
```bash
# Check PV/PVC status
kubectl get pv,pvc --all-namespaces
kubectl describe pvc -n <namespace> <pvc-name>

# Check storage class
kubectl get storageclass
kubectl describe storageclass <storage-class>

# Fix stuck PVC
kubectl patch pvc -n <namespace> <pvc-name> -p '{"metadata":{"finalizers":null}}'
```

#### Disk Space Issues
```bash
# Check node disk usage
kubectl exec -n kube-system <cilium-pod> -- df -h
kubectl top nodes

# Clean up unused images
kubectl exec -n kube-system <cilium-pod> -- crictl images
kubectl exec -n kube-system <cilium-pod> -- crictl rmi --prune
```

### 8. Authentication Issues

#### Authentik Login Problems
```bash
# Check Authentik server logs
kubectl logs -n identity deployment/authentik-server -f

# Check worker logs
kubectl logs -n identity deployment/authentik-worker -f

# Reset admin password
kubectl exec -n identity deployment/authentik-server -- ak create_admin_group
```

#### LDAP Integration Issues
```bash
# Check LDAP outpost
kubectl get pods -n identity | grep ldap
kubectl logs -n identity deployment/authentik-ldap-outpost

# Test LDAP connectivity
kubectl exec -n identity deployment/authentik-ldap-outpost -- ldapsearch -x -h localhost -p 389
```

### 9. Monitoring Issues

#### Prometheus Not Scraping
```bash
# Check Prometheus status
kubectl get pods -n monitoring | grep prometheus
kubectl logs -n monitoring statefulset/prometheus-stack-prometheus

# Check service monitors
kubectl get servicemonitor --all-namespaces
```

#### Grafana Dashboard Issues
```bash
# Check Grafana pods
kubectl get pods -n monitoring | grep grafana
kubectl logs -n monitoring deployment/prometheus-stack-grafana

# Reset Grafana admin password
kubectl get secret -n monitoring prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```

## Emergency Recovery Procedures

### Complete Infrastructure Recovery
```bash
# 1. Save current state
kubectl get all --all-namespaces > emergency-backup.yaml
helm list --all-namespaces > helm-backup.yaml

# 2. Perform complete reset
python noah.py cluster destroy --force

# 3. Recreate from scratch
python noah.py cluster create --name noah-cluster --domain noah-infra.com
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com
python noah.py deploy authentik --namespace identity --domain noah-infra.com
python noah.py deploy samba4 --namespace identity --domain noah-infra.com
python noah.py deploy all --namespace identity --domain noah-infra.com  # Or deploy complete stack
```

### Partial Component Recovery
```bash
# 1. Backup component state
helm get values -n <namespace> <component> > <component>-values-backup.yaml

# 2. Uninstall component
helm uninstall <component> -n <namespace>

# 3. Clean namespace (if needed)
kubectl delete namespace <namespace> --force --grace-period=0

# 4. Redeploy component
python noah.py deploy <component> --namespace <namespace> --domain noah-infra.com
```

## Monitoring and Health Checks

### Automated Health Check Script
```bash
#!/bin/bash
# health-check.sh

echo "=== NOAH Health Check ==="

# Check cluster connectivity
if ! kubectl cluster-info >/dev/null 2>&1; then
    echo "❌ Cluster not accessible"
    exit 1
fi

# Check critical pods
critical_pods=$(kubectl get pods --all-namespaces --field-selector=status.phase!=Running -o name | wc -l)
if [ "$critical_pods" -gt 0 ]; then
    echo "⚠️  $critical_pods pods not running"
    kubectl get pods --all-namespaces --field-selector=status.phase!=Running
fi

# Check Helm releases
failed_releases=$(helm list --all-namespaces --failed -o json | jq '. | length')
if [ "$failed_releases" -gt 0 ]; then
    echo "❌ $failed_releases failed Helm releases"
    helm list --all-namespaces --failed
fi

# Check certificates
cert_files="Certificates/*.noah-infra.com.crt"
for cert in $cert_files; do
    if [ -f "$cert" ]; then
        expiry=$(openssl x509 -in "$cert" -noout -enddate | cut -d= -f2)
        echo "📜 Certificate expires: $expiry"
    fi
done

echo "✅ Health check completed"
```

## Performance Optimization

### Resource Limits
```bash
# Check resource usage
kubectl top pods --all-namespaces --sort-by=cpu
kubectl top pods --all-namespaces --sort-by=memory

# Adjust resource limits in values.yaml files
vim Helm/authentik/values.yaml
vim Helm/cilium/values.yaml
```

### Network Performance
```bash
# Check Cilium metrics
kubectl exec -n kube-system <cilium-pod> -- cilium metrics list
```

## Useful Debugging Commands

```bash
# Get everything in a namespace
kubectl get all -n <namespace>

# Describe all resources in a namespace
kubectl describe all -n <namespace>

# Get events sorted by time
kubectl get events --sort-by=.metadata.creationTimestamp

# Check resource quotas
kubectl describe quota --all-namespaces

# Check node conditions
kubectl describe nodes

# Get logs from all containers in a pod
kubectl logs -n <namespace> <pod> --all-containers=true

# Follow logs in real time
kubectl logs -n <namespace> <pod> -f

# Execute commands in running pod
kubectl exec -it -n <namespace> <pod> -- /bin/bash
```
