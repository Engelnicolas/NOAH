# Authentik OIDC Integration Guide

This guide covers the complete setup of Authentik as an OIDC provider for Kubernetes cluster authentication.

## Overview

Authentik will serve as a standalone OIDC provider with:
- **Persistent PostgreSQL database** for user data
- **Persistent Redis cache** for session storage
- **Persistent media storage** for configuration and assets
- **OIDC endpoints** for Kubernetes API server integration
- **RBAC integration** for fine-grained access control

## 1. Deploy Authentik with Persistent Storage

```bash
# Deploy Authentik with enhanced OIDC configuration
cd /root/NOAH
python noah.py deploy authentik --namespace identity --domain noah-infra.com
```

### Storage Configuration

The deployment includes three persistent volumes:

1. **PostgreSQL Storage**: 20Gi for user database
2. **Redis Storage**: 4Gi for session cache  
3. **Media Storage**: 5Gi for Authentik configuration files

```yaml
# Persistent volumes automatically created:
- authentik-postgresql-0 (20Gi) - User database
- authentik-redis-master-0 (4Gi) - Session storage
- authentik-media (5Gi) - Application data
```

## 2. Access Authentik Admin Interface

Once deployed, access Authentik at:
- **URL**: `https://auth.noah-infra.com`
- **Username**: `akadmin`
- **Password**: Check the bootstrap password in secrets

```bash
# Get the bootstrap password
kubectl get secret authentik-secrets -n identity -o jsonpath='{.data.bootstrap-password}' | base64 -d
```

## 3. Configure OIDC Provider in Authentik

### 3.1 Create OAuth2/OIDC Provider

1. Navigate to **Applications** → **Providers**
2. Click **Create** → **OAuth2/OpenID Provider**
3. Configure the provider:

```yaml
Name: "Kubernetes Cluster OIDC"
Authorization flow: "default-authentication-flow"
Client type: "Confidential"
Client ID: "kubernetes-cluster"
Client Secret: <generate secure secret>
Redirect URIs:
  - "http://localhost:8080"
  - "https://kubernetes.noah-infra.com/oauth/callback"
Signing Key: <create or select RS256 key>
```

### 3.2 Configure Property Mappings

Add the following scope mappings:

**Groups Mapping**:
```python
# Scope: groups
# Expression:
return {
    "groups": [group.name for group in request.user.ak_groups.all()]
}
```

**Profile Mapping**:
```python
# Scope: profile  
# Expression:
return {
    "preferred_username": request.user.username,
    "name": request.user.name,
    "email": request.user.email,
    "groups": [group.name for group in request.user.ak_groups.all()]
}
```

### 3.3 Create Application

1. Navigate to **Applications** → **Applications**
2. Click **Create**
3. Configure:

```yaml
Name: "Kubernetes Cluster"
Slug: "kubernetes"
Provider: "Kubernetes Cluster OIDC" (created above)
Launch URL: "https://kubernetes.noah-infra.com"
```

## 4. Configure Kubernetes API Server

### 4.1 Generate Configuration

```bash
# Run the OIDC configuration script
python /root/NOAH/Scripts/configure_k8s_oidc.py

# With custom parameters
python /root/NOAH/Scripts/configure_k8s_oidc.py --domain auth.example.com --client-id my-cluster
```

### 4.2 Apply API Server Configuration

For **kubeadm clusters**, edit `/etc/kubernetes/manifests/kube-apiserver.yaml`:

```yaml
spec:
  containers:
  - command:
    - kube-apiserver
    # Add these OIDC flags:
    - --oidc-issuer-url=https://auth.noah-infra.com/application/o/kubernetes/
    - --oidc-client-id=kubernetes-cluster
    - --oidc-username-claim=preferred_username
    - --oidc-groups-claim=groups
    - --oidc-signing-algs=RS256
    # Optional for production:
    - --oidc-username-prefix=oidc:
    - --oidc-groups-prefix=oidc:
```

The API server will automatically restart after saving the file.

### 4.3 Verify OIDC Discovery

```bash
# Test OIDC discovery endpoint
curl -k https://auth.noah-infra.com/application/o/kubernetes/.well-known/openid_configuration

# Should return OIDC configuration including:
{
  "issuer": "https://auth.noah-infra.com/application/o/kubernetes/",
  "authorization_endpoint": "https://auth.noah-infra.com/application/o/authorize/",
  "token_endpoint": "https://auth.noah-infra.com/application/o/token/",
  "userinfo_endpoint": "https://auth.noah-infra.com/application/o/userinfo/",
  "jwks_uri": "https://auth.noah-infra.com/application/o/kubernetes/jwks/",
  "scopes_supported": ["openid", "profile", "email", "groups"],
  "response_types_supported": ["code"],
  "claims_supported": ["sub", "iss", "aud", "exp", "iat", "auth_time", "preferred_username", "email", "groups"]
}
```

## 5. Set Up RBAC Policies

### 5.1 Create Admin Group Binding

```yaml
# Apply admin access for Authentik administrators
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: authentik-admins-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: Group
  name: "oidc:authentik Admins"
  apiGroup: rbac.authorization.k8s.io
```

### 5.2 Create Developer Role

```yaml
# Apply developer access for specific namespaces
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: development
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
subjects:
- kind: Group
  name: "oidc:developers"
  apiGroup: rbac.authorization.k8s.io
```

```bash
# Apply RBAC configurations
kubectl apply -f /tmp/kubernetes-rbac-examples.yaml
```

## 6. Configure kubectl for OIDC

### 6.1 Install kubectl-oidc-login Plugin

```bash
# Install the kubectl OIDC login plugin
curl -LO https://github.com/int128/kubelogin/releases/latest/download/kubelogin_linux_amd64.zip
unzip kubelogin_linux_amd64.zip
sudo mv kubelogin /usr/local/bin/kubectl-oidc_login
chmod +x /usr/local/bin/kubectl-oidc_login
```

### 6.2 Configure kubectl Context

```bash
# Add OIDC user to kubectl config
kubectl config set-credentials oidc-user \
  --exec-api-version=client.authentication.k8s.io/v1beta1 \
  --exec-command=kubectl \
  --exec-arg=oidc-login \
  --exec-arg=get-token \
  --exec-arg=--oidc-issuer-url=https://auth.noah-infra.com/application/o/kubernetes/ \
  --exec-arg=--oidc-client-id=kubernetes-cluster \
  --exec-arg=--oidc-extra-scope=groups

# Create OIDC context
kubectl config set-context noah-oidc \
  --cluster=kubernetes \
  --user=oidc-user

# Switch to OIDC context
kubectl config use-context noah-oidc
```

## 7. Test OIDC Authentication

### 7.1 Test User Login

```bash
# This will open a browser for authentication
kubectl get pods

# First time will prompt for login via browser
# Subsequent requests will use cached token
```

### 7.2 Verify User Identity

```bash
# Check current user
kubectl auth whoami

# Expected output:
# ATTRIBUTE   VALUE
# Username    oidc:username@noah-infra.com
# Groups      [oidc:authentik Admins system:authenticated]
```

### 7.3 Test RBAC

```bash
# Test admin access
kubectl get nodes

# Test namespace access
kubectl get pods -n development
```

## 8. User Management

### 8.1 Create Users in Authentik

1. Navigate to **Directory** → **Users**
2. Click **Create**
3. Configure user details and assign to groups

### 8.2 Create Groups for RBAC

1. Navigate to **Directory** → **Groups**
2. Create groups matching your RBAC policies:
   - `authentik Admins` - Full cluster access
   - `developers` - Development namespace access
   - `viewers` - Read-only access

## 9. Monitoring and Troubleshooting

### 9.1 Check Authentik Logs

```bash
# Check server logs
kubectl logs -n identity deployment/authentik-server -f

# Check worker logs  
kubectl logs -n identity deployment/authentik-worker -f
```

### 9.2 Verify Persistent Storage

```bash
# Check persistent volumes
kubectl get pv | grep authentik

# Check volume claims
kubectl get pvc -n identity

# Check storage usage
kubectl exec -n identity deployment/authentik-server -- df -h
```

### 9.3 Test OIDC Endpoints

```bash
# Test issuer discovery
curl -k https://auth.noah-infra.com/application/o/kubernetes/.well-known/openid_configuration

# Test JWKS endpoint
curl -k https://auth.noah-infra.com/application/o/kubernetes/jwks/
```

## 10. Backup and Recovery

### 10.1 Database Backup

```bash
# Backup PostgreSQL database
kubectl exec -n identity statefulset/authentik-postgresql-0 -- pg_dump -U authentik authentik > authentik-backup.sql

# Restore database
kubectl exec -i -n identity statefulset/authentik-postgresql-0 -- psql -U authentik authentik < authentik-backup.sql
```

### 10.2 Configuration Backup

```bash
# Backup secrets
kubectl get secret authentik-secrets -n identity -o yaml > authentik-secrets-backup.yaml

# Backup configuration
kubectl get configmap authentik-config -n identity -o yaml > authentik-config-backup.yaml
```

## Security Considerations

1. **Use TLS certificates** for all endpoints
2. **Rotate secrets regularly** using the secret management system
3. **Limit token lifetime** in Authentik provider settings
4. **Monitor authentication logs** for suspicious activity
5. **Use least-privilege RBAC** policies
6. **Enable audit logging** in Kubernetes API server

## Troubleshooting Common Issues

### OIDC Discovery Fails
- Check Authentik service is running
- Verify ingress/service configuration
- Test DNS resolution

### Authentication Loop
- Clear browser cache and cookies
- Check redirect URIs configuration
- Verify client ID/secret

### Permission Denied
- Check RBAC bindings
- Verify group membership in Authentik
- Check username/groups claims

For more detailed troubleshooting, see `/root/NOAH/Docs/troubleshooting-guide.md`.
