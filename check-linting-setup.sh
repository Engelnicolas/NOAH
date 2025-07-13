#!/bin/bash

# NOAH Super-Linter Setup Summary
# Shows the current linting configuration and status

echo "🔍 NOAH Super-Linter Configuration Summary"
echo "=========================================="
echo

# Check if pre-commit is installed
if command -v pre-commit &> /dev/null; then
    echo "✅ Pre-commit: $(pre-commit --version)"
else
    echo "❌ Pre-commit: Not installed"
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✅ Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"
else
    echo "❌ Docker: Not available (needed for Super-Linter)"
fi

echo
echo "📋 Configuration Files:"
echo "========================"

configs=(
    ".pre-commit-config.yaml:Pre-commit hooks configuration"
    ".markdownlint.yml:Markdown linting rules"
    "Script/.yamllint.yml:YAML linting rules"
    "Ansible/.ansible-lint:Ansible linting rules"
    ".github/workflows/ci.yml:GitHub Actions CI with Super-Linter"
    "setup-linting.sh:Development environment setup"
    "run-super-linter.sh:Local Super-Linter runner"
    "docs/LINTING.md:Documentation"
)

for config in "${configs[@]}"; do
    file="${config%%:*}"
    desc="${config##*:}"
    if [[ -f "$file" ]]; then
        echo "   ✅ $file - $desc"
    else
        echo "   ❌ $file - $desc (missing)"
    fi
done

echo
echo "🎯 Quick Start:"
echo "================"
echo "1. Run setup: ./setup-linting.sh"
echo "2. Make changes to your code"
echo "3. Commit (hooks run automatically)"
echo "4. Optional: ./run-super-linter.sh"
echo

# Check if hooks are installed
if [[ -f ".git/hooks/pre-commit" ]]; then
    echo "✅ Pre-commit hooks are installed and ready!"
else
    echo "⚠️  Pre-commit hooks not installed. Run: ./setup-linting.sh"
fi

echo
echo "📚 Documentation: docs/LINTING.md"
echo "🔧 Support: Check configuration files and documentation"
