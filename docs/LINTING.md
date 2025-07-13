# NOAH Linting and Code Quality

This document describes the automated code quality and linting setup for the NOAH project using GitHub Super-Linter and pre-commit hooks.

## Overview

The NOAH project uses a comprehensive linting and code quality setup that includes:

- **GitHub Super-Linter**: Multi-language linter running in CI/CD
- **Pre-commit hooks**: Local validation before commits
- **Custom configurations**: Tailored rules for our project structure

## Supported Languages and Tools

### Languages and Formats
- **YAML**: Custom yamllint configuration excluding Helm templates
- **Markdown**: Markdownlint with project-specific rules
- **Bash/Shell**: ShellCheck for script validation
- **Python**: Black formatting + Flake8 linting
- **Ansible**: Ansible-lint for playbook validation
- **Helm**: Helm lint for chart validation
- **Docker**: Hadolint for Dockerfile linting
- **JSON**: JSON syntax validation

### Quality Checks
- Trailing whitespace removal
- End-of-file fixing
- Merge conflict detection
- Case conflict detection
- Mixed line ending normalization

## Quick Setup

Run the setup script to install and configure everything:

```bash
./setup-linting.sh
```

This will:
1. Install pre-commit hooks
2. Configure all linters
3. Create helper scripts
4. Run initial validation

## Usage

### Automatic (Recommended)
Pre-commit hooks run automatically on each commit. No action needed!

### Manual Validation
```bash
# Run all hooks on changed files
pre-commit run

# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run --hook-id yamllint

# Run Super-Linter locally (requires Docker)
./run-super-linter.sh

# Run Super-Linter on all files
./run-super-linter.sh --all
```

### GitHub Actions
Super-Linter runs automatically on:
- Push to main/develop branches
- Pull requests to main branch

Only changed files are validated to improve performance.

## Configuration Files

### Main Configurations
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.markdownlint.yml` - Markdown linting rules
- `Script/.yamllint.yml` - YAML linting rules (excludes Helm templates)
- `Ansible/.ansible-lint` - Ansible-specific linting rules

### GitHub Actions
- `.github/workflows/ci.yml` - CI pipeline with Super-Linter

## Customization

### Adding New Hooks
Edit `.pre-commit-config.yaml` and run:
```bash
pre-commit install
pre-commit autoupdate
```

### Modifying Rules
Update the relevant configuration file:
- YAML rules: `Script/.yamllint.yml`
- Markdown rules: `.markdownlint.yml`
- Ansible rules: `Ansible/.ansible-lint`

### Skipping Hooks
```bash
# Skip all hooks for a commit (not recommended)
git commit --no-verify

# Skip specific hooks using environment variables
SKIP=helm-lint git commit
```

## Troubleshooting

### Pre-commit Not Found
Add to your shell profile:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Docker Issues (Super-Linter)
Ensure Docker is installed and running:
```bash
docker --version
docker run hello-world
```

### Hook Failures
1. Read the error message carefully
2. Fix the reported issues
3. Stage the fixes: `git add .`
4. Retry the commit

### Common Issues

#### YAML Linting
- Helm templates are automatically excluded
- Check indentation (2 spaces)
- Verify YAML syntax

#### Markdown Linting
- Line length limit: 120 characters
- Use proper heading hierarchy
- Check for trailing spaces

#### Shell Scripts
- Use ShellCheck recommendations
- Quote variables properly
- Handle error cases

## Best Practices

1. **Run hooks before pushing**: `pre-commit run --all-files`
2. **Update regularly**: `pre-commit autoupdate`
3. **Fix issues incrementally**: Don't disable entire hooks
4. **Use meaningful commit messages**: Follow conventional commits
5. **Test locally**: Use `./run-super-linter.sh` before pushing

## Benefits

- **Consistent code quality** across the entire project
- **Early issue detection** before CI/CD
- **Automated formatting** for supported languages
- **Reduced review time** by catching issues early
- **Team collaboration** with shared standards

## Integration with IDEs

### VS Code
Install recommended extensions:
- YAML
- Markdownlint
- ShellCheck
- Python
- Ansible

### Vim/Neovim
Use ALE or similar plugins with the same linters.

## Performance

- Pre-commit hooks only run on changed files
- Super-Linter in CI only validates changed files
- Docker image is cached for faster local runs
- Hooks are optimized for development workflow

## Support

For issues or questions about the linting setup:
1. Check this documentation
2. Review configuration files
3. Run with verbose output: `pre-commit run --verbose`
4. Open an issue in the project repository

---

*This linting setup ensures high code quality and consistency across the NOAH project while maintaining developer productivity.*
