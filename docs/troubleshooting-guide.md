# 🔧 NOAH Troubleshooting Guide

Quick solutions for NOAH infrastructure issues.

## � **Emergency Quick Fixes**

### **Everything Broken? Start Here:**
```bash
# Nuclear option - complete reset
python noah.py cluster destroy --force
python noah.py cluster create --name noah --domain your-domain.com
python noah.py deploy core --domain your-domain.com
```

### **Quick Health Check:**
```bash
# Check overall status
python noah.py status

# Test authentication
python noah.py test sso

# Basic cluster check
kubectl get nodes && kubectl get pods -A
```

## 🚀 **Deployment Issues**

### **Deployment Fails**
```bash
# 1. Check requirements (4+ CPU, 8GB+ RAM, 50GB+ storage)
free -h && df -h && nproc

# 2. Test internet connectivity
curl -I https://github.com

# 3. Clean and retry
python noah.py cluster destroy --force
rm -rf ~/.kube/ ~/.helm/
python noah.py cluster create --name noah --domain your-domain.com
python noah.py deploy core --domain your-domain.com
```

### **Services Not Starting**
```bash
# Check specific service
kubectl get pods -l app=authentik
kubectl logs deployment/authentik-server

# Restart service
kubectl delete pod -l app=authentik
```

### **Can't Access Web Interface**
```bash
# 1. Check external IP
kubectl get svc -A | grep LoadBalancer

# 2. Test DNS (should point to external IP)
nslookup auth.your-domain.com
nslookup headlamp.your-domain.com

# 3. Add to /etc/hosts if needed
echo "EXTERNAL_IP auth.your-domain.com" >> /etc/hosts
echo "EXTERNAL_IP headlamp.your-domain.com" >> /etc/hosts
```

## 📊 **Headlamp Dashboard Issues**

### **Can't Access Headlamp**
```bash
# Check Headlamp deployment
kubectl get pods -n kube-system -l app.kubernetes.io/name=headlamp

# Check Headlamp service
kubectl get svc -n kube-system -l app.kubernetes.io/name=headlamp

# Check Headlamp ingress
kubectl get ingress -n kube-system -l app.kubernetes.io/name=headlamp

# View Headlamp logs
kubectl logs deployment/headlamp -n kube-system --tail=50

# Test Headlamp deployment
python noah.py test headlamp
```

### **Headlamp SSO Not Working**
```bash
# Verify OIDC secret exists
kubectl get secret headlamp-oidc -n kube-system -o yaml
kubectl get secret headlamp-secret -n kube-system -o yaml

# Check Authentik provider configuration
# Log into Authentik and verify the Headlamp OAuth2/OIDC provider exists
# Issuer URL should be: https://auth.your-domain.com/application/o/headlamp/
# Callback URL should be: https://headlamp.your-domain.com/oidc-callback

# Restart Headlamp pods
kubectl delete pod -n kube-system -l app.kubernetes.io/name=headlamp
```

### **Headlamp Shows "Forbidden" Errors**
```bash
# Headlamp uses OIDC for authentication, not service account tokens
# This is expected - users should authenticate via Authentik SSO

# Check if OIDC is properly configured
kubectl exec -n kube-system deployment/headlamp -- env | grep OIDC

# Verify Authentik is accessible from Headlamp
kubectl exec -n kube-system deployment/headlamp -- wget -O- https://auth.your-domain.com/.well-known/openid-configuration
```

## 🔐 **Authentication Problems**

### **Can't Login to Authentik**
```bash
# Get credentials
python noah.py password show

# Reset (rotate) if needed – updates canonical secrets store
python noah.py password new
python noah.py deploy authentik --regenerate-password
```

### **Database Issues**
```bash
# Quick fix - restart database
kubectl delete pod -l app.kubernetes.io/name=postgresql

# Check logs
kubectl logs deployment/authentik-postgresql
```

## 🌐 **Network Problems**

### **Pods Can't Communicate**
```bash
# Check Cilium status
kubectl get pods -n kube-system -l k8s-app=cilium

# Restart Cilium if needed
kubectl delete pod -n kube-system -l k8s-app=cilium

# Test connectivity
kubectl exec -it <any-pod> -- ping google.com
```

### **Service Discovery Broken**
```bash
# Test DNS
kubectl exec -it <any-pod> -- nslookup kubernetes.default.svc.cluster.local

# Check CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
```

## 🛠️ **Quick Fixes by Symptom**

### **"Connection Refused" Errors**
```bash
# Restart the service
kubectl delete pod -l app=<service-name>
```

### **"Permission Denied" Errors**
```bash
# Fix kubectl permissions
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### **"DNS Resolution Failed"**
```bash
# Add to /etc/hosts
echo "EXTERNAL_IP auth.your-domain.com" >> /etc/hosts
echo "EXTERNAL_IP headlamp.your-domain.com" >> /etc/hosts
echo "EXTERNAL_IP hubble.your-domain.com" >> /etc/hosts
```

### **"Service Unavailable"**
```bash
# Check if pods are running
kubectl get pods -A

# Check resource usage
kubectl top nodes
```

### **"Certificate Errors"**
```bash
# Check certificate validity
openssl x509 -in Certificates/ca.crt -text -noout

# Redeploy with fresh certificates
python noah.py deploy core --regenerate-certs
```

## 📊 **Monitoring & Logs**

### **Essential Commands**
```bash
# System overview
python noah.py status
kubectl get nodes
kubectl get pods -A

# Resource usage
kubectl top nodes
kubectl top pods -A

# Recent events
kubectl get events --sort-by=.metadata.creationTimestamp
```

### **Important Logs**
```bash
# Authentik
kubectl logs deployment/authentik-server --tail=20

# Headlamp
kubectl logs deployment/headlamp -n kube-system --tail=20

# Cilium
kubectl logs daemonset/cilium -n kube-system --tail=20

# Database
kubectl logs deployment/authentik-postgresql --tail=20
```

## 🆘 **Emergency Recovery**

### **Cluster Unresponsive**
```bash
# Check cluster service
sudo systemctl status k3s

# Restart if needed
sudo systemctl restart k3s
sleep 30
kubectl get nodes
```

### **Complete Reset (Last Resort)**
```bash
# 1. Backup important data
python noah.py password show > backup-passwords.txt
kubectl get secrets -A -o yaml > backup-secrets.yaml

# 2. Destroy everything
python noah.py cluster destroy --force
rm -rf ~/.kube/ ~/.helm/

# 3. Fresh install
python noah.py cluster create --name noah --domain your-domain.com
python noah.py deploy core --domain your-domain.com

# 4. Restore passwords if needed
# Use backup-passwords.txt to recreate accounts (rotation creates new versioned entry in canonical store)
```

## 💡 **Common Gotchas**

1. **Wrong Domain**: Ensure DNS points to LoadBalancer IP
2. **Resource Limits**: Need minimum 8GB RAM, 4 CPU cores
3. **Firewall**: Ensure ports 80, 443, 6443 are open
4. **Time Sync**: Check system time is synchronized
5. **Disk Space**: Ensure 50GB+ available storage

## 🔍 **Need More Help?**

- Check system requirements in [README.md](README.md)
- See detailed deployment in [deployment-guide.md](deployment-guide.md)
- View command reference in [quick-reference.md](quick-reference.md)

---

**💡 Tip**: Most issues are solved by the "nuclear option" reset above. When in doubt, destroy and redeploy!
   
   # Verify key format
   head -1 Age/keys.txt
   ```

2. **Canonical secrets operations:**
   ```bash
   # Show canonical store (with metadata & integrity)
   python noah.py secrets canonical --show

   # Rotate Authentik admin password
   python noah.py password new

   # Force rotation during deploy
   python noah.py deploy authentik --regenerate-password
   ```

3. **Reinitialize encryption keys (rare):**
   ```bash
   # Regenerate Age key (will require manual re-encryption of canonical file if encrypted)
   age-keygen > Age/keys.txt
   python noah.py config init
   ```

### **Issue: Certificate Errors**

**Symptoms:**
- SSL certificate warnings
- TLS handshake failures
- Certificate expired errors

**Solutions:**

1. **Check certificate status:**
   ```bash
   # View certificate details
   openssl x509 -in Certificates/ca.crt -text -noout
   
   # Check expiration
   openssl x509 -in Certificates/ca.crt -noout -dates
   ```

2. **Regenerate certificates:**
   ```bash
   # Remove old certificates
   rm -rf Certificates/
   
   # Redeploy (will create new certs)
   python noah.py deploy core --domain your-domain.com
   ```

## 🧪 **Testing & Validation Issues**

### **Issue: Tests Fail**

**Symptoms:**
- `python noah.py test sso` fails
- Workflow tests report errors
- Health checks timeout

**Solutions:**

1. **Run detailed diagnostics:**
   ```bash
   # Verbose status check
   python noah.py status --verbose
   
   # Individual component tests
   kubectl get pods --all-namespaces
   kubectl get svc --all-namespaces
   kubectl get ingress --all-namespaces
   ```

2. **Check individual services:**
   ```bash
   # Test each service directly
   curl -k https://auth.your-domain.com/if/admin/
   curl -k https://hubble.your-domain.com/
   
   # Internal service tests
   kubectl exec -it <pod> -- curl http://service:port/health
   ```

### Pod Startup Failures 

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