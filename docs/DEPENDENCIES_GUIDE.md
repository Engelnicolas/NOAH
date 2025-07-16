# NOAH Dependencies Management Guide

## 🎯 Overview

This guide covers Python dependencies management for the NOAH project, including installation, updates, validation, and troubleshooting.

---

## 📦 Dependencies Structure

### Core Dependencies (`requirements.txt`)
- **Production-ready** packages required for NOAH operations
- **Version-pinned** for stability and security
- **Tested** across Python 3.8-3.12
- **Cross-platform** compatible (Linux, macOS, Windows)
- **Development tools** included as optional dependencies

---

## 🚀 Quick Start

### Install Dependencies
```bash
# Install core dependencies only
./Script/noah deps --install-only

# Install core + development dependencies
./Script/noah deps --dev --install-only

# Install with verbose output
./Script/noah deps --install-only --verbose
```

### Validate Installation
```bash
# Basic validation
./Script/noah deps

# Full validation with security check
./Script/noah deps --check-security

# Generate dependency report
./Script/noah deps --report
```

---

## 📋 Available Commands

### Installation Commands
```bash
# Install core dependencies
./Script/noah deps --install-only

# Install with development dependencies
./Script/noah deps --dev --install-only

# Upgrade all dependencies
./Script/noah deps --upgrade

# Upgrade with development dependencies
./Script/noah deps --dev --upgrade
```

### Validation Commands
```bash
# Validate installed packages
./Script/noah deps

# Check for security vulnerabilities
./Script/noah deps --check-security

# Generate comprehensive report
./Script/noah deps --report

# Verbose output for debugging
./Script/noah deps --verbose
```

### Maintenance Commands
```bash
# Clean unused dependencies
./Script/noah deps --cleanup

# Check for outdated packages
./Script/noah deps --report

# Full maintenance cycle
./Script/noah deps --upgrade --check-security --report
```

---

## 📊 Dependency Categories

### System & Hardware
```python
psutil>=5.9.0,<6.0.0          # System monitoring
```

### Configuration & Data
```python
PyYAML>=6.0,<7.0              # YAML processing
jsonschema>=4.17.0,<5.0       # JSON validation
configparser>=5.3.0,<6.0      # Configuration management
```

### Networking & HTTP
```python
requests>=2.28.0,<3.0         # HTTP requests
urllib3>=1.26.0,<2.0          # URL handling
```

### CLI & User Interface
```python
click>=8.1.0,<9.0             # CLI framework
colorama>=0.4.6,<1.0          # Terminal colors
rich>=13.0.0,<14.0            # Rich text formatting
```

### Date & Time
```python
python-dateutil>=2.8.0,<3.0   # Date/time parsing
```

### Logging & Observability
```python
structlog>=22.3.0,<24.0       # Structured logging
```

### Testing & Quality
```python
pytest>=7.4.0,<8.0           # Testing framework
pytest-cov>=4.1.0,<5.0       # Coverage reporting
bandit>=1.7.5,<2.0           # Security scanning
```

### Optional Dependencies
```python
# Commented out in requirements.txt, install manually if needed:
# kubernetes>=27.2.0,<28.0     # Kubernetes client
# docker>=6.1.0,<7.0          # Docker SDK
# ansible-core>=2.14.0,<3.0   # Ansible automation
```

---

## 🔧 Manual Installation

### Core Dependencies Only
```bash
pip install -r Script/requirements.txt
```

### All Dependencies (Including Development Tools)
```bash
pip install -r Script/requirements.txt
```

### Optional Dependencies
```bash
# Kubernetes integration
pip install kubernetes>=27.2.0,<28.0

# Docker integration
pip install docker>=6.1.0,<7.0

# Ansible integration
pip install ansible-core>=2.14.0,<3.0
```

---

## 🛡️ Security Best Practices

### Regular Security Checks
```bash
# Check for vulnerabilities
./Script/noah deps --check-security

# Manual security audit
pip install safety
safety check

# Dependency vulnerability scan
pip install pip-audit
pip-audit
```

### Version Management
- **Pin major versions** to prevent breaking changes
- **Update regularly** for security patches
- **Test updates** in development environment first
- **Use version ranges** for flexibility

### Security Configuration
```bash
# Use pip configuration for security
cp Script/pip.conf ~/.config/pip/pip.conf

# Verify package integrity
pip install --require-hashes -r requirements.txt
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Installation Failures
```bash
# Problem: Package not found
ERROR: Could not find a version that satisfies the requirement package_name

# Solution: Update pip and try again
pip install --upgrade pip
./Script/noah deps --install-only

# Alternative: Use different index
pip install --index-url https://pypi.org/simple/ package_name
```

#### 2. Permission Errors
```bash
# Problem: Permission denied
ERROR: Could not install packages due to an EnvironmentError

# Solution: Use user installation
pip install --user -r Script/requirements.txt

# Or use virtual environment
python -m venv noah-env
source noah-env/bin/activate  # Linux/macOS
noah-env\Scripts\activate     # Windows
```

#### 3. SSL Certificate Issues
```bash
# Problem: SSL verification failed
ERROR: SSL: CERTIFICATE_VERIFY_FAILED

# Solution: Use trusted hosts
pip install --trusted-host pypi.org --trusted-host pypi.python.org -r Script/requirements.txt
```

#### 4. Dependency Conflicts
```bash
# Problem: Conflicting dependencies
ERROR: package_a depends on package_b>=1.0, but you'll have package_b 0.9

# Solution: Force reinstall
pip install --force-reinstall -r Script/requirements.txt

# Or use dependency resolver
pip install --upgrade --force-reinstall --no-deps -r Script/requirements.txt
```

#### 5. Outdated Packages
```bash
# Check outdated packages
./Script/noah deps --report

# Update all packages
./Script/noah deps --upgrade

# Update specific package
pip install --upgrade package_name
```

### Debug Mode
```bash
# Enable verbose output
./Script/noah deps --verbose

# Show pip debug information
pip install --verbose package_name

# Show dependency tree
pip install pipdeptree
pipdeptree
```

---

## 📊 Dependency Reports

### Generate Reports
```bash
# Basic report
./Script/noah deps --report

# Detailed report with security check
./Script/noah deps --report --check-security

# Custom report location
./Script/noah deps --report > custom_report.txt
```

### Report Contents
- **Python version** and platform information
- **Installed packages** with versions
- **Outdated packages** with available updates
- **Security vulnerabilities** (if --check-security used)
- **Dependency tree** and relationships

---

## 🔄 Update Workflow

### Regular Updates
```bash
# 1. Check current status
./Script/noah deps --report

# 2. Update dependencies
./Script/noah deps --upgrade

# 3. Validate installation
./Script/noah deps --check-security

# 4. Run tests
pytest tests/  # if available

# 5. Generate final report
./Script/noah deps --report
```

### Before Deployment
```bash
# Validate production dependencies
./Script/noah deps --install-only

# Check for security issues
./Script/noah deps --check-security

# Verify all scripts work
./Script/noah validate --scope all
```

---

## 🎯 Best Practices

### Development Environment
1. **Use virtual environments** for isolation
2. **Pin exact versions** in production
3. **Regular security checks** with automated tools
4. **Document dependencies** with clear comments
5. **Test updates** in staging environment

### Production Environment
1. **Use pinned versions** from requirements.txt
2. **Avoid development dependencies** in production
3. **Regular security audits** and updates
4. **Monitor dependency vulnerabilities**
5. **Backup working configurations**

### Maintenance Schedule
- **Weekly**: Check for security updates
- **Monthly**: Review outdated packages
- **Quarterly**: Major version updates
- **Annually**: Dependency audit and cleanup

---

## 📚 Additional Resources

### Official Documentation
- [pip documentation](https://pip.pypa.io/en/stable/)
- [Python packaging guide](https://packaging.python.org/)
- [Virtual environments](https://docs.python.org/3/tutorial/venv.html)

### Security Resources
- [Safety database](https://github.com/pyupio/safety-db)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Python security advisories](https://github.com/pypa/advisory-database)

### Development Tools
- [pip-tools](https://github.com/jazzband/pip-tools)
- [pipdeptree](https://github.com/tox-dev/pipdeptree)
- [pip-review](https://github.com/jgonggrijp/pip-review)

---

## 🎉 Conclusion

The NOAH dependencies management system provides:

✅ **Comprehensive dependency management** with automated tools
✅ **Security-first approach** with regular vulnerability checks
✅ **Cross-platform compatibility** for all major operating systems
✅ **Development-friendly** with clear documentation and tooling
✅ **Production-ready** with pinned versions and stability

Use `./Script/noah deps --help` for command-specific help and options.

For issues or questions, refer to the troubleshooting section or check the project documentation.
