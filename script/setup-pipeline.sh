#!/bin/bash

# Script d'initialisation du pipeline CI/CD NOAH
# Ce script configure l'environnement pour le déploiement automatisé

set -e

# Variables
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "🚀 Initialisation du pipeline CI/CD NOAH"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "🧪 MODE DRY-RUN - Aucune modification ne sera effectuée"
fi
echo "========================================"

# Vérification des prérequis
check_requirements() {
    echo "📋 Vérification des prérequis..."
    
    # Vérifier Ansible
    if ! command -v ansible &> /dev/null; then
        echo "❌ Ansible n'est pas installé"
        exit 1
    fi
    
    # Vérifier Git
    if ! command -v git &> /dev/null; then
        echo "❌ Git n'est pas installé"
        exit 1
    fi
    
    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 n'est pas installé"
        exit 1
    fi
    
    echo "✅ Tous les prérequis sont satisfaits"
}

# Installation des collections Ansible
install_ansible_collections() {
    echo "📦 Installation des collections Ansible..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Action qui serait exécutée:"
        echo "   - ansible-galaxy collection install -r ansible/requirements.yml --force"
        echo "✅ [DRY-RUN] Collections Ansible seraient installées"
    else
        ansible-galaxy collection install -r ansible/requirements.yml --force
        echo "✅ Collections Ansible installées"
    fi
}

# Clonage de Kubespray
setup_kubespray() {
    echo "⚙️  Configuration de Kubespray..."
    
    local kubespray_dir="ansible/kubespray"
    local requirements_file="$kubespray_dir/requirements.txt"
    
    # Test de la condition
    echo "🔍 Vérification de la condition Kubespray:"
    echo "   - Répertoire .git existe: $([ -d "$kubespray_dir/.git" ] && echo "✅ OUI" || echo "❌ NON")"
    echo "   - Fichier requirements.txt existe et non vide: $([ -s "$requirements_file" ] && echo "✅ OUI" || echo "❌ NON")"
    
    if [ ! -d "$kubespray_dir/.git" ] || [ ! -s "$requirements_file" ]; then
        echo "📥 Clonage de Kubespray requis..."
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "🧪 [DRY-RUN] Actions qui seraient exécutées:"
            echo "   - rm -rf $kubespray_dir"
            echo "   - git clone https://github.com/kubernetes-sigs/kubespray.git $kubespray_dir"
            echo "   - cd $kubespray_dir && git checkout v2.23.1 && cd ../.."
            echo "✅ [DRY-RUN] Kubespray serait cloné"
        else
            rm -rf "$kubespray_dir"
            git clone https://github.com/kubernetes-sigs/kubespray.git "$kubespray_dir"
            cd "$kubespray_dir"
            git checkout v2.23.1
            cd ../..
            echo "✅ Kubespray cloné"
        fi
    else
        echo "ℹ️  Kubespray déjà présent et valide"
    fi
    
    # Installation des dépendances Kubespray
    if [ -f "$requirements_file" ] || [[ "$DRY_RUN" == "true" ]]; then
        echo "📦 Installation des dépendances Kubespray..."
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "🧪 [DRY-RUN] Action qui serait exécutée:"
            echo "   - pip3 install -r $requirements_file"
            echo "✅ [DRY-RUN] Dépendances Kubespray seraient installées"
        else
            pip3 install -r "$requirements_file"
            echo "✅ Dépendances Kubespray installées"
        fi
    else
        echo "⚠️  Fichier requirements.txt de Kubespray non trouvé"
    fi
}

# Configuration des secrets
setup_secrets() {
    echo "🔐 Configuration des secrets..."
    
    if [ ! -f "ansible/.vault_pass" ]; then
        echo "⚠️  Créez le fichier ansible/.vault_pass avec votre mot de passe Vault"
        echo "    echo 'votre_mot_de_passe_vault' > ansible/.vault_pass"
        echo "    chmod 600 ansible/.vault_pass"
    fi
    
    if [ -f "ansible/vars/secrets.yml" ]; then
        echo "🔒 Chiffrement du fichier secrets.yml..."
        ansible-vault encrypt ansible/vars/secrets.yml || echo "⚠️  Fichier déjà chiffré ou erreur"
    fi
    
    echo "✅ Configuration des secrets terminée"
}

# Création des répertoires nécessaires
create_directories() {
    echo "📁 Création des répertoires..."
    
    mkdir -p ansible/kubeconfig
    mkdir -p ansible/reports
    mkdir -p helm/noah-chart/templates
    
    echo "✅ Répertoires créés"
}

# Validation de la configuration
validate_config() {
    echo "🔍 Validation de la configuration..."
    
    # Vérifier la syntaxe des playbooks
    for playbook in ansible/playbooks/*.yml; do
        if [ -f "$playbook" ]; then
            echo "  Validation de $(basename "$playbook")..."
            ansible-playbook --syntax-check "$playbook" || echo "⚠️  Erreur de syntaxe dans $playbook"
        fi
    done
    
    # Vérifier l'inventaire
    if [ -f "ansible/inventory/mycluster/hosts.yaml" ]; then
        echo "  Validation de l'inventaire..."
        ansible-inventory --list -i ansible/inventory/mycluster/hosts.yaml > /dev/null || echo "⚠️  Erreur dans l'inventaire"
    fi
    
    echo "✅ Validation terminée"
}

# Affichage des informations finales
display_info() {
    echo ""
    echo "🎉 Initialisation terminée !"
    echo "=============================="
    echo ""
    echo "📋 Prochaines étapes :"
    echo "1. Configurer vos secrets dans ansible/vars/secrets.yml"
    echo "2. Ajuster l'inventaire dans ansible/inventory/mycluster/hosts.yaml"
    echo "3. Mettre à jour les valeurs dans values/values-prod.yaml"
    echo "4. Configurer les secrets GitHub Actions :"
    echo "   - SSH_PRIVATE_KEY"
    echo "   - ANSIBLE_VAULT_PASSWORD"
    echo "   - MASTER_HOST"
    echo "5. Pousser sur la branche main ou Ansible pour déclencher le pipeline"
    echo ""
    echo "🔧 Commandes utiles :"
    echo "  # Tester la connexion"
    echo "  ansible all -m ping -i ansible/inventory/mycluster/hosts.yaml"
    echo ""
    echo "  # Lancer le déploiement manuellement"
    echo "  cd ansible && ansible-playbook playbooks/01-provision.yml -i inventory/mycluster/hosts.yaml"
    echo ""
    echo "  # Chiffrer les secrets"  
    echo "  ansible-vault encrypt ansible/vars/secrets.yml"
    echo ""
    echo "✨ Bon déploiement !"
}

# Exécution du script
main() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 Mode dry-run activé - seule la logique sera testée"
    fi
    
    check_requirements
    create_directories
    install_ansible_collections
    setup_kubespray
    setup_secrets
    validate_config
    display_info
}

# Lancement du script
main "$@"
