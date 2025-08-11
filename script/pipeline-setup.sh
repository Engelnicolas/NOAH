#!/bin/bash

# Script intégré de configuration du pipeline CI/CD NOAH
# Combine l'initialisation et la configuration automatique

set -e

# Variables
DRY_RUN=false
KUBESPRAY_VENV=".venv-kubespray"

# Variables de configuration (modifiables)
DOMAIN="${DOMAIN:-noah.local}"
MASTER_IP="${MASTER_IP:-192.168.1.10}"
WORKER_IP="${WORKER_IP:-192.168.1.12}"
INGRESS_IP="${INGRESS_IP:-192.168.1.10}"
VAULT_PASSWORD="${VAULT_PASSWORD:-MYPASSWORD}"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Affichage de l'aide
show_help() {
    echo "🚀 Script de configuration du pipeline CI/CD NOAH"
    echo ""
    echo "Usage: $0 [OPTIONS] [MODE]"
    echo ""
    echo "MODES:"
    echo "  setup       Initialisation complète (défaut)"
    echo "  configure   Configuration automatique"
    echo "  full        Les deux étapes"
    echo ""
    echo "OPTIONS:"
    echo "  --dry-run        Mode simulation"
    echo "  --auto          Mode automatique (sans interaction)"
    echo "  --domain=VALUE  Domaine personnalisé"
    echo "  --master=IP     IP du serveur master"
    echo "  --worker=IP     IP du serveur worker"
    echo "  --ingress=IP    IP de l'ingress"
    echo "  -h, --help      Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 full --auto"
    echo "  $0 configure --domain=example.com --master=10.0.1.5"
    echo "  $0 setup --dry-run"
}

# Parse arguments
parse_arguments() {
    MODE="setup"
    AUTO_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --auto)
                AUTO_MODE=true
                shift
                ;;
            --domain=*)
                DOMAIN="${1#*=}"
                shift
                ;;
            --master=*)
                MASTER_IP="${1#*=}"
                shift
                ;;
            --worker=*)
                WORKER_IP="${1#*=}"
                shift
                ;;
            --ingress=*)
                INGRESS_IP="${1#*=}"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            setup|configure|full)
                MODE="$1"
                shift
                ;;
            *)
                echo "Option inconnue: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Vérification des prérequis
check_requirements() {
    echo -e "${YELLOW}📋 Vérification des prérequis...${NC}"
    
    local missing_tools=()
    
    # Vérifier les outils essentiels
    command -v ansible >/dev/null 2>&1 || missing_tools+=("ansible")
    command -v git >/dev/null 2>&1 || missing_tools+=("git")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    command -v ssh-keygen >/dev/null 2>&1 || missing_tools+=("ssh-keygen")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}❌ Outils manquants: ${missing_tools[*]}${NC}"
        echo "Installez-les avant de continuer."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Tous les prérequis sont satisfaits${NC}"
}

# Créer un venv Python dédié pour Kubespray
create_kubespray_venv() {
    echo -e "${YELLOW}🐍 Préparation de l'environnement Python dédié Kubespray ($KUBESPRAY_VENV)...${NC}"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Actions qui seraient exécutées:"
        echo "   - python3 -m venv $KUBESPRAY_VENV"
        echo "   - $KUBESPRAY_VENV/bin/pip install --upgrade pip wheel setuptools"
        return 0
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}❌ Python3 introuvable${NC}"
        exit 1
    fi

    # Créer le venv s'il n'existe pas
    if [[ ! -d "$KUBESPRAY_VENV" ]]; then
        python3 -m venv "$KUBESPRAY_VENV"
    fi

    # Mettre à jour pip/outils de build dans ce venv
    "$KUBESPRAY_VENV/bin/pip" install --upgrade pip wheel setuptools >/dev/null 2>&1 || true
    echo -e "${GREEN}✅ Environnement Kubespray prêt: $KUBESPRAY_VENV${NC}"
    echo -e "${BLUE}ℹ️  Pour l'utiliser manuellement: source $KUBESPRAY_VENV/bin/activate${NC}"
}

# Installation des collections Ansible
install_ansible_collections() {
    echo -e "${YELLOW}📦 Installation des collections Ansible...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Action qui serait exécutée:"
        echo "   - ansible-galaxy collection install -r ansible/requirements.yml --force"
        echo -e "${GREEN}✅ [DRY-RUN] Collections Ansible seraient installées${NC}"
    else
        ansible-galaxy collection install -r ansible/requirements.yml --force
        echo -e "${GREEN}✅ Collections Ansible installées${NC}"
    fi
}

# Clonage de Kubespray
setup_kubespray() {
    echo -e "${YELLOW}⚙️  Configuration de Kubespray...${NC}"
    
    local kubespray_dir="ansible/kubespray"
    local requirements_file="$kubespray_dir/requirements.txt"
    
    # Test de la condition
    echo -e "${BLUE}🔍 Vérification de la condition Kubespray:${NC}"
    echo "   - Répertoire .git existe: $([ -d "$kubespray_dir/.git" ] && echo "✅ OUI" || echo "❌ NON")"
    echo "   - Fichier requirements.txt existe et non vide: $([ -s "$requirements_file" ] && echo "✅ OUI" || echo "❌ NON")"
    
    if [ ! -d "$kubespray_dir/.git" ] || [ ! -s "$requirements_file" ]; then
        echo -e "${YELLOW}📥 Clonage de Kubespray requis...${NC}"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "🧪 [DRY-RUN] Actions qui seraient exécutées:"
            echo "   - rm -rf $kubespray_dir"
            echo "   - git clone https://github.com/kubernetes-sigs/kubespray.git $kubespray_dir"
            echo "   - cd $kubespray_dir && git checkout v2.23.1 && cd ../.."
            echo -e "${GREEN}✅ [DRY-RUN] Kubespray serait cloné${NC}"
        else
            rm -rf "$kubespray_dir"
            git clone https://github.com/kubernetes-sigs/kubespray.git "$kubespray_dir"
            cd "$kubespray_dir"
            git checkout v2.23.1
            cd ../..
            echo -e "${GREEN}✅ Kubespray cloné${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️  Kubespray déjà présent et valide${NC}"
    fi
    
    # Installation des dépendances Kubespray via un venv dédié
    if [ -f "$requirements_file" ] || [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}📦 Installation des dépendances Kubespray (environnement isolé)...${NC}"

        # Créer/mettre à jour le venv dédié
        create_kubespray_venv

        if [[ "$DRY_RUN" == "true" ]]; then
            echo "🧪 [DRY-RUN] Action qui serait exécutée:"
            echo "   - $KUBESPRAY_VENV/bin/pip install -r $requirements_file"
            echo -e "${GREEN}✅ [DRY-RUN] Dépendances Kubespray seraient installées dans $KUBESPRAY_VENV${NC}"
        else
            "$KUBESPRAY_VENV/bin/pip" install -r "$requirements_file"
            echo -e "${GREEN}✅ Dépendances Kubespray installées dans $KUBESPRAY_VENV${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Fichier requirements.txt de Kubespray non trouvé${NC}"
    fi
}

# Création des répertoires nécessaires
create_directories() {
    echo -e "${YELLOW}📁 Création des répertoires...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Répertoires qui seraient créés:"
        echo "   - ansible/kubeconfig"
        echo "   - ansible/reports"
        echo "   - helm/noah-chart/templates"
    else
        mkdir -p ansible/kubeconfig
        mkdir -p ansible/reports
        mkdir -p helm/noah-chart/templates
    fi
    
    echo -e "${GREEN}✅ Répertoires créés${NC}"
}

# Configuration du fichier .vault_pass
setup_vault_password() {
    echo -e "${YELLOW}🔐 Configuration du mot de passe Ansible Vault...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Action qui serait exécutée:"
        echo "   - echo '$VAULT_PASSWORD' > ansible/.vault_pass"
        echo "   - chmod 600 ansible/.vault_pass"
    else
        echo "$VAULT_PASSWORD" > ansible/.vault_pass
        chmod 600 ansible/.vault_pass
    fi
    
    echo -e "${GREEN}✅ Fichier .vault_pass créé${NC}"
    echo -e "${RED}⚠️  IMPORTANT: Ajoutez ce mot de passe au secret GitHub 'ANSIBLE_VAULT_PASSWORD'${NC}"
    echo "   Mot de passe: $VAULT_PASSWORD"
    echo ""
}

# Génération des clés SSH
generate_ssh_keys() {
    echo -e "${YELLOW}🔑 Génération des clés SSH...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Action qui serait exécutée:"
        echo "   - ssh-keygen -t ed25519 -C 'noah-pipeline@github-actions' -f ~/.ssh/noah_pipeline -N ''"
        echo -e "${GREEN}✅ [DRY-RUN] Clés SSH seraient générées${NC}"
        return
    fi
    
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

# Mise à jour de l'inventaire
update_inventory() {
    echo -e "${YELLOW}📝 Mise à jour de l'inventaire...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Inventaire qui serait créé avec:"
        echo "   - Master IP: $MASTER_IP"
        echo "   - Worker IP: $WORKER_IP"
        echo -e "${GREEN}✅ [DRY-RUN] Inventaire serait mis à jour${NC}"
        return
    fi
    
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

# Configuration des domaines
update_domains() {
    echo -e "${YELLOW}🌐 Configuration des domaines...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Action qui serait exécutée:"
        echo "   - Mise à jour du domaine dans values/values-prod.yaml: $DOMAIN"
        if [[ "$DOMAIN" == *.local ]]; then
            echo "   - Configuration DNS locale pour domaine .local"
        fi
        echo -e "${GREEN}✅ [DRY-RUN] Domaines seraient configurés${NC}"
        return
    fi
    
    # Mise à jour du domaine dans values-prod.yaml si le fichier existe
    if [ -f "values/values-prod.yaml" ]; then
        sed -i "s/domain: noah\.local/domain: $DOMAIN/g" values/values-prod.yaml
    fi
    
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

# Configuration des secrets
setup_secrets() {
    echo -e "${YELLOW}🔐 Configuration des secrets...${NC}"
    
    if [ ! -f "ansible/.vault_pass" ]; then
        echo -e "${YELLOW}⚠️  Créez le fichier ansible/.vault_pass avec votre mot de passe Vault${NC}"
        echo "    echo 'votre_mot_de_passe_vault' > ansible/.vault_pass"
        echo "    chmod 600 ansible/.vault_pass"
    fi
    
    # Vérifier/Créer .sops.yaml minimal si absent
    if [ ! -f ".sops.yaml" ]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "🧪 [DRY-RUN] Création d'un .sops.yaml minimal (avec clé Age placeholder)"
        else
            cat > .sops.yaml << 'EOF'
# Configuration SOPS minimale générée automatiquement
# Remplacez AGE-PLACEHOLDER-PUBLIC-KEY par votre clé publique Age
# Générer une paire: age-keygen -o ~/.config/sops/age/keys.txt
# Puis récupérer la clé publique: grep -m1 '^# public key:' ~/.config/sops/age/keys.txt | awk '{print $4}'
creation_rules:
  - path_regex: ^ansible/vars/secrets\.yml$
    age: ["AGE-PLACEHOLDER-PUBLIC-KEY"]
    encrypted_regex: '^(data|stringData|vault_.*)$'
EOF
            echo -e "${GREEN}✅ Fichier .sops.yaml minimal créé (à personnaliser)${NC}"
        fi
    fi

    echo -e "${GREEN}✅ Configuration des secrets terminée${NC}"
}

# Chiffrement du fichier secrets
encrypt_secrets() {
    echo -e "${YELLOW}🔒 Chiffrement du fichier secrets...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Action qui serait exécutée:"
        echo "   - ansible-vault encrypt ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass"
        echo -e "${GREEN}✅ [DRY-RUN] Fichier secrets.yml serait chiffré${NC}"
        return
    fi
    
    if [ -f ansible/vars/secrets.yml ]; then
        # Vérifier si le fichier est déjà chiffré
        if ! head -1 ansible/vars/secrets.yml | grep -q "ANSIBLE_VAULT"; then
            ansible-vault encrypt ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass
            echo -e "${GREEN}✅ Fichier secrets.yml chiffré${NC}"
        else
            echo -e "${BLUE}ℹ️  Fichier secrets.yml déjà chiffré${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Fichier secrets.yml non trouvé${NC}"
    fi
}

# Validation de la configuration
validate_config() {
    echo -e "${YELLOW}🔍 Validation de la configuration...${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "🧪 [DRY-RUN] Validations qui seraient effectuées:"
        echo "   - Test de syntaxe des playbooks Ansible"
        echo "   - Validation de l'inventaire"
        echo "   - Test de connectivité SSH (optionnel)"
        echo -e "${GREEN}✅ [DRY-RUN] Validation serait effectuée${NC}"
        return
    fi
    
    # Vérifier la syntaxe des playbooks
    for playbook in ansible/playbooks/*.yml; do
        if [ -f "$playbook" ]; then
            echo "  Validation de $(basename "$playbook")..."
            if ansible-playbook --syntax-check "$playbook" >/dev/null 2>&1; then
                echo -e "    ${GREEN}✅ $(basename "$playbook")${NC}"
            else
                echo -e "    ${RED}❌ $(basename "$playbook")${NC}"
            fi
        fi
    done
    
    # Vérifier l'inventaire
    if [ -f "ansible/inventory/mycluster/hosts.yaml" ]; then
        echo "  Validation de l'inventaire..."
        if ansible-inventory --list -i ansible/inventory/mycluster/hosts.yaml >/dev/null 2>&1; then
            echo -e "    ${GREEN}✅ Inventaire valide${NC}"
        else
            echo -e "    ${RED}❌ Erreur dans l'inventaire${NC}"
        fi
    fi
    
    # Test de connectivité (optionnel)
    echo "  Test de connectivité SSH (optionnel)..."
    if timeout 5 ssh -o ConnectTimeout=5 -o BatchMode=yes -i ~/.ssh/noah_pipeline ubuntu@$MASTER_IP exit >/dev/null 2>&1; then
        echo -e "    ${GREEN}✅ Connexion SSH au master réussie${NC}"
    else
        echo -e "    ${YELLOW}⚠️  Connexion SSH au master échouée (normal si les serveurs ne sont pas encore configurés)${NC}"
    fi
    
    echo -e "${GREEN}✅ Validation terminée${NC}"
}

# Menu interactif
interactive_setup() {
    if [[ "$AUTO_MODE" == "true" ]]; then
        return
    fi
    
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

# Affichage des informations finales
display_summary() {
    echo ""
    echo -e "${GREEN}🎉 Configuration terminée !${NC}"
    echo "=============================="
    echo ""
    echo -e "${BLUE}📋 Résumé de la configuration :${NC}"
    echo "  - Domaine: $DOMAIN"
    echo "  - Master IP: $MASTER_IP"
    echo "  - Worker IP: $WORKER_IP"
    echo "  - Ingress IP: $INGRESS_IP"
    echo "  - Vault password: Configuré"
    echo "  - SSH keys: Générées"
    echo "  - Secrets: Configurés"
    echo ""
    echo -e "${YELLOW}🔧 Prochaines étapes :${NC}"
    echo "1. Configurez les secrets GitHub Actions avec les valeurs affichées ci-dessus"
    echo "2. Déployez les clés SSH sur vos serveurs"
    echo "3. Vérifiez la configuration réseau de vos serveurs"
    echo "4. Poussez les modifications sur la branche 'Ansible' ou 'main'"
    echo ""
    echo -e "${BLUE}🚀 Commandes de test :${NC}"
    echo "  # Tester la connectivité"
    echo "  ansible all -m ping -i ansible/inventory/mycluster/hosts.yaml"
    echo ""
    echo "  # Lancer le déploiement"
    echo "  git add . && git commit -m 'Configure pipeline' && git push origin main"
    echo ""
    echo -e "${GREEN}✨ Le pipeline est prêt !${NC}"
}

# Fonction d'initialisation (ex setup-pipeline.sh)
run_setup() {
    echo -e "${GREEN}🚀 Initialisation du pipeline CI/CD NOAH${NC}"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}🧪 MODE DRY-RUN - Aucune modification ne sera effectuée${NC}"
    fi
    echo "========================================"
    
    check_requirements
    create_directories
    install_ansible_collections
    setup_kubespray
    setup_secrets
}

# Fonction de configuration (ex configure-pipeline.sh)
run_configure() {
    echo -e "${GREEN}🔧 Configuration automatique du pipeline NOAH${NC}"
    echo "=============================================="
    
    echo -e "${BLUE}Configuration avec les paramètres suivants :${NC}"
    echo "  - Domaine: $DOMAIN"
    echo "  - IP Master: $MASTER_IP"
    echo "  - IP Worker: $WORKER_IP"
    echo "  - IP Ingress: $INGRESS_IP"
    echo ""
    
    interactive_setup
    setup_vault_password
    generate_ssh_keys
    update_inventory
    update_domains
    encrypt_secrets
}

# Fonction principale
main() {
    case $MODE in
        "setup")
            run_setup
            validate_config
            display_summary
            ;;
        "configure")
            check_requirements
            run_configure
            validate_config
            display_summary
            ;;
        "full")
            run_setup
            run_configure
            validate_config
            display_summary
            ;;
        *)
            echo -e "${RED}Mode invalide: $MODE${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Point d'entrée
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    parse_arguments "$@"
    main
fi
