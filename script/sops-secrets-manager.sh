#!/bin/bash
# Gestionnaire de secrets NOAH avec SOPS
# Usage: ./sops-secrets-manager.sh {edit|view|rotate|deploy}

set -e

SECRETS_FILE="ansible/vars/secrets.yml"

case "${1:-help}" in
    edit)
        echo "Édition des secrets avec SOPS..."
        sops "$SECRETS_FILE"
        ;;
    view)
        echo "Affichage des secrets..."
        sops --decrypt "$SECRETS_FILE"
        ;;
    rotate)
        echo "Rotation des secrets..."
        temp_file=$(mktemp)
        sops --decrypt "$SECRETS_FILE" > "$temp_file"
        
        # Rotation des mots de passe (exemple)
        sed -i "s/vault_postgres_password: .*/vault_postgres_password: \"$(openssl rand -base64 32)\"/" "$temp_file"
        sed -i "s/vault_keycloak_admin_password: .*/vault_keycloak_admin_password: \"$(openssl rand -base64 24)\"/" "$temp_file"
        
        # Re-chiffrer
        sops --encrypt "$temp_file" > "$SECRETS_FILE"
        rm "$temp_file"
        echo "Rotation terminée"
        ;;
    deploy)
        echo "Déploiement avec secrets..."
        if command -v helm >/dev/null 2>&1; then
            # Utiliser helm-secrets si disponible
            if helm plugin list | grep -q secrets; then
                helm secrets upgrade --install noah ./helm/noah -f "$SECRETS_FILE"
            else
                echo "Plugin helm-secrets non installé"
                echo "Installation: helm plugin install https://github.com/jkroepke/helm-secrets"
            fi
        fi
        ;;
    help|*)
        echo "Usage: $0 {edit|view|rotate|deploy}"
        echo ""
        echo "Commandes:"
        echo "  edit     Éditer les secrets avec SOPS"
        echo "  view     Afficher les secrets déchiffrés"
        echo "  rotate   Effectuer une rotation des secrets"
        echo "  deploy   Déployer avec les secrets"
        ;;
esac
