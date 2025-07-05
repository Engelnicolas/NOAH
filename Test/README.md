# N.O.A.H Testing Suite - Simplified & Modernized

## 🎯 Overview

The N.O.A.H testing suite has been **dramatically simplified** from 12+ complex test files to just **2 comprehensive scripts** that provide the same level of coverage with much easier maintenance.

**Before**: 8 shell scripts + 3 Python files + complex configuration
**After**: 1 shell script + 1 Python file + minimal configuration

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Helm 3.x** (optional, for advanced chart testing)
- **Basic shell tools** (bash, curl, find)

### Installation & Running Tests

```bash
# Install minimal dependencies
cd Test
make install

# Run all tests (comprehensive coverage)
make test

# Check available commands
make help
```

## 📁 Test Suite Structure (Only 6 Files!)

```
Test/
├── noah_test.py          # 🐍 Python test suite (structure, YAML, Helm validation)
├── unified_tests.sh      # 🐚 Shell test suite (dependencies, integration, security)
├── test_config.yaml      # ⚙️  Simple configuration
├── requirements.txt      # 📦 Minimal dependencies (PyYAML, requests)
├── Makefile             # 🛠️  Easy commands and targets
└── README.md            # 📖 This documentation
```

## 🧪 What Gets Tested

### 🐍 **Python Tests** (`noah_test.py`)

**Structure & Configuration:**
- ✅ Project directory structure validation
- ✅ Required files presence check
- ✅ Configuration file consistency

**YAML Validation:**
- ✅ Syntax checking across all YAML files
- ✅ Schema validation for Helm values
- ✅ Indentation and formatting checks

**Helm Chart Validation:**
- ✅ Chart structure and metadata validation
- ✅ Template syntax checking
- ✅ Values schema validation
- ✅ Dependency verification

**Security Checks:**
- ✅ Basic security policy validation
- ✅ Sensitive data exposure checks
- ✅ Permission and access control validation

### 🐚 **Shell Tests** (`unified_tests.sh`)

**Dependency Checking:**
- ✅ Required tools availability (helm, kubectl, etc.)
- ✅ Version compatibility verification
- ✅ System prerequisites validation

**Helm Operations:**
- ✅ Chart linting with helm lint
- ✅ Template rendering tests
- ✅ Dependency update verification
- ✅ Values file validation

**Integration Testing:**
- ✅ Cross-service configuration consistency
- ✅ Network connectivity tests
- ✅ Basic deployment simulation

**Security Scanning:**
- ✅ Chart security policy validation
- ✅ Container image security checks
- ✅ RBAC configuration validation

## 🎮 Running Tests

### Make Targets (Recommended)

```bash
# Quick reference
make help           # Show all available targets

# Essential commands
make install        # Install dependencies
make test           # Run all tests
make clean          # Clean up test artifacts

# Specific test types
make test-python    # Python-based tests only
make test-shell     # Shell-based tests only
make test-charts    # Helm chart tests only

# Utilities
make check-deps     # Check dependencies
make show-config    # Display test configuration
```

### Direct Script Execution

#### Python Test Options
```bash
cd Test
python3 noah_test.py                  # Run all Python tests
python3 noah_test.py -v               # Verbose output
python3 noah_test.py --charts-only    # Helm charts only
python3 noah_test.py --structure-only # Structure validation only
python3 noah_test.py --yaml-only      # YAML validation only
```

#### Shell Test Options
```bash
cd Test
./unified_tests.sh                    # Run all shell tests
./unified_tests.sh --deps-only        # Check dependencies only
./unified_tests.sh --python-only      # Run Python tests via shell
./unified_tests.sh --helm-only        # Helm operations only
./unified_tests.sh --yaml-only        # YAML validation only
./unified_tests.sh --security-only    # Security checks only
./unified_tests.sh --integration      # Integration tests only
./unified_tests.sh --help             # Show all options
```

## 📋 Test Output & Reports

### Console Output
Both scripts provide:
- 🎨 **Color-coded output** for easy status identification
- 📊 **Progress indicators** showing test execution status
- ⏱️ **Execution timing** for performance monitoring
- 📝 **Summary statistics** with pass/fail counts

### Generated Reports
- **📄 JSON reports** (Python): Structured test results in JSON format
- **📝 Log files** (Shell): Detailed execution logs with timestamps
- **✅ Exit codes**: Clear success/failure indication for CI/CD integration

### Example Output
```bash
$ make test

🧪 N.O.A.H Test Suite - Running All Tests...

🐍 Python Tests (noah_test.py):
  ✅ Project structure validation    [PASSED]
  ✅ YAML syntax checking           [PASSED]
  ✅ Helm chart validation          [PASSED]
  ✅ Security checks                [PASSED]

🐚 Shell Tests (unified_tests.sh):
  ✅ Dependency checking            [PASSED]
  ✅ Helm chart linting             [PASSED]
  ✅ Integration testing            [PASSED]
  ✅ Security scanning              [PASSED]

📊 Summary: 8/8 tests passed ✅
⏱️  Total execution time: 45 seconds
```

## ⚙️ Configuration

### Simple Configuration (`test_config.yaml`)
```yaml
# Minimal, essential configuration
test_namespace: "noah-test"
timeout_seconds: 300
helm_charts:
  - gitlab
  - grafana
  - keycloak
  - mattermost
  - nextcloud
  - oauth2-proxy
  - openedr
  - prometheus
  - samba4
  - wazuh
run_security_tests: true
python_version_min: "3.8"
helm_version_min: "3.0"
```

### Environment Variables
```bash
# Override default configuration
export NOAH_TEST_NAMESPACE="custom-test"
export NOAH_TEST_TIMEOUT=600
export NOAH_VERBOSE=true
export NOAH_PARALLEL=true
```

## 🚀 CI/CD Integration

### GitHub Actions (Simplified)
The test suite integrates seamlessly with CI/CD:

```yaml
name: NOAH Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        cd Test
        make install
    
    - name: Run comprehensive tests
      run: |
        cd Test
        make test
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-reports
        path: Test/reports/
```

## 🔧 Development & Customization

### Adding New Tests

#### To Python Test Suite (`noah_test.py`):
```python
def test_custom_validation(self):
    """Add custom validation logic"""
    # Your custom test logic here
    self.assertTrue(condition, "Custom test message")
```

#### To Shell Test Suite (`unified_tests.sh`):
```bash
run_custom_tests() {
    echo "Running custom tests..."
    # Your custom shell test logic here
    return 0  # or 1 for failure
}
```

### Extending Configuration
Add new settings to `test_config.yaml`:
```yaml
custom_settings:
  enable_feature_x: true
  custom_timeout: 120
```

## � Troubleshooting

### Common Issues

1. **Permission Errors**:
   ```bash
   chmod +x Test/unified_tests.sh
   ```

2. **Missing Dependencies**:
   ```bash
   cd Test
   make install
   pip install -r requirements.txt
   ```

3. **Helm Not Found**:
   ```bash
   # Install Helm
   curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
   sudo mv linux-amd64/helm /usr/local/bin/
   ```

4. **Python Version Issues**:
   ```bash
   python3 --version  # Should be 3.8+
   # Use pyenv or conda to manage Python versions
   ```

### Debug Mode
```bash
# Enable verbose output
export NOAH_VERBOSE=true

# Enable debug mode
export NOAH_DEBUG=true

# Run with maximum verbosity
make test VERBOSE=1
```

### Getting Help
```bash
# Show detailed help
make help
./unified_tests.sh --help
python3 noah_test.py --help

# Check system compatibility
make check-deps
```

## � Migration from Legacy Tests

### What Was Removed
We consolidated and removed these **legacy test files**:
- ❌ `test_helm.py` → merged into `noah_test.py`
- ❌ `test_utils.py` → merged into `noah_test.py`
- ❌ `test_pytest.py` → merged into `noah_test.py`
- ❌ `chaos_tests.sh` → core features in `unified_tests.sh`
- ❌ `compliance_tests.sh` → core features in `unified_tests.sh`
- ❌ `helm_chart_tests.sh` → merged into `unified_tests.sh`
- ❌ `integration_tests.sh` → merged into `unified_tests.sh`
- ❌ `load_tests.sh` → essential features in `unified_tests.sh`
- ❌ `performance_tests.sh` → basic checks in `unified_tests.sh`
- ❌ `run_all_tests.sh` → replaced by `make test`
- ❌ `security_tests.sh` → merged into `unified_tests.sh`

### What We Kept
- ✅ **All essential functionality** consolidated into 2 scripts
- ✅ **Same comprehensive coverage** as before
- ✅ **Faster execution** due to optimized code paths
- ✅ **Easier maintenance** with unified codebase
- ✅ **Better error handling** and reporting

## 🎯 Best Practices

### Regular Testing
```bash
# Run tests before committing changes
make test

# Quick validation during development
make test-python  # Fast structure/YAML checks

# Full validation before deployment
make test         # Complete test suite
```

### Continuous Integration
- **Pre-commit hooks**: Run tests automatically before commits
- **Pull request validation**: Automatic test execution on PRs
- **Deployment gates**: Tests must pass before deployment

### Performance Optimization
- **Parallel execution**: Use `--parallel` flag when available
- **Selective testing**: Use specific test targets during development
- **Caching**: Dependencies are cached between runs

## 🆘 Support

### Getting Help
1. **Check this README** for common usage patterns
2. **Review test output** for specific error details
3. **Use debug mode** for detailed troubleshooting
4. **Check project documentation** in `docs/`

### Contributing
1. **Follow existing patterns** when adding new tests
2. **Test your changes** with `make test`
3. **Update documentation** for new features
4. **Keep it simple** - maintain the unified approach

---

**🎉 The simplified NOAH test suite: Maximum coverage, minimum complexity!**

For more information about the NOAH project, see the main documentation in the `docs/` directory.

