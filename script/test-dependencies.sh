#!/bin/bash
# Test script to verify Ansible collections and dependencies

set -e

echo "🔍 NOAH Infrastructure Test Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test Python dependencies
echo -e "\n${YELLOW}Testing Python dependencies...${NC}"
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 is available"
    python3 --version
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Test pip packages
echo -e "\n${YELLOW}Testing pip packages...${NC}"
required_packages=("ansible" "proxmoxer" "requests" "kubernetes" "pyyaml")
for package in "${required_packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo "✅ $package is installed"
    else
        echo -e "${YELLOW}⚠️  $package not found - install with: pip install -r script/requirements.txt${NC}"
    fi
done

# Test Ansible
echo -e "\n${YELLOW}Testing Ansible installation...${NC}"
if command -v ansible &> /dev/null; then
    echo "✅ Ansible is available"
    ansible --version | head -1
else
    echo -e "${RED}❌ Ansible not found${NC}"
    exit 1
fi

# Test Ansible collections
echo -e "\n${YELLOW}Testing Ansible collections...${NC}"
required_collections=("community.general" "kubernetes.core" "community.kubernetes")
for collection in "${required_collections[@]}"; do
    if ansible-galaxy collection list | grep -q "$collection"; then
        echo "✅ $collection is installed"
    else
        echo -e "${YELLOW}⚠️  $collection not found - install with: ansible-galaxy collection install -r ansible/requirements.yml --force${NC}"
    fi
done

# Test specific modules
echo -e "\n${YELLOW}Testing specific Ansible modules...${NC}"
modules=("community.general.proxmox_kvm" "kubernetes.core.k8s" "community.kubernetes.helm")
for module in "${modules[@]}"; do
    if ansible-doc "$module" &>/dev/null; then
        echo "✅ $module module is available"
    else
        echo -e "${YELLOW}⚠️  $module module not found${NC}"
    fi
done

# Test playbook syntax
echo -e "\n${YELLOW}Testing playbook syntax...${NC}"
cd "$(dirname "$0")/.."
if [ -f "ansible/playbooks/01-provision.yml" ]; then
    if ansible-playbook --syntax-check ansible/playbooks/01-provision.yml -i ansible/inventory/mycluster/hosts.yaml &>/dev/null; then
        echo "✅ Playbook syntax is valid"
    else
        echo -e "${YELLOW}⚠️  Playbook syntax check failed${NC}"
    fi
else
    echo -e "${RED}❌ Playbook not found${NC}"
fi

# Test inventory file
echo -e "\n${YELLOW}Testing inventory configuration...${NC}"
if [ -f "ansible/inventory/mycluster/hosts.yaml" ]; then
    echo "✅ Inventory file exists"
    if ansible-inventory --list -i ansible/inventory/mycluster/hosts.yaml &>/dev/null; then
        echo "✅ Inventory syntax is valid"
    else
        echo -e "${YELLOW}⚠️  Inventory syntax check failed${NC}"
    fi
else
    echo -e "${RED}❌ Inventory file not found${NC}"
fi

echo -e "\n${GREEN}🎉 Test completed!${NC}"
echo "If you see warnings above, install missing dependencies:"
echo "  pip install -r script/requirements.txt"
echo "  ansible-galaxy collection install -r ansible/requirements.yml --force"
