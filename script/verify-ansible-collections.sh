#!/bin/bash
# Verify Ansible collections and modules are properly installed
# This script helps diagnose collection installation issues in CI/CD

set -e

echo "🔍 NOAH Ansible Collection Verification"
echo "======================================="

# Check Ansible version
echo "Ansible version:"
ansible --version | head -1

echo ""
echo "📦 Checking critical collections..."

# Check if critical collections are installed
collections=(
    "community.proxmox"
    "kubernetes.core"
    "community.general"
    "community.kubernetes"
    "ansible.posix"
    "community.crypto"
)

for collection in "${collections[@]}"; do
    if ansible-galaxy collection list "$collection" >/dev/null 2>&1; then
        version=$(ansible-galaxy collection list "$collection" | grep -o "${collection}.*" | awk '{print $2}' | head -1)
        echo "✅ $collection $version"
    else
        echo "❌ $collection NOT FOUND"
        exit 1
    fi
done

echo ""
echo "🔧 Testing critical modules..."

# Test critical modules
modules=(
    "community.proxmox.proxmox_kvm"
    "kubernetes.core.k8s"
    "community.kubernetes.helm"
)

for module in "${modules[@]}"; do
    if ansible-doc "$module" >/dev/null 2>&1; then
        echo "✅ $module module available"
    else
        echo "❌ $module module NOT FOUND"
        exit 1
    fi
done

echo ""
echo "🎯 Testing playbook syntax..."
playbooks=(
    "ansible/playbooks/01-provision.yml"
    "ansible/playbooks/02-install-k8s.yml"
    "ansible/playbooks/03-configure-cluster.yml"
    "ansible/playbooks/04-deploy-apps.yml"
    "ansible/playbooks/05-verify-deployment.yml"
)

for playbook in "${playbooks[@]}"; do
    if [ -f "$playbook" ]; then
        if ansible-playbook --syntax-check "$playbook" >/dev/null 2>&1; then
            echo "✅ $(basename "$playbook") syntax valid"
        else
            echo "❌ $(basename "$playbook") syntax ERROR"
            exit 1
        fi
    else
        echo "⚠️  $(basename "$playbook") not found (skipping)"
    fi
done

echo ""
echo "🎉 All checks passed! Ansible collections and modules are ready."
echo "Ready to run NOAH deployment playbooks."
