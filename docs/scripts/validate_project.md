# Project Validation Script

This page documents the `validate_project.sh` script used in the N.O.A.H project.

## Purpose
- Runs comprehensive validation on YAML, Ansible, Helm, and shell scripts.
- Ensures code quality and best practices before merging or deploying.

## Usage
```bash
./Script/validate_project.sh
```

## What it Checks
- YAML syntax and linting
- Ansible inventory and playbook syntax
- Helm chart linting and template rendering
- Shell script syntax
- File structure and required files

## See Also
- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [User Guide](../USER_GUIDE.md)
