# NOAH Scripts Directory

This directory contains all Python modules for the NOAH (Network Operations & Automation Hub) infrastructure.

## 📁 Module Organization

### **Core Business Logic**
- `cluster_manager.py` - Kubernetes cluster lifecycle management
- `security_manager.py` - Security, encryption, and secret management  
- `helm_deployer.py` - Helm chart deployment and management
- `ansible_runner.py` - Ansible playbook execution
- `config_loader.py` - Configuration file loading and validation

### **CLI Utilities**
- `cli_utils.py` - kubectl management and environment cleanup
- `redeploy_utils.py` - Complete infrastructure redeploy functionality

### **Specialized Modules**
- `configure_k8s_oidc.py` - Kubernetes OIDC integration with Authentik
- `secure_env_loader.py` - Encrypted environment variable loading
- `sso_tester.py` - SSO authentication testing utilities
- `export_env_vars.py` - Environment variable export utilities

### **Configuration**
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies
- `__init__.py` - Package initialization and exports

## 🚀 Usage

### Import in Python Code
```python
# Core business logic
from Scripts.cluster_manager import ClusterManager
from Scripts.security_manager import NoahSecurityManager
from Scripts.helm_deployer import HelmDeployer

# CLI utilities  
from Scripts.cli_utils import cleanup_kubectl_cache
from Scripts.redeploy_utils import execute_redeploy
```

### Package-level Imports
```python
# Import from package level (recommended)
from Scripts import ClusterManager, NoahSecurityManager, cleanup_kubectl_cache
```

## 🧪 Testing

All modules in this directory are tested via:
- `../Tests/test_noah.py` - CLI integration tests
- `../Tests/test_workflows.py` - Workflow and syntax validation
- `../Tests/test_modifications.py` - Modification testing

## 📋 Standards

### **File Naming**
- Use `snake_case` for all Python files
- Descriptive names indicating module purpose
- Keep module names concise but clear

### **Module Structure**
```python
"""Module docstring describing purpose"""

import statements
class definitions
function definitions

if __name__ == "__main__":
    # CLI interface (if applicable)
    main()
```

### **Import Organization**
1. Standard library imports
2. Third-party imports  
3. Local/relative imports
4. Type hints and optional imports with fallbacks

### **Documentation**
- Comprehensive docstrings for all classes and functions
- Type hints for function parameters and returns
- Inline comments for complex logic
- README updates when adding new modules

## 🔄 Migration from CLI Directory

The former `CLI/` directory has been consolidated into `Scripts/` for:
- **Simplified structure** - Single import path
- **Logical organization** - All Python modules in one place
- **Easier maintenance** - Centralized testing and documentation
- **Clear separation** - Scripts vs configuration/data directories

This consolidation maintains all functionality while improving repository organization.
