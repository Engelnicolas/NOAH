# NOAH Deployment Profiles Comparison

## 🎯 Profile Overview

N.O.A.H supports two main deployment profiles, each optimized for different use cases and environments. This document provides a comprehensive comparison to help you choose the right profile for your needs.

---

## 📊 Side-by-Side Comparison

| Aspect | Minimal Profile | Root Profile |
|--------|------------------|--------------|
| **Target Use Case** | Development, testing, POC | Production, enterprise |
| **CPU Requirements** | 2-4 cores | 8+ cores |
| **RAM Requirements** | 6GB total | 28GB total |
| **Storage Requirements** | 50GB | 500GB+ |
| **Kubernetes Nodes** | 1 (single-node) | 3+ (multi-node) |
| **Security Context** | Permissive | Balanced |
| **Persistence** | Disabled (ephemeral) | Enabled (persistent) |
| **Database** | In-memory/SQLite | PostgreSQL |
| **Cache** | In-memory | Redis |
| **Monitoring** | Basic | Full observability |
| **Backup** | Not required | Automated |
| **Network Policies** | Disabled | Configurable |

---

## 🔧 Technical Specifications

### Resource Allocation

#### Minimal Profile (`values-minimal.yaml`)
```yaml
# Application resources
resources:
  requests:
    cpu: 100m        # 0.1 CPU core
    memory: 256Mi    # 256 MB RAM
  limits:
    cpu: 500m        # 0.5 CPU core
    memory: 1Gi      # 1 GB RAM

# Storage
persistence:
  enabled: false     # No persistent storage
  size: 1Gi         # Container storage only

# Dependencies
postgresql:
  enabled: false     # No external database
redis:
  enabled: false     # No external cache
```

#### Root Profile (`values-root.yaml`)
```yaml
# Application resources
resources:
  requests:
    cpu: 500m        # 0.5 CPU core
    memory: 1Gi      # 1 GB RAM
  limits:
    cpu: 2000m       # 2 CPU cores
    memory: 4Gi      # 4 GB RAM

# Storage
persistence:
  enabled: true      # Persistent storage
  size: 20Gi        # 20 GB per service

# PostgreSQL database
postgresql:
  enabled: true
  resources:
    requests:
      cpu: 250m      # 0.25 CPU core
      memory: 512Mi  # 512 MB RAM
    limits:
      cpu: 1000m     # 1 CPU core
      memory: 2Gi    # 2 GB RAM
  persistence:
    size: 10Gi       # 10 GB database storage

# Redis cache
redis:
  enabled: true
  resources:
    requests:
      cpu: 100m      # 0.1 CPU core
      memory: 256Mi  # 256 MB RAM
    limits:
      cpu: 500m      # 0.5 CPU core
      memory: 1Gi    # 1 GB RAM
  persistence:
    size: 5Gi        # 5 GB cache storage
```

---

## 🔐 Security Configurations

### Minimal Profile Security
```yaml
securityContext:
  runAsUser: 0                    # Root user (development)
  runAsGroup: 0                   # Root group
  fsGroup: 0                      # Root filesystem access
  readOnlyRootFilesystem: false   # Writable filesystem
  allowPrivilegeEscalation: true  # Privilege escalation allowed
  capabilities:
    drop: ["ALL"]                 # Drop all capabilities
```

**Security Implications:**
- ✅ **Pros**: Maximum compatibility, easy debugging
- ⚠️ **Cons**: Higher security risk, not production-ready

### Root Profile Security
```yaml
securityContext:
  runAsUser: 0                     # Root for compatibility
  runAsGroup: 0                    # Root group
  fsGroup: 0                       # Root filesystem access
  readOnlyRootFilesystem: false    # Writable filesystem
  allowPrivilegeEscalation: false  # No privilege escalation
  capabilities:
    add: ["SYS_ADMIN", "NET_ADMIN"] # Required capabilities only
    drop: ["ALL"]                   # Drop all others
```

**Security Implications:**
- ✅ **Pros**: Balanced security, production-compatible
- ⚠️ **Cons**: May require specific capability adjustments

---

## 🚀 Performance Characteristics

### Minimal Profile Performance
- **Startup Time**: 30-60 seconds
- **Resource Usage**: 1-2 CPU cores, 2-4GB RAM
- **Throughput**: 10-50 concurrent users
- **Latency**: 100-500ms response time
- **Scalability**: Single instance only

### Root Profile Performance
- **Startup Time**: 2-5 minutes
- **Resource Usage**: 4-6 CPU cores, 8-12GB RAM
- **Throughput**: 100-1000 concurrent users
- **Latency**: 50-200ms response time
- **Scalability**: Horizontal scaling enabled

---

## 📈 Scaling Capabilities

### Minimal Profile Scaling
```yaml
# No autoscaling (fixed single replica)
replicaCount: 1

# No horizontal scaling
autoscaling:
  enabled: false
```

### Root Profile Scaling
```yaml
# Multiple replicas supported
replicaCount: 2

# Horizontal Pod Autoscaler
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

---

## 🗄️ Data Management

### Minimal Profile Data
- **Database**: In-memory or SQLite
- **Persistence**: None (data lost on restart)
- **Backup**: Not applicable
- **Recovery**: Application restart required

### Root Profile Data
- **Database**: PostgreSQL with persistence
- **Persistence**: Persistent volumes for all services
- **Backup**: Automated daily backups
- **Recovery**: Point-in-time recovery available

---

## 🔍 Monitoring & Observability

### Minimal Profile Monitoring
```yaml
# Basic service monitoring
serviceMonitor:
  enabled: false

# Basic health checks
healthChecks:
  enabled: true
  livenessProbe:
    path: /health
    initialDelaySeconds: 30
  readinessProbe:
    path: /ready
    initialDelaySeconds: 5
```

### Root Profile Monitoring
```yaml
# Full Prometheus monitoring
serviceMonitor:
  enabled: true
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s

# Advanced health checks
healthChecks:
  enabled: true
  livenessProbe:
    path: /health
    initialDelaySeconds: 60
    timeoutSeconds: 5
    periodSeconds: 10
  readinessProbe:
    path: /ready
    initialDelaySeconds: 10
    timeoutSeconds: 3
    periodSeconds: 5
```

---

## 🌐 Network Configuration

### Minimal Profile Network
```yaml
# Internal access only
service:
  type: ClusterIP
  port: 80

# No external access
ingress:
  enabled: false

# No network restrictions
networkPolicy:
  enabled: false
```

### Root Profile Network
```yaml
# Flexible service configuration
service:
  type: ClusterIP
  port: 80
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"

# Ingress ready for external access
ingress:
  enabled: false  # Can be enabled as needed
  className: "nginx"
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"

# Network policies can be enabled
networkPolicy:
  enabled: false  # Can be enabled for security
```

---

## 🎯 Use Case Recommendations

### Choose Minimal Profile When:
- 🧪 **Development Environment**: Local testing and development
- 🏃 **Quick Prototyping**: Rapid proof-of-concept deployment
- 📚 **Learning**: Understanding NOAH architecture
- 💰 **Resource Constraints**: Limited hardware available
- ⚡ **Fast Deployment**: Need immediate results

### Choose Root Profile When:
- 🏢 **Production Environment**: Live systems with users
- 🔄 **High Availability**: Mission-critical applications
- 📊 **Data Persistence**: Important data that must survive restarts
- 👥 **Multi-User**: Multiple concurrent users
- 🔧 **Integration**: Complex system integrations
- 📈 **Scalability**: Growth expected

---

## 🚀 Migration Path

### From Minimal to Root
1. **Backup Configuration**: Export current settings
2. **Provision Resources**: Ensure adequate hardware
3. **Deploy Root Profile**: Use `values-root.yaml`
4. **Data Migration**: Transfer any important data
5. **Validation**: Test all functionality
6. **Monitoring**: Enable observability stack

### Migration Commands
```bash
# Validate current deployment
./Script/noah validate --scope all

# Check requirements for root profile
./Script/noah requirements --profile root

# Backup current configuration
kubectl get configmaps -o yaml > config-backup.yaml

# Deploy root profile
./Script/noah infra deploy --profile root

# Validate new deployment
./Script/noah infra status
```

---

## 📋 Pre-Deployment Checklist

### Minimal Profile Checklist
- [ ] Docker installed and running
- [ ] Kubernetes cluster available (single-node OK)
- [ ] Helm 3.x installed
- [ ] 6GB RAM available
- [ ] 50GB storage available
- [ ] Internet connectivity

### Root Profile Checklist
- [ ] Docker installed and running
- [ ] Kubernetes cluster available (multi-node recommended)
- [ ] Helm 3.x installed
- [ ] 28GB RAM available
- [ ] 500GB storage available
- [ ] Storage classes configured
- [ ] Network policies planned
- [ ] Monitoring stack capacity
- [ ] Backup strategy defined

---

## 🎯 Conclusion

The choice between Minimal and Root profiles depends on your specific needs:

- **Minimal Profile**: Perfect for development, testing, and learning
- **Root Profile**: Essential for production, scaling, and enterprise use

Both profiles are production-ready in their respective contexts, with the Root profile offering enhanced security, persistence, and scalability features necessary for enterprise deployments.

Use the technical requirements validator to ensure your environment meets the necessary specifications:

```bash
# Validate for minimal profile
./Script/noah requirements --profile minimal

# Validate for root profile
./Script/noah requirements --profile root
```

For detailed technical specifications, see [TECHNICAL_REQUIREMENTS.md](TECHNICAL_REQUIREMENTS.md).
