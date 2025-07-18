# N.O.A.H User Guide - Complete Deployment Guide

## 🎯 Overview

N.O.A.H provides a production-ready, secure, and scalable open-source infrastructure stack with identity management, collaboration tools, monitoring, and security components.

---

## 🚀 Quick Start (5 Minutes)

### Fastest Path to Running N.O.A.H

```bash
# Clone repository
git clone https://github.com/your-org/noah.git
cd noah

# Validate and fix any issues
./Script/noah validate --fix

# Deploy infrastructure with root security (recommended for compatibility)
./Script/noah infra deploy --security root --verbose

# Monitor deployment progress
./Script/noah-logs tail

# Verify deployment
./Script/noah infra status

# Access your services at:
# - Keycloak: kubectl port-forward svc/keycloak 8080:8080
# - Nextcloud: kubectl port-forward svc/nextcloud 8081:80
# - Mattermost: kubectl port-forward svc/mattermost 8082:8065
# - Grafana: kubectl port-forward svc/grafana 3000:3000
```

---

## 📋 Prerequisites

### System Requirements

**Development Environment (values-minimal.yaml):**
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, or similar)
- **CPU**: 2-4 cores
- **RAM**: 6GB (4GB system + 2GB applications)
- **Storage**: 50GB available space
- **Network**: 10 Mbps internet connection

**Production Environment (values-root.yaml):**
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, or similar)
- **CPU**: 8+ cores (16+ recommended)
- **RAM**: 28GB (16GB system + 12GB applications)
- **Storage**: 500GB+ SSD storage
- **Network**: 100 Mbps dedicated connection

> 📋 **Note**: For detailed technical specifications, see [TECHNICAL_REQUIREMENTS.md](TECHNICAL_REQUIREMENTS.md)

### Kubernetes Cluster Requirements

**Development Cluster:**
```yaml
# Single-node cluster acceptable
nodes:
  master: 1
  worker: 0 (can run on master)
resources:
  cpu: 2-4 cores total
  memory: 6-8GB total
  storage: 50-100GB
```

**Production Cluster:**
```yaml
# Multi-node cluster recommended
nodes:
  master: 3 (HA setup)
  worker: 2+ (minimum)
resources:
  cpu: 8-16 cores per node
  memory: 16-32GB per node
  storage: 200-500GB per node
```

### Required Software

**Core Tools:**
```bash
# Check if tools are installed
./Script/noah validate --scope dependencies

# Required tools (auto-validated by noah-validate):
- Docker >= 20.10
- Kubernetes (kubectl) >= 1.24
- Helm >= 3.10
- Python >= 3.8
- Git >= 2.30
- Make >= 4.2
```

**Optional Tools (Enhanced Features):**
```bash
# Infrastructure as Code
- Terraform >= 1.3 (for infrastructure provisioning)
- Ansible >= 2.12 (for configuration management)

# Monitoring and Observability
- Prometheus >= 2.40 (metrics collection)
- Grafana >= 9.0 (visualization)

# CI/CD Integration
- GitLab Runner >= 15.0
- Jenkins >= 2.400
```

### Storage Requirements

**Development Profile:**
```yaml
# Ephemeral storage (no persistence)
persistence:
  enabled: false
  size: 1Gi

# Total storage needed: ~10-20GB (containers + logs)
```

**Production Profile:**
```yaml
# Persistent storage required
persistence:
  enabled: true
  size: 20Gi        # Per main service

# Database storage
postgresql:
  persistence:
    size: 10Gi      # Database data

# Cache storage
redis:
  persistence:
    size: 5Gi       # Cache data

# Total storage needed: ~200-500GB (data + backups + logs)
```

For further information, check out https://github.com/Engelnicolas/NOAH/wiki
