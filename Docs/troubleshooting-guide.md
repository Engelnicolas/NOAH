# NOAH Troubleshooting Guide

## Common Issues and Solutions

### 1. Deployment Timeouts

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

4. **Manual cleanup and retry**:
   ```bash
   helm uninstall <component> -n <namespace>
   kubectl delete namespace <namespace> --force --grace-period=0
   python noah.py deploy <component> --namespace <namespace> --domain noah-infra.com
   ```

### 2. Pod Startup Failures

#### Cilium Pod Issues
```bash
# Check Cilium status
kubectl get pods -n kube-system | grep cilium
kubectl describe pod -n kube-system <cilium-pod>

# Common fixes
kubectl delete pod -n kube-system <stuck-cilium-pod>
kubectl exec -n kube-system <working-cilium-pod> -- cilium status
```

#### Authentik Pod Issues
```bash
# Check Authentik components
kubectl get pods -n identity | grep authentik

# Check database connectivity
kubectl logs -n identity deployment/authentik-server
kubectl logs -n identity statefulset/authentik-postgresql

# Common fixes
kubectl delete pod -n identity <stuck-authentik-pod>
```

#### Samba4 Pod Issues
```bash
# Check Samba4 status
kubectl get pods -n identity | grep samba4
kubectl logs -n identity deployment/samba4

# Check persistent volume
kubectl get pvc -n identity
kubectl describe pvc -n identity samba4-data

# Common fixes
kubectl delete pod -n identity <samba4-pod>  # Will recreate
```

### 3. Network Connectivity Issues

#### Inter-Pod Communication
```bash
# Test from one pod to another
kubectl exec -n <namespace> <pod> -- ping <target-ip>
kubectl exec -n <namespace> <pod> -- nslookup <service-name>

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
