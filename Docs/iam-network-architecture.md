# NOAH IAM Network Architecture

## Overview

This document describes the enhanced Cilium network configuration for NOAH's standalone IAM solution using Authentik.

## Deployment Architecture

### Phase 1: Network Preparation
Before deploying any IAM services, Cilium CNI is deployed with basic networking capabilities:

```
1. Cilium CNI (basic) → 2. Authentik IAM
```

### Benefits of Phased Deployment

1. **Network First**: Ensures proper networking foundation before services
2. **Service Mesh Ready**: Prepares L7 policies and service mesh features
3. **Secure by Default**: Network policies applied from the start
4. **Better Connectivity**: DNS and service discovery working before IAM services start

## Network Policies

### Authentik Network Policy  
- **Ingress**: Allows HTTP/HTTPS from ingress controller
- **Egress**: Allows LDAP to Samba4, database connections, external APIs
- **Security**: Restricted to necessary services only

### PostgreSQL/Redis Network Policies
- **Ingress**: Only from Authentik pods
- **Egress**: DNS only
- **Security**: Database isolation

## Service Configuration

### Samba4 Service Enhancements
```yaml
service:
  type: ClusterIP
  clusterIP: None  # Headless service for better DNS
  annotations:
    service.cilium.io/global: "true"    # Global service mesh
    service.cilium.io/shared: "true"    # Shared across namespaces
```

### Authentik LDAP Configuration
```yaml
ldap:
  serverUri: "ldap://samba4.identity.svc.cluster.local:389"
  connectionTimeout: 30
  poolSize: 5
  retryAttempts: 3
```

## Deployment Sequence

### 1. Network Preparation Phase
```bash
# Deploy basic Cilium CNI
ansible-playbook deploy-cilium.yml -e deployment_phase=preparation
```

Features enabled:
- Basic CNI functionality
- Service mesh preparation
- DNS policy
- Network policy enforcement

### 2. Samba4 Deployment
```bash
# Deploy Samba4 with network ready
ansible-playbook deploy-samba4.yml -e namespace=identity
```

Network features:
- LDAP services (389, 636)
- Kerberos services (88, 464)
- DNS resolution
- Network policy applied

### 3. Authentik Deployment
```bash
# Deploy Authentik with LDAP integration
ansible-playbook deploy-authentik.yml -e ldap_integration=true
```

Network features:
- LDAP connectivity to Samba4
- PostgreSQL/Redis connections
- External API access
- Ingress configuration

### 4. Full SSO Integration
```bash
# Complete Cilium with SSO features
ansible-playbook deploy-cilium.yml -e deployment_phase=sso-integration
```

Features enabled:
- Hubble UI with SSO
- Advanced network policies
- Service mesh monitoring
- SSO authentication

## Validation

### Integrated Network Validation
The SSO tester now includes comprehensive network validation:

```bash
# Run comprehensive SSO tests with integrated network validation
python noah.py test sso

# Or use the SSO tester directly with network validation
python -c "
from Scripts.sso_tester import SSOTester
from Scripts.config_loader import ConfigLoader
tester = SSOTester(ConfigLoader())
tester.run_comprehensive_test()
"
```

### Network-Only Validation
```bash
# Run only network validation
python -c "
from Scripts.sso_tester import SSONetworkValidator
validator = SSONetworkValidator()
validator.validate_network()
"
```

**Validation Features:**
- ✅ **Prerequisites Check**: kubectl, helm availability
- ✅ **Cluster Connectivity**: Kubernetes API access
- ✅ **Namespace Validation**: Required namespaces exist
- ✅ **Service Deployments**: Cilium, Samba4, Authentik readiness
- ✅ **Network Policies**: Security policy enforcement
- ✅ **DNS Resolution**: Service discovery validation
- ✅ **LDAP Connectivity**: Authentik → Samba4 connection
- ✅ **API Endpoints**: Service API accessibility
- ✅ **SSO Integration**: Complete authentication flow testing

### Manual Testing
```bash
# Test LDAP connectivity
kubectl exec -n identity deployment/samba4 -- ldapsearch -x -H ldap://localhost:389 -s base

# Test Authentik API
kubectl exec -n identity deployment/authentik-server -- wget -q -O- http://localhost:9000/api/v3/

# Test network policies
kubectl exec -n identity deployment/authentik-server -- nc -zv samba4.identity.svc.cluster.local 389
```

## Monitoring

### Hubble UI Access
- URL: `https://hubble.noah-infra.com`
- Authentication: Authentik SSO
- Features: Network flow visualization, policy enforcement monitoring

### Network Flow Monitoring
```bash
# Monitor network traffic
kubectl exec -n kube-system ds/cilium -- hubble observe

# Monitor specific services
kubectl exec -n kube-system ds/cilium -- hubble observe --from-pod identity/samba4 --to-pod identity/authentik-server
```

## Troubleshooting

### Common Issues

1. **LDAP Connectivity Issues**
   ```bash
   # Check network policy
   kubectl describe networkpolicy samba4-network-policy -n identity
   
   # Test connectivity
   kubectl exec -n identity deployment/authentik-server -- nc -zv samba4.identity.svc.cluster.local 389
   ```

2. **DNS Resolution Issues**
   ```bash
   # Check DNS
   kubectl run test-dns --image=busybox --rm -i --restart=Never -- nslookup samba4.identity.svc.cluster.local
   ```

3. **Network Policy Blocking Traffic**
   ```bash
   # Check policy enforcement
   kubectl exec -n kube-system ds/cilium -- cilium endpoint list
   kubectl exec -n kube-system ds/cilium -- cilium policy get
   ```

### Debug Commands
```bash
# Cilium status
kubectl exec -n kube-system ds/cilium -- cilium status

# Network connectivity test
kubectl exec -n kube-system ds/cilium -- cilium connectivity test

# Service mesh status
kubectl exec -n kube-system ds/cilium -- cilium service list

# Policy trace
kubectl exec -n kube-system ds/cilium -- cilium policy trace
```

## Security Features

### Network Segmentation
- Identity namespace isolation
- Service-to-service encryption
- L7 policy enforcement
- Zero-trust networking

### SSO Integration Security
- Ingress authentication
- Service mesh authorization
- Network policy enforcement
- TLS encryption

### Monitoring and Alerting
- Hubble flow monitoring
- Policy violation alerts
- Service mesh metrics
- Security event logging

## Files Created/Modified

### New Files
- `Helm/cilium/templates/network-policies.yaml` - Network policies for SSO services

### Modified Files
- `Scripts/sso_tester.py` - **Enhanced with integrated network validation**
- `Helm/cilium/values.yaml` - Replaced with SSO-optimized Cilium configuration
- `Ansible/deploy-cilium.yml` - Replaced with phased SSO-ready deployment playbook
- `Ansible/cluster-redeploy.yml` - Updated deployment sequence
- `Helm/samba4/values.yaml` - Enhanced service configuration
- `Helm/authentik/values.yaml` - Improved LDAP integration settings

### Removed Files
- `Scripts/validate_sso_network.sh` - **Functionality integrated into sso_tester.py**

## Next Steps

1. Test the new deployment sequence
2. Validate SSO integration
3. Monitor network performance
4. Configure additional network policies as needed
5. Set up monitoring and alerting
