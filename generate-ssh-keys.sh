#!/bin/bash
# Script pour générer une paire de clés SSH pour le pipeline NOAH

echo "🔑 Génération des clés SSH pour le pipeline NOAH"
echo "================================================"

# Générer une nouvelle paire de clés SSH
ssh-keygen -t ed25519 -C "noah-pipeline@github-actions" -f ~/.ssh/noah_pipeline -N ""

echo ""
echo "✅ Clés générées avec succès !"
echo ""
echo "📋 Configuration GitHub Actions :"
echo "--------------------------------"
echo "1. Copiez la clé PRIVÉE ci-dessous dans le secret GitHub 'SSH_PRIVATE_KEY' :"
echo ""
cat ~/.ssh/noah_pipeline
echo ""
echo "2. Copiez la clé PUBLIQUE ci-dessous sur vos serveurs dans ~/.ssh/authorized_keys :"
echo ""
cat ~/.ssh/noah_pipeline.pub
echo ""
echo "💡 Commandes pour déployer la clé publique sur vos serveurs :"
echo "ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@IP_MASTER_1"
echo "ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@IP_MASTER_2"
echo "ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@IP_WORKER_1"
