#!/bin/bash

# Script de configuration automatique pour le pipeline NOAH CI/CD
# Ce script configure tous les éléments nécessaires avec des valeurs par défaut

set -e

echo "🔧 Configuration automatique du pipeline NOAH"
echo "=============================================="

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables de configuration (modifiables)
DOMAIN="${DOMAIN:-noah.local}"
MASTER_IP="${MASTER_IP:-192.168.1.10}"
WORKER_IP="${WORKER_IP:-192.168.1.12}"
INGRESS_IP="${INGRESS_IP:-192.168.1.10}"
VAULT_PASSWORD="${VAULT_PASSWORD:-MYPASSWORD}"

echo -e "${BLUE}Configuration avec les paramètres suivants :${NC}"
echo "  - Domaine: $DOMAIN"
echo "  - IP Master: $MASTER_IP"
echo "  - IP Worker: $WORKER_IP"
echo "  - IP Ingress: $INGRESS_IP"
echo ""

# 1. Configuration du fichier .vault_pass
setup_vault_password() {
    echo -e "${YELLOW}🔐 Configuration du mot de passe Ansible Vault...${NC}"
    
    echo "$VAULT_PASSWORD" > ansible/.vault_pass
    chmod 600 ansible/.vault_pass
    
    echo -e "${GREEN}✅ Fichier .vault_pass créé${NC}"
    echo -e "${RED}⚠️  IMPORTANT: Ajoutez ce mot de passe au secret GitHub 'ANSIBLE_VAULT_PASSWORD'${NC}"
    echo "   Mot de passe: $VAULT_PASSWORD"
    echo ""
}

# 2. Génération des clés SSH
generate_ssh_keys() {
    echo -e "${YELLOW}🔑 Génération des clés SSH...${NC}"
    
    if [ ! -f ~/.ssh/noah_pipeline ]; then
        ssh-keygen -t ed25519 -C "noah-pipeline@github-actions" -f ~/.ssh/noah_pipeline -N ""
        echo -e "${GREEN}✅ Clés SSH générées${NC}"
    else
        echo -e "${BLUE}ℹ️  Clés SSH déjà existantes${NC}"
    fi
    
    echo -e "${RED}⚠️  IMPORTANT: Configurez les secrets GitHub suivants :${NC}"
    echo ""
    echo -e "${YELLOW}SSH_PRIVATE_KEY:${NC}"
    cat ~/.ssh/noah_pipeline
    echo ""
    echo -e "${YELLOW}MASTER_HOST:${NC} $MASTER_IP"
    echo ""
    echo -e "${BLUE}💡 Déployez aussi la clé publique sur vos serveurs :${NC}"
    echo "ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@$MASTER_IP"
    echo "ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@$WORKER_IP"
    echo ""
}

# 3. Mise à jour de l'inventaire
update_inventory() {
    echo -e "${YELLOW}📝 Mise à jour de l'inventaire...${NC}"
    
    cat > ansible/inventory/mycluster/hosts.yaml << EOF
# Inventaire Kubespray pour cluster NOAH - Généré automatiquement
all:
  hosts:
    noah-master-1:
      ansible_host: $MASTER_IP
      ip: $MASTER_IP
      access_ip: $MASTER_IP
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/noah_pipeline
    noah-worker-1:
      ansible_host: $WORKER_IP
      ip: $WORKER_IP
      access_ip: $WORKER_IP
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/noah_pipeline

  children:
    kube_control_plane:
      hosts:
        noah-master-1:
    kube_node:
      hosts:
        noah-master-1:
        noah-worker-1:
    etcd:
      hosts:
        noah-master-1:
    k8s_cluster:
      children:
        kube_control_plane:
        kube_node:
    calico_rr:
      hosts: {}

  vars:
    # Configuration réseau
    kube_network_plugin: calico
    kube_pods_subnet: 10.233.64.0/18
    kube_service_addresses: 10.233.0.0/18
    
    # Configuration cluster
    cluster_name: noah-cluster
    kube_version: v1.28.2
    
    # Configuration DNS
    upstream_dns_servers:
      - 8.8.8.8
      - 8.8.4.4
    
    # Configuration ingress
    ingress_nginx_enabled: true
    ingress_nginx_host_network: true
    
    # Configuration monitoring
    metrics_server_enabled: true
EOF
    
    echo -e "${GREEN}✅ Inventaire mis à jour avec les IPs configurées${NC}"
}

# 4. Configuration des domaines
update_domains() {
    echo -e "${YELLOW}🌐 Configuration des domaines...${NC}"
    
    # Mise à jour du domaine dans values-prod.yaml
    sed -i "s/domain: noah\.local/domain: $DOMAIN/g" values/values-prod.yaml
    
    # Configuration du /etc/hosts pour domaines .local
    if [[ "$DOMAIN" == *.local ]]; then
        echo -e "${BLUE}📋 Configuration DNS locale requise :${NC}"
        echo "Ajoutez les lignes suivantes à votre /etc/hosts :"
        echo ""
        echo "$INGRESS_IP keycloak.$DOMAIN"
        echo "$INGRESS_IP gitlab.$DOMAIN"
        echo "$INGRESS_IP nextcloud.$DOMAIN"
        echo "$INGRESS_IP mattermost.$DOMAIN"
        echo "$INGRESS_IP grafana.$DOMAIN"
        echo ""
        
        # Optionnel : ajout automatique si l'utilisateur est root
        if [ "$EUID" -eq 0 ]; then
            echo -e "${YELLOW}🔧 Ajout automatique au /etc/hosts (mode root détecté)...${NC}"
            tee -a /etc/hosts << EOF
# Entrées NOAH ajoutées automatiquement
$INGRESS_IP keycloak.$DOMAIN
$INGRESS_IP gitlab.$DOMAIN
$INGRESS_IP nextcloud.$DOMAIN
$INGRESS_IP mattermost.$DOMAIN
$INGRESS_IP grafana.$DOMAIN
EOF
            echo -e "${GREEN}✅ Entrées DNS ajoutées au /etc/hosts${NC}"
        fi
    fi
    
    echo -e "${GREEN}✅ Configuration des domaines terminée${NC}"
}

# 5. Chiffrement du fichier secrets
encrypt_secrets() {
    echo -e "${YELLOW}🔒 Chiffrement du fichier secrets...${NC}"
    
    if [ -f ansible/vars/secrets.yml ]; then
        # Vérifier si le fichier est déjà chiffré
        if ! head -1 ansible/vars/secrets.yml | grep -q "ANSIBLE_VAULT"; then
            ansible-vault encrypt ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass
            echo -e "${GREEN}✅ Fichier secrets.yml chiffré${NC}"
        else
            echo -e "${BLUE}ℹ️  Fichier secrets.yml déjà chiffré${NC}"
        fi
    else
        echo -e "${RED}❌ Fichier secrets.yml non trouvé${NC}"
    fi
}

# 6. Test de la configuration
test_configuration() {
    echo -e "${YELLOW}🧪 Test de la configuration...${NC}"
    
    # Test de la syntaxe des playbooks
    echo "  - Test des playbooks Ansible..."
    for playbook in ansible/playbooks/*.yml; do
        if ansible-playbook --syntax-check "$playbook" >/dev/null 2>&1; then
            echo -e "    ${GREEN}✅ $(basename "$playbook")${NC}"
        else
            echo -e "    ${RED}❌ $(basename "$playbook")${NC}"
        fi
    done
    
    # Test de l'inventaire
    echo "  - Test de l'inventaire..."
    if ansible-inventory --list -i ansible/inventory/mycluster/hosts.yaml >/dev/null 2>&1; then
        echo -e "    ${GREEN}✅ Inventaire valide${NC}"
    else
        echo -e "    ${RED}❌ Erreur dans l'inventaire${NC}"
    fi
    
    # Test de connectivité (optionnel)
    echo "  - Test de connectivité SSH (optionnel)..."
    if timeout 5 ssh -o ConnectTimeout=5 -o BatchMode=yes -i ~/.ssh/noah_pipeline ubuntu@$MASTER_IP exit >/dev/null 2>&1; then
        echo -e "    ${GREEN}✅ Connexion SSH au master réussie${NC}"
    else
        echo -e "    ${YELLOW}⚠️  Connexion SSH au master échouée (normal si les serveurs ne sont pas encore configurés)${NC}"
    fi
}

# 7. Affichage du résumé
display_summary() {
    echo ""
    echo -e "${GREEN}🎉 Configuration automatique terminée !${NC}"
    echo "======================================="
    echo ""
    echo -e "${BLUE}📋 Résumé de la configuration :${NC}"
    echo "  - Domaine: $DOMAIN"
    echo "  - Master IP: $MASTER_IP"
    echo "  - Worker IP: $WORKER_IP"
    echo "  - Ingress IP: $INGRESS_IP"
    echo "  - Vault password: Configuré"
    echo "  - SSH keys: Générées"
    echo "  - Secrets: Chiffrés"
    echo ""
    echo -e "${YELLOW}🔧 Prochaines étapes :${NC}"
    echo "1. Configurez les secrets GitHub Actions avec les valeurs affichées ci-dessus"
    echo "2. Déployez les clés SSH sur vos serveurs"
    echo "3. Vérifiez la configuration réseau de vos serveurs"
    echo "4. Poussez les modifications sur la branche 'Ansible'"
    echo ""
    echo -e "${BLUE}🚀 Commandes de test :${NC}"
    echo "  # Tester la connectivité"
    echo "  ansible all -m ping -i ansible/inventory/mycluster/hosts.yaml"
    echo ""
    echo "  # Lancer le déploiement"
    echo "  git add . && git commit -m 'Configure pipeline' && git push origin Ansible"
    echo ""
    echo -e "${GREEN}✨ Le pipeline est prêt !${NC}"
}

# Menu interactif
interactive_setup() {
    echo -e "${BLUE}🤔 Voulez-vous personnaliser la configuration ? (y/N)${NC}"
    read -r customize
    
    if [[ $customize =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}📝 Configuration personnalisée :${NC}"
        
        read -p "Domaine (défaut: $DOMAIN): " input_domain
        DOMAIN=${input_domain:-$DOMAIN}
        
        read -p "IP du serveur master (défaut: $MASTER_IP): " input_master
        MASTER_IP=${input_master:-$MASTER_IP}
        
        read -p "IP du serveur worker (défaut: $WORKER_IP): " input_worker
        WORKER_IP=${input_worker:-$WORKER_IP}
        
        read -p "IP de l'ingress (défaut: $INGRESS_IP): " input_ingress
        INGRESS_IP=${input_ingress:-$INGRESS_IP}
        
        echo ""
        echo -e "${GREEN}✅ Configuration personnalisée enregistrée${NC}"
    fi
}

# Fonction principale
main() {
    echo -e "${BLUE}Mode de configuration : ${1:-interactif}${NC}"
    echo ""
    
    if [ "$1" != "--auto" ]; then
        interactive_setup
    fi
    
    setup_vault_password
    generate_ssh_keys
    update_inventory
    update_domains
    encrypt_secrets
    test_configuration
    display_summary
}

# Vérification des prérequis
check_requirements() {
    local missing_tools=()
    
    command -v ansible >/dev/null 2>&1 || missing_tools+=("ansible")
    command -v ssh-keygen >/dev/null 2>&1 || missing_tools+=("ssh-keygen")
    command -v git >/dev/null 2>&1 || missing_tools+=("git")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}❌ Outils manquants: ${missing_tools[*]}${NC}"
        echo "Installez-les avant de continuer."
        exit 1
    fi
}

# Point d'entrée
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    check_requirements
    main "$@"
fi
