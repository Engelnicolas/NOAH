#!/bin/bash

# Complete migration from Kustomize to Helm
set -e

echo "🔄 Starting migration from Kustomize to Helm..."

# Step 1: Backup current deployment
echo "💾 Creating backup of current deployment..."
kubectl get all -n noah-namespace -o yaml > backup-kustomize-deployment.yaml

# Step 2: Remove current Kustomize deployment
echo "🗑️  Removing current Kustomize deployment..."
kubectl delete -k k8s/base/ --ignore-not-found=true

# Step 3: Deploy with Helm
echo "🚀 Deploying with Helm..."
./scripts/deploy-helm.sh

# Step 4: Verify migration
echo "✅ Verifying migration..."
kubectl get pods -n noah-namespace
kubectl get secrets -n noah-namespace

# Step 5: Remove old Kustomize files (optional)
read -p "Do you want to remove the old k8s/base/ directory? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing k8s/base/ directory..."
    rm -rf k8s/base/
    echo "✅ Old Kustomize files removed"
else
    echo "📁 Keeping k8s/base/ directory for reference"
fi

echo "🎉 Migration completed successfully!"
echo "📋 New workflow:"
echo "- Deploy: ./scripts/deploy-helm.sh"
echo "- Update: helm upgrade noah helm/noah-chart/ -n noah-namespace"
echo "- Rollback: helm rollback noah -n noah-namespace"
