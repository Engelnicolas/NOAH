#!/bin/bash
# NOAH CLI - Interface pour les pipelines CI/CD modernes

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Variables globales
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NOAH_VERSION="0.2.1"
PIPELINE_MODE="modern"
INFRASTRUCTURE_TYPE="kubernetes"  # Par défaut: kubernetes, options: kubernetes, docker

# Fonctions d'affichage
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Banner NOAH
show_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                 🚀 NOAH CLI v${NOAH_VERSION}                 ║"
    echo "║              Network Operations & Automation Hub              ║"
    echo "║                   Pipeline CI/CD Moderne                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Vérification de l'environnement
check_environment() {
    # Vérifier qu'on est dans le bon répertoire
    if [[ ! -f "$SCRIPT_DIR/ansible/ansible.cfg" ]] || [[ ! -d "$SCRIPT_DIR/.github/workflows" ]]; then
        error "Ce script doit être exécuté depuis le répertoire racine du projet NOAH"
        error "Structure attendue: NOAH/noah (ce script), NOAH/ansible/, NOAH/.github/workflows/"
        error "Répertoire actuel: $SCRIPT_DIR"
        exit 1
    fi
    
    cd "$SCRIPT_DIR" || {
        error "Impossible de se déplacer vers le répertoire racine: $SCRIPT_DIR"
        exit 1
    }
    
    success "Environnement NOAH validé"
}

# Vérifier les prérequis
check_prerequisites() {
    step "Vérification des prérequis..."
    
    local missing_tools=()
    
    # Vérification de Python (version la plus récente)
    step "Vérification de l'installation Python..."
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local python_major=$(echo "$python_version" | cut -d'.' -f1)
        local python_minor=$(echo "$python_version" | cut -d'.' -f2)
        
        if [[ "$python_major" -ge 3 ]] && [[ "$python_minor" -ge 8 ]]; then
            success "Python $python_version détecté (version compatible)"
        else
            error "Python $python_version détecté - Version 3.8+ requise"
            info "Veuillez mettre à jour Python vers la dernière version"
            exit 1
        fi
    else
        error "Python 3 n'est pas installé"
        info "Installation requise: sudo apt update && sudo apt install -y python3 python3-dev"
        exit 1
    fi
    
    # Vérification de pip
    step "Vérification de l'installation pip..."
    if command -v pip3 >/dev/null 2>&1; then
        local pip_version=$(pip3 --version 2>&1 | cut -d' ' -f2)
        success "pip $pip_version détecté"
        
        # Vérifier si pip est à jour
        info "Vérification des mises à jour pip..."
        pip3 install --upgrade pip >/dev/null 2>&1 || warning "Impossible de mettre à jour pip"
    else
        error "pip3 n'est pas installé"
        info "Installation requise: sudo apt install -y python3-pip"
        exit 1
    fi
    
    # Outils essentiels
    command -v git >/dev/null 2>&1 || missing_tools+=("git")
    command -v ansible >/dev/null 2>&1 || missing_tools+=("ansible")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm (optionnel pour certaines commandes)")
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl (optionnel pour certaines commandes)")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        warning "Outils manquants: ${missing_tools[*]}"
        info "Certaines fonctionnalités peuvent ne pas être disponibles"
        
        # Installation automatique d'Ansible si manquant
        if [[ " ${missing_tools[*]} " =~ " ansible " ]]; then
            info "Tentative d'installation d'Ansible..."
            if command -v pip3 >/dev/null 2>&1; then
                pip3 install ansible ansible-core
                success "Ansible installé via pip3"
            elif command -v apt >/dev/null 2>&1; then
                sudo apt update && sudo apt install -y ansible
                success "Ansible installé via apt"
            else
                error "Impossible d'installer Ansible automatiquement"
                echo "Veuillez l'installer manuellement: pip3 install ansible"
            fi
        fi
    else
        success "Tous les prérequis sont satisfaits"
    fi
}

# Configuration du type d'infrastructure
configure_infrastructure_type() {
    echo -e "${BOLD}Configuration du type d'infrastructure${NC}"
    echo ""
    echo "Choisissez le type d'infrastructure cible pour le déploiement NOAH :"
    echo ""
    echo -e "${CYAN}1)${NC} Kubernetes Cluster ${GREEN}(recommandé - par défaut)${NC}"
    echo "   - Déploiement dans un cluster Kubernetes existant"
    echo "   - Support complet de toutes les fonctionnalités NOAH"
    echo "   - Haute disponibilité et scalabilité"
    echo ""
    echo -e "${CYAN}2)${NC} Docker Compose ${YELLOW}(développement)${NC}"
    echo "   - Déploiement local avec Docker Compose"
    echo "   - Idéal pour le développement et les tests"
    echo "   - Fonctionnalités limitées"
    echo ""
    
    while true; do
        echo -n "Votre choix [1-2] (défaut: 1): "
        read -r choice
        
        case ${choice:-1} in
        1)
            INFRASTRUCTURE_TYPE="kubernetes"
            success "Infrastructure sélectionnée: Kubernetes Cluster"
            break
            ;;
        2)
            INFRASTRUCTURE_TYPE="docker"
            success "Infrastructure sélectionnée: Docker Compose"
            warning "Mode développement - Fonctionnalités limitées"
            break
            ;;
        *)
            error "Choix invalide. Veuillez sélectionner 1 ou 2."
            ;;
        esac
    done
    
    # Sauvegarder le choix dans un fichier de configuration
    echo "INFRASTRUCTURE_TYPE=$INFRASTRUCTURE_TYPE" > "$SCRIPT_DIR/.noah_config"
    info "Configuration sauvegardée dans .noah_config"
}

# Charger la configuration si elle existe
load_infrastructure_config() {
    if [[ -f "$SCRIPT_DIR/.noah_config" ]]; then
        source "$SCRIPT_DIR/.noah_config"
    fi
}

# Fonction d'aide principale
show_help() {
    echo -e "${BOLD}NOAH CLI - Network Operations & Automation Hub${NC}"
    echo ""
    echo -e "${YELLOW}COMMANDES PRINCIPALES:${NC}"
    echo ""
    echo -e "${CYAN}🚀 Déploiement${NC}"
    echo "  init              Initialiser l'environnement de déploiement"
    echo "  init-pipeline     Initialiser uniquement le pipeline CI/CD"
    echo "  configure         Configurer les paramètres de déploiement"
    echo "  configure-pipeline Configurer uniquement le pipeline CI/CD"
    echo "  setup-pipeline    Configuration complète du pipeline (init + configure)"
    echo "  deploy            Déployer la plateforme NOAH complète"
    echo "  status            Vérifier l'état du déploiement"
    echo "  logs              Afficher les logs de déploiement"
    echo ""
    echo -e "${CYAN}🔧 Gestion${NC}"
    echo "  start             Démarrer les services NOAH"
    echo "  stop              Arrêter les services NOAH"
    echo "  restart           Redémarrer les services NOAH"
    echo "  update            Mettre à jour les applications"
    echo "  backup            Sauvegarder les données"
    echo "  restore           Restaurer depuis une sauvegarde"
    echo ""
    echo -e "${CYAN}🔍 Monitoring${NC}"
    echo "  health            Vérifier la santé du système"
    echo "  metrics           Afficher les métriques système"
    echo "  alerts            Gérer les alertes"
    echo "  dashboard         Ouvrir le tableau de bord Grafana"
    echo ""
    echo -e "${CYAN}⚙️  Configuration${NC}"
    echo "  config list       Lister les configurations"
    echo "  config set        Définir une configuration"
    echo "  config get        Obtenir une configuration"
    echo "  infrastructure    Configurer le type d'infrastructure"
    echo "  secrets           Gérer les secrets"
    echo "  secrets generate  Générer de nouveaux secrets"
    echo "  secrets validate  Valider les secrets"
    echo "  secrets encrypt   Chiffrer le fichier secrets"
    echo "  secrets decrypt   Déchiffrer le fichier secrets"
    echo ""
    echo -e "${CYAN}🧪 Développement${NC}"
    echo "  test              Lancer les tests"
    echo "  validate          Valider la configuration"
    echo "  lint              Vérifier la syntaxe des fichiers"
    echo "  debug             Mode debug interactif"
    echo ""
    echo -e "${YELLOW}OPTIONS GLOBALES:${NC}"
    echo "  -h, --help        Afficher cette aide"
    echo "  -v, --verbose     Mode verbeux"
    echo "  -q, --quiet       Mode silencieux"
    echo "  --version         Afficher la version"
    echo "  --dry-run         Simulation sans exécution"
    echo ""
    echo -e "${YELLOW}EXEMPLES:${NC}"
    echo "  noah init                     # Initialiser l'environnement"
    echo "  noah setup-pipeline --auto    # Configuration complète du pipeline" 
    echo "  noah infrastructure           # Configurer le type d'infrastructure"
    echo "  noah configure --auto         # Configuration automatique"
    echo "  noah deploy --profile prod    # Déploiement en production"
    echo "  noah status --all             # État complet du système"
    echo "  noah configure-pipeline --dry-run  # Test de configuration pipeline"
    echo ""
    echo -e "${BLUE}Pour plus d'informations sur une commande:${NC}"
    echo "  noah <commande> --help"
    echo ""
}

# ===================================================================
# PIPELINE SETUP FUNCTIONS (intégré de script/pipeline-setup.sh)
# ===================================================================

# Variables de configuration pipeline
DOMAIN="${DOMAIN:-noah.local}"
MASTER_IP="${MASTER_IP:-192.168.1.10}"
WORKER_IP="${WORKER_IP:-192.168.1.12}"
INGRESS_IP="${INGRESS_IP:-192.168.1.10}"
VAULT_PASSWORD="${VAULT_PASSWORD:-MYPASSWORD}"
KUBESPRAY_VENV=".venv-kubespray"

# Vérification des prérequis pipeline
check_pipeline_requirements() {
    echo -e "${YELLOW}🔍 Vérification des prérequis...${NC}"
    
    local missing_tools=()
    
    for tool in python3 pip git ansible ansible-galaxy ssh-keygen; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Outils manquants: ${missing_tools[*]}"
        info "Installation requise avant de continuer"
        exit 1
    fi
    
    success "Tous les prérequis sont satisfaits"
}

# Configuration interactive
interactive_pipeline_setup() {
    if [[ "${AUTO_MODE:-false}" == "true" ]]; then
        info "Mode automatique activé - utilisation des valeurs par défaut"
        return
    fi
    
    echo -e "${YELLOW}🔧 Configuration interactive du pipeline${NC}"
    echo "Appuyez sur Entrée pour garder les valeurs par défaut"
    echo ""
    
    read -p "Domaine principal [$DOMAIN]: " input_domain
    DOMAIN="${input_domain:-$DOMAIN}"
    
    read -p "IP du serveur master [$MASTER_IP]: " input_master
    MASTER_IP="${input_master:-$MASTER_IP}"
    
    read -p "IP du serveur worker [$WORKER_IP]: " input_worker
    WORKER_IP="${input_worker:-$WORKER_IP}"
    
    read -p "IP de l'ingress [$INGRESS_IP]: " input_ingress
    INGRESS_IP="${input_ingress:-$INGRESS_IP}"
    
    echo ""
    echo -e "${GREEN}Configuration retenue:${NC}"
    echo "  Domaine: $DOMAIN"
    echo "  Master: $MASTER_IP"
    echo "  Worker: $WORKER_IP"
    echo "  Ingress: $INGRESS_IP"
    echo ""
}

# Création du venv Kubespray
create_kubespray_venv() {
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Création du venv Kubespray: $KUBESPRAY_VENV"
        return
    fi
    
    if [ ! -d "$KUBESPRAY_VENV" ]; then
        echo -e "${YELLOW}🐍 Création de l'environnement virtuel Kubespray...${NC}"
        python3 -m venv "$KUBESPRAY_VENV"
        success "Environnement virtuel créé: $KUBESPRAY_VENV"
    fi
    
    source "$KUBESPRAY_VENV/bin/activate"
    pip install --upgrade pip wheel
    echo -e "${GREEN}✅ Environnement virtuel activé${NC}"
}

# Installation des collections Ansible
install_ansible_collections() {
    echo -e "${YELLOW}📦 Installation des collections Ansible...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Installation des collections Ansible"
        echo -e "${GREEN}✅ [DRY-RUN] Collections seraient installées${NC}"
        return
    fi
    
    ansible-galaxy collection install -r ansible/requirements.yml --force
    echo -e "${GREEN}✅ Collections Ansible installées${NC}"
}

# Configuration de Kubespray
setup_kubespray() {
    echo -e "${YELLOW}⚙️  Configuration de Kubespray...${NC}"
    
    local kubespray_dir="ansible/kubespray"
    local requirements_file="$kubespray_dir/requirements.txt"
    
    if [ ! -d "$kubespray_dir/.git" ] || [ ! -s "$requirements_file" ]; then
        echo -e "${YELLOW}📥 Clonage de Kubespray...${NC}"
        
        if [[ "${DRY_RUN:-false}" == "true" ]]; then
            echo "🧪 [DRY-RUN] Clonage de Kubespray"
            echo -e "${GREEN}✅ [DRY-RUN] Kubespray serait cloné${NC}"
            return
        fi
        
        rm -rf "$kubespray_dir"
        git clone https://github.com/kubernetes-sigs/kubespray.git "$kubespray_dir"
        cd "$kubespray_dir"
        git checkout v2.23.1
        cd ../..
        echo -e "${GREEN}✅ Kubespray cloné${NC}"
    else
        echo -e "${BLUE}ℹ️  Kubespray déjà présent${NC}"
    fi
    
    # Installation des dépendances Kubespray
    if [ -f "$requirements_file" ] || [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo -e "${YELLOW}📦 Installation des dépendances Kubespray...${NC}"
        
        create_kubespray_venv
        
        if [[ "${DRY_RUN:-false}" == "true" ]]; then
            echo "🧪 [DRY-RUN] Installation des dépendances Kubespray"
        else
            pip install -r "$requirements_file"
        fi
        
        echo -e "${GREEN}✅ Dépendances Kubespray installées${NC}"
    fi
}

# Configuration du mot de passe Vault
setup_vault_password() {
    echo -e "${YELLOW}🔐 Configuration du mot de passe Ansible Vault...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Configuration du mot de passe Vault"
        echo -e "${GREEN}✅ [DRY-RUN] Mot de passe Vault configuré${NC}"
        return
    fi
    
    if [ ! -f "ansible/.vault_pass" ]; then
        echo "$VAULT_PASSWORD" > ansible/.vault_pass
        chmod 600 ansible/.vault_pass
        echo -e "${GREEN}✅ Mot de passe Vault configuré${NC}"
    else
        echo -e "${BLUE}ℹ️  Mot de passe Vault déjà configuré${NC}"
    fi
}

# Génération des clés SSH
generate_ssh_keys() {
    echo -e "${YELLOW}🔑 Génération des clés SSH...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Génération des clés SSH"
        echo -e "${GREEN}✅ [DRY-RUN] Clés SSH seraient générées${NC}"
        return
    fi
    
    if [ ! -f ~/.ssh/noah_pipeline ]; then
        ssh-keygen -t ed25519 -C "noah-pipeline@github-actions" -f ~/.ssh/noah_pipeline -N ""
        echo -e "${GREEN}✅ Clés SSH générées${NC}"
    else
        echo -e "${BLUE}ℹ️  Clés SSH déjà existantes${NC}"
    fi
    
    echo -e "${RED}⚠️  IMPORTANT: Configurez les secrets GitHub:${NC}"
    echo ""
    echo -e "${YELLOW}SSH_PRIVATE_KEY:${NC}"
    cat ~/.ssh/noah_pipeline
    echo ""
    echo -e "${YELLOW}MASTER_HOST:${NC} $MASTER_IP"
    echo ""
}

# Mise à jour de l'inventaire
update_inventory() {
    echo -e "${YELLOW}📝 Mise à jour de l'inventaire...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Mise à jour de l'inventaire"
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
    noah-worker-1:
      ansible_host: $WORKER_IP
      ip: $WORKER_IP
      access_ip: $WORKER_IP
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
EOF
    
    echo -e "${GREEN}✅ Inventaire mis à jour${NC}"
}

# Mise à jour des domaines
update_domains() {
    echo -e "${YELLOW}🌐 Mise à jour des domaines...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Mise à jour des domaines"
        echo -e "${GREEN}✅ [DRY-RUN] Domaines seraient mis à jour${NC}"
        return
    fi
    
    local config_file="ansible/vars/global.yml"
    
    if [ -f "$config_file" ]; then
        sed -i "s/domain_name:.*/domain_name: \"$DOMAIN\"/" "$config_file"
        sed -i "s/ingress_ip:.*/ingress_ip: \"$INGRESS_IP\"/" "$config_file"
        echo -e "${GREEN}✅ Configuration des domaines mise à jour${NC}"
    else
        warning "Fichier de configuration non trouvé: $config_file"
    fi
}

# Chiffrement des secrets
encrypt_secrets() {
    echo -e "${YELLOW}🔐 Chiffrement des secrets...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Chiffrement des secrets"
        echo -e "${GREEN}✅ [DRY-RUN] Secrets seraient chiffrés${NC}"
        return
    fi
    
    if [ -f "ansible/vars/secrets.yml" ]; then
        if ! file ansible/vars/secrets.yml | grep -q "Ansible Vault"; then
            ansible-vault encrypt ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass
            echo -e "${GREEN}✅ Fichier secrets.yml chiffré${NC}"
        else
            echo -e "${BLUE}ℹ️  Fichier secrets.yml déjà chiffré${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Fichier secrets.yml non trouvé${NC}"
    fi
}

# Validation de la configuration pipeline
validate_pipeline_config() {
    echo -e "${YELLOW}🔍 Validation de la configuration...${NC}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        echo "🧪 [DRY-RUN] Validation de la configuration"
        echo -e "${GREEN}✅ [DRY-RUN] Validation effectuée${NC}"
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
}

# Affichage du résumé
display_pipeline_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}✅ Configuration du pipeline terminée${NC}"
    echo "==========================================="
    echo ""
    echo -e "${YELLOW}Configuration:${NC}"
    echo "  • Domaine: $DOMAIN"
    echo "  • Master: $MASTER_IP"
    echo "  • Worker: $WORKER_IP"
    echo "  • Ingress: $INGRESS_IP"
    echo ""
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo "  1. Configurer les secrets GitHub Actions"
    echo "  2. Déployer les clés SSH sur les serveurs"
    echo "  3. Lancer le déploiement avec: noah deploy"
    echo ""
}

# ===================================================================
# COMMANDES PRINCIPALES NOAH
# ===================================================================

# Initialisation de l'environnement
cmd_init() {
    step "Initialisation de l'environnement NOAH..."
    
    # Charger la configuration existante
    load_infrastructure_config
    
    # Vérifier si déjà initialisé
    if [[ -f "ansible/.vault_pass" ]] && [[ -f "ansible/inventory/mycluster/hosts.yaml" ]]; then
        warning "Environnement déjà initialisé"
        echo "Voulez-vous réinitialiser ? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            info "Initialisation annulée"
            return 0
        fi
    fi
    
    # Configuration du type d'infrastructure si pas encore défini
    if [[ ! -f "$SCRIPT_DIR/.noah_config" ]]; then
        configure_infrastructure_type
        echo ""
    fi
    
    # Lancer l'initialisation du pipeline intégrée
    info "Initialisation du pipeline NOAH..."
    cmd_init_pipeline "$@"
    
    success "Initialisation terminée"
    info "Infrastructure configurée: $INFRASTRUCTURE_TYPE"
    info "Prochaine étape: noah configure"
}

# Configuration
cmd_configure() {
    step "Configuration de l'environnement NOAH..."
    
    local auto_mode=false
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --auto)
            auto_mode=true
            shift
            ;;
        --help)
            echo "Usage: noah configure [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --auto    Configuration automatique avec valeurs par défaut"
            echo "  --help    Afficher cette aide"
            return 0
            ;;
        *)
            warning "Option inconnue: $1"
            shift
            ;;
        esac
    done
    
    # Lancer le script de configuration
    if [[ -f "script/configure-pipeline.sh" ]]; then
        if [[ "$auto_mode" == "true" ]]; then
            info "Configuration automatique..."
            ./script/configure-pipeline.sh --auto
        else
            info "Configuration interactive..."
            ./script/configure-pipeline.sh
        fi
    else
        error "Script de configuration non trouvé: script/configure-pipeline.sh"
        exit 1
    fi
    
    success "Configuration terminée"
    info "Prochaine étape: noah deploy"
}

# Déploiement
cmd_deploy() {
    step "Déploiement de la plateforme NOAH..."
    
    # Charger la configuration d'infrastructure
    load_infrastructure_config
    
    local profile="prod"
    local dry_run=false
    local skip_provision=false
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --profile)
            profile="$2"
            shift 2
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        --skip-provision)
            skip_provision=true
            shift
            ;;
        --help)
            echo "Usage: noah deploy [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --profile PROFILE    Profil de déploiement (dev|prod) [défaut: prod]"
            echo "  --dry-run           Simulation sans exécution réelle"
            echo "  --skip-provision    Ignorer la provision d'infrastructure"
            echo "  --help              Afficher cette aide"
            return 0
            ;;
        *)
            warning "Option inconnue: $1"
            shift
            ;;
        esac
    done
    
    info "Profil de déploiement: $profile"
    info "Type d'infrastructure: $INFRASTRUCTURE_TYPE"
    
    # Vérifier que la configuration est prête
    if [[ ! -f "ansible/.vault_pass" ]]; then
        error "Environnement non configuré. Lancez d'abord: noah configure"
        exit 1
    fi
    
    # Vérifier que le type d'infrastructure est configuré
    if [[ -z "$INFRASTRUCTURE_TYPE" ]]; then
        warning "Type d'infrastructure non défini. Configuration automatique..."
        configure_infrastructure_type
    fi
    
    # Mode dry-run
    if [[ "$dry_run" == "true" ]]; then
        info "Mode simulation activé"
        local dry_run_flag="--check"
    else
        local dry_run_flag=""
    fi
    
    # Déploiement selon le type d'infrastructure
    case "$INFRASTRUCTURE_TYPE" in
        kubernetes)
            deploy_kubernetes "$profile" "$skip_provision" "$dry_run_flag"
            ;;
        docker)
            deploy_docker "$profile" "$dry_run_flag"
            ;;
        *)
            error "Type d'infrastructure non supporté: $INFRASTRUCTURE_TYPE"
            error "Types supportés: kubernetes, docker"
            exit 1
            ;;
    esac
    
    success "Déploiement terminé avec succès"
    info "Infrastructure: $INFRASTRUCTURE_TYPE"
    info "Profil: $profile"
}

# Déploiement spécifique pour Kubernetes
deploy_kubernetes() {
    local profile="$1"
    local skip_provision="$2"
    local dry_run_flag="$3"
    
    step "Déploiement sur cluster Kubernetes..."
    
    cd ansible || {
        error "Répertoire ansible non trouvé"
        exit 1
    }
    
    # Étapes de déploiement Kubernetes
    if [[ "$skip_provision" != "true" ]]; then
        step "1/4 - Provision de l'infrastructure..."
        ansible-playbook playbooks/01-provision.yml -i inventory/mycluster/hosts.yaml $dry_run_flag || {
            error "Échec de la provision d'infrastructure"
            exit 1
        }
    fi
    
    step "2/4 - Installation de Kubernetes..."
    ansible-playbook playbooks/02-install-k8s.yml -i inventory/mycluster/hosts.yaml $dry_run_flag || {
        error "Échec de l'installation Kubernetes"
        exit 1
    }
    
    step "3/4 - Configuration du cluster..."
    ansible-playbook playbooks/03-configure-cluster.yml -i inventory/mycluster/hosts.yaml $dry_run_flag || {
        error "Échec de la configuration du cluster"
        exit 1
    }
    
    step "4/4 - Déploiement des applications..."
    ansible-playbook playbooks/04-deploy-apps.yml -i inventory/mycluster/hosts.yaml $dry_run_flag || {
        error "Échec du déploiement des applications"
        exit 1
    }
    
    # Vérification post-déploiement
    if [[ "$dry_run_flag" != "--check" ]]; then
        step "Vérification du déploiement..."
        ansible-playbook playbooks/05-verify-deployment.yml -i inventory/mycluster/hosts.yaml || {
            warning "Vérification échouée, mais déploiement peut être OK"
        }
    fi
    
    cd ..
    
    if [[ "$dry_run_flag" != "--check" ]]; then
        info "Applications disponibles:"
        info "  • Keycloak: https://keycloak.noah.local"
        info "  • GitLab: https://gitlab.noah.local"
        info "  • Nextcloud: https://nextcloud.noah.local"
        info "  • Mattermost: https://mattermost.noah.local"
        info "  • Grafana: https://grafana.noah.local"
    fi
}

# Déploiement spécifique pour Docker Compose
deploy_docker() {
    local profile="$1"
    local dry_run_flag="$2"
    
    step "Déploiement avec Docker Compose..."
    
    # Vérifier que Docker est installé
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker n'est pas installé"
        info "Installation requise: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose n'est pas installé"
        info "Installation requise: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Créer le fichier docker-compose si nécessaire
    if [[ ! -f "docker-compose.yml" ]]; then
        info "Génération du fichier docker-compose.yml..."
        cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    ports:
      - "8080:8080"
    environment:
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=admin123
    command: start-dev
    
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana-data:/var/lib/grafana
      
volumes:
  grafana-data:
EOF
    fi
    
    if [[ "$dry_run_flag" != "--check" ]]; then
        step "Démarrage des services Docker..."
        docker-compose up -d || {
            error "Échec du déploiement Docker Compose"
            exit 1
        }
        
        info "Services disponibles:"
        info "  • Keycloak: http://localhost:8080"
        info "  • Grafana: http://localhost:3000"
    else
        info "Mode simulation: docker-compose up -d serait exécuté"
    fi
}

# Status du déploiement
cmd_status() {
    step "Vérification de l'état du déploiement..."
    
    local detailed=false
    local all_namespaces=false
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --detailed)
            detailed=true
            shift
            ;;
        --all)
            all_namespaces=true
            shift
            ;;
        --help)
            echo "Usage: noah status [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --detailed    Affichage détaillé"
            echo "  --all         Tous les namespaces"
            echo "  --help        Afficher cette aide"
            return 0
            ;;
        *)
            warning "Option inconnue: $1"
            shift
            ;;
        esac
    done
    
    # Vérifier kubectl
    if ! command -v kubectl >/dev/null 2>&1; then
        error "kubectl non trouvé. Impossible de vérifier l'état du cluster"
        exit 1
    fi
    
    # Vérifier la connexion au cluster
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error "Impossible de se connecter au cluster Kubernetes"
        info "Vérifiez votre configuration kubeconfig"
        exit 1
    fi
    
    # Affichage de l'état
    echo -e "${CYAN}${BOLD}État du cluster NOAH${NC}"
    echo "=================================="
    
    # Informations du cluster
    info "Informations du cluster:"
    kubectl cluster-info --short
    echo ""
    
    # État des nœuds
    info "État des nœuds:"
    kubectl get nodes -o wide
    echo ""
    
    # État des pods NOAH
    if [[ "$all_namespaces" == "true" ]]; then
        info "État des pods (tous namespaces):"
        kubectl get pods --all-namespaces
    else
        info "État des pods NOAH:"
        kubectl get pods -n noah -o wide 2>/dev/null || info "Namespace 'noah' non trouvé"
    fi
    echo ""
    
    # Services
    info "Services NOAH:"
    kubectl get svc -n noah 2>/dev/null || info "Namespace 'noah' non trouvé"
    echo ""
    
    # Ingress
    info "Ingress:"
    kubectl get ingress -n noah 2>/dev/null || info "Aucun ingress trouvé"
    echo ""
    
    if [[ "$detailed" == "true" ]]; then
        # PVC
        info "Volumes persistants:"
        kubectl get pvc -n noah 2>/dev/null || info "Aucun PVC trouvé"
        echo ""
        
        # Secrets
        info "Secrets:"
        kubectl get secrets -n noah 2>/dev/null || info "Aucun secret trouvé"
        echo ""
    fi
    
    success "Vérification terminée"
}

# Logs
cmd_logs() {
    local service=""
    local follow=false
    local lines=100
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --service)
            service="$2"
            shift 2
            ;;
        -f|--follow)
            follow=true
            shift
            ;;
        --lines)
            lines="$2"
            shift 2
            ;;
        --help)
            echo "Usage: noah logs [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --service SERVICE   Service spécifique (keycloak, gitlab, etc.)"
            echo "  -f, --follow        Suivre les logs en temps réel"
            echo "  --lines N          Nombre de lignes à afficher [défaut: 100]"
            echo "  --help             Afficher cette aide"
            return 0
            ;;
        *)
            if [[ -z "$service" ]]; then
                service="$1"
            fi
            shift
            ;;
        esac
    done
    
    if ! command -v kubectl >/dev/null 2>&1; then
        error "kubectl non trouvé"
        exit 1
    fi
    
    local kubectl_args="-n noah --tail=$lines"
    if [[ "$follow" == "true" ]]; then
        kubectl_args="$kubectl_args -f"
    fi
    
    if [[ -n "$service" ]]; then
        info "Logs du service: $service"
        kubectl logs $kubectl_args -l app=$service
    else
        info "Logs de tous les services NOAH:"
        kubectl logs $kubectl_args --all-containers=true --selector=app.kubernetes.io/instance
    fi
}

# Commandes de gestion
cmd_start() {
    step "Démarrage des services NOAH..."
    if command -v kubectl >/dev/null 2>&1; then
        kubectl scale deployment --all --replicas=1 -n noah
        success "Services démarrés"
    else
        error "kubectl non trouvé"
    fi
}

cmd_stop() {
    step "Arrêt des services NOAH..."
    if command -v kubectl >/dev/null 2>&1; then
        kubectl scale deployment --all --replicas=0 -n noah
        success "Services arrêtés"
    else
        error "kubectl non trouvé"
    fi
}

cmd_restart() {
    step "Redémarrage des services NOAH..."
    if command -v kubectl >/dev/null 2>&1; then
        kubectl rollout restart deployment --all -n noah
        success "Services redémarrés"
    else
        error "kubectl non trouvé"
    fi
}

# Validation
cmd_validate() {
    step "Validation de la configuration NOAH..."
    
    local check_ansible=true
    local check_helm=true
    local check_k8s=true
    
    # Validation Ansible
    if [[ "$check_ansible" == "true" ]]; then
        info "Validation des playbooks Ansible..."
        for playbook in ansible/playbooks/*.yml; do
            if [[ -f "$playbook" ]]; then
                if ansible-playbook --syntax-check "$playbook" >/dev/null 2>&1; then
                    success "✅ $(basename "$playbook")"
                else
                    error "❌ $(basename "$playbook")"
                fi
            fi
        done
    fi
    
    # Validation Helm
    if [[ "$check_helm" == "true" ]] && command -v helm >/dev/null 2>&1; then
        info "Validation des charts Helm..."
        for chart in helm/*/; do
            if [[ -d "$chart" ]] && [[ -f "$chart/Chart.yaml" ]]; then
                if helm lint "$chart" >/dev/null 2>&1; then
                    success "✅ $(basename "$chart")"
                else
                    error "❌ $(basename "$chart")"
                fi
            fi
        done
    fi
    
    # Validation inventaire
    info "Validation de l'inventaire..."
    if ansible-inventory --list -i ansible/inventory/mycluster/hosts.yaml >/dev/null 2>&1; then
        success "✅ Inventaire valide"
    else
        error "❌ Erreur dans l'inventaire"
    fi
    
    success "Validation terminée"
}

# Test de connectivité
cmd_test() {
    step "Tests de connectivité NOAH..."
    
    local test_ssh=true
    local test_apps=true
    
    # Test SSH
    if [[ "$test_ssh" == "true" ]]; then
        info "Test de connectivité SSH..."
        if ansible all -m ping -i ansible/inventory/mycluster/hosts.yaml >/dev/null 2>&1; then
            success "✅ Connectivité SSH OK"
        else
            error "❌ Problème de connectivité SSH"
        fi
    fi
    
    # Test des applications
    if [[ "$test_apps" == "true" ]]; then
        info "Test des applications..."
        local apps=("keycloak" "gitlab" "nextcloud" "mattermost" "grafana")
        for app in "${apps[@]}"; do
            if curl -k -s -o /dev/null -w "%{http_code}" "https://$app.noah.local" | grep -q "200\|302\|401"; then
                success "✅ $app accessible"
            else
                warning "⚠️  $app non accessible"
            fi
        done
    fi
    
    success "Tests terminés"
}

# Gestion des secrets
cmd_secrets() {
    local subcommand="$1"
    shift
    
    case "$subcommand" in
    init)
        cmd_secrets_init "$@"
        ;;
    generate)
        cmd_secrets_generate "$@"
        ;;
    validate)
        cmd_secrets_validate "$@"
        ;;
    encrypt)
        cmd_secrets_encrypt "$@"
        ;;
    decrypt)
        cmd_secrets_decrypt "$@"
        ;;
    edit)
        cmd_secrets_edit "$@"
        ;;
    view)
        cmd_secrets_view "$@"
        ;;
    rotate)
        cmd_secrets_rotate "$@"
        ;;
    status)
        cmd_secrets_status "$@"
        ;;
    *)
        cmd_secrets_help
        ;;
    esac
}

cmd_secrets_help() {
    echo -e "${BOLD}NOAH CLI - Gestion des secrets avec SOPS${NC}"
    echo ""
    echo -e "${YELLOW}Commandes de base:${NC}"
    echo "  secrets init       Initialiser SOPS (.sops.yaml) et le fichier de secrets"
    echo "  secrets generate   Générer de nouveaux secrets sécurisés"
    echo "  secrets validate   Valider la configuration des secrets"
    echo "  secrets encrypt    Chiffrer le fichier des secrets avec SOPS"
    echo "  secrets decrypt    Déchiffrer le fichier des secrets"
    echo "  secrets edit       Éditer le fichier des secrets chiffrés"
    echo "  secrets view       Voir le contenu des secrets chiffrés"
    echo ""
    echo -e "${YELLOW}Commandes avancées:${NC}"
    echo "  secrets rotate     Effectuer une rotation des secrets"
    echo "  secrets status     Vérifier l'état du chiffrement SOPS"
    echo ""
    echo -e "${YELLOW}Exemples:${NC}"
    echo "  noah secrets generate              # Générer tous les secrets"
    echo "  noah secrets edit                  # Éditer avec SOPS"
    echo "  noah secrets view                  # Voir les secrets déchiffrés"
    echo "  noah secrets encrypt               # Chiffrer avec SOPS"
    echo "  noah secrets rotate                # Rotation des secrets"
    echo "  noah secrets status                # Vérifier le statut SOPS"
    echo ""
    echo -e "${CYAN}Informations SOPS:${NC}"
    echo "  • Chiffrement: Age encryption"
    echo "  • Configuration: .sops.yaml"
    echo "  • Clés: ~/.config/sops/age/keys.txt"
    echo ""
}

cmd_secrets_init() {
    step "Initialisation de la configuration SOPS..."
    local secrets_file="ansible/vars/secrets.yml"
    local created_any=false

    # Créer .sops.yaml minimal si absent
    if [[ ! -f ".sops.yaml" ]]; then
        cat > .sops.yaml << 'EOF'
# Configuration SOPS minimale pour NOAH
# Remplacez AGE-PLACEHOLDER-PUBLIC-KEY par votre clé publique Age
# Générer une paire: age-keygen -o ~/.config/sops/age/keys.txt
# Clé publique: grep -m1 '^# public key:' ~/.config/sops/age/keys.txt | awk '{print $4}'
creation_rules:
  - path_regex: ^ansible/vars/secrets\.yml$
    age: ["AGE-PLACEHOLDER-PUBLIC-KEY"]
    encrypted_regex: '^(data|stringData|vault_.*)$'
EOF
        success "Fichier .sops.yaml créé"
        created_any=true
    else
        info ".sops.yaml déjà présent"
    fi

    # Créer un template de secrets si absent
    if [[ ! -f "$secrets_file" ]]; then
        mkdir -p "$(dirname "$secrets_file")"
        cat > "$secrets_file" << 'EOF'
# Secrets NOAH - Gérés par SOPS (Age)
# Exemple de clés:
# vault_postgres_password: "changeme"
# vault_keycloak_admin_password: "changeme"
EOF
        success "Template créé: $secrets_file"
        created_any=true
    else
        info "Fichier de secrets déjà présent: $secrets_file"
    fi

    if command -v sops >/dev/null 2>&1 && [[ -f "$secrets_file" ]]; then
        # Chiffrer en place si .sops.yaml contient une clé valide
        if grep -q "AGE-PLACEHOLDER-PUBLIC-KEY" .sops.yaml; then
            warning "Remplacez la clé publique Age placeholder dans .sops.yaml avant chiffrement"
        else
            if sops --encrypt --in-place "$secrets_file"; then
                success "Secrets chiffrés avec SOPS"
            else
                warning "Impossible de chiffrer automatiquement les secrets"
            fi
        fi
    fi

    $created_any || info "Rien à initialiser"
}

cmd_secrets_generate() {
    step "Génération des secrets NOAH..."
    
    local secrets_file="ansible/vars/secrets.yml"
    
    # Vérifier si SOPS est disponible
    if ! command -v sops >/dev/null 2>&1; then
        error "SOPS n'est pas installé"
        info "Installation: voir docs/SOPS_INTEGRATION.md"
        exit 1
    fi
    
    # Utiliser le nouveau script SOPS ou générer directement
    if [[ -f "script/sops-secrets-manager.sh" ]]; then
        ./script/sops-secrets-manager.sh generate
        success "Secrets générés avec SOPS"
    else
        warning "Script SOPS non trouvé - Génération manuelle requise"
        info "Utilisez: sops $secrets_file"
    fi
}

cmd_secrets_validate() {
    step "Validation des secrets NOAH..."
    
    local secrets_file="ansible/vars/secrets.yml"
    
    # Vérifier SOPS
    if ! command -v sops >/dev/null 2>&1; then
        error "SOPS n'est pas installé"
        exit 1
    fi
    
    # Vérifier l'existence du fichier
    if [[ ! -f "$secrets_file" ]]; then
        error "Fichier des secrets non trouvé: $secrets_file"
        info "Créez le fichier avec: noah secrets edit"
        exit 1
    fi
    
    # Vérifier que le fichier est chiffré avec SOPS
    if sops --decrypt "$secrets_file" >/dev/null 2>&1; then
        success "✅ Fichier chiffré avec SOPS"
        
        # Vérifier la configuration SOPS
        if [[ -f ".sops.yaml" ]]; then
            success "✅ Configuration SOPS trouvée (.sops.yaml)"
        else
            warning "⚠️  Configuration SOPS non trouvée (.sops.yaml)"
        fi
        
        # Vérifier les clés Age
        if [[ -f "$HOME/.config/sops/age/keys.txt" ]]; then
            success "✅ Clés Age trouvées"
        else
            warning "⚠️  Clés Age non trouvées dans ~/.config/sops/age/keys.txt"
        fi
        
        success "Validation SOPS terminée"
    else
        error "❌ Le fichier n'est pas chiffré avec SOPS ou les clés sont manquantes"
        info "Vérifiez: ~/.config/sops/age/keys.txt et .sops.yaml"
        exit 1
    fi
}

cmd_secrets_encrypt() {
    step "Chiffrement du fichier des secrets avec SOPS..."
    
    local secrets_file="ansible/vars/secrets.yml"
    
    # Vérifier SOPS
    if ! command -v sops >/dev/null 2>&1; then
        error "SOPS n'est pas installé"
        exit 1
    fi
    
    if [[ ! -f "$secrets_file" ]]; then
        error "Fichier des secrets non trouvé: $secrets_file"
        info "Créez le fichier avec: noah secrets edit"
        exit 1
    fi
    
    # Vérifier si déjà chiffré avec SOPS
    if sops --decrypt "$secrets_file" >/dev/null 2>&1; then
        success "Le fichier est déjà chiffré avec SOPS"
        return 0
    fi
    
    # Vérifier la configuration SOPS
    if [[ -f ".sops.yaml" ]]; then
        error "Configuration SOPS manquante (.sops.yaml)"
        info "Exécutez la migration: ./script/deprecated-shell-secrets/migrate-to-sops.sh"
        exit 1
    fi
        error "❌ Configuration SOPS manquante (.sops.yaml)"
        info "   → Exécutez: noah secrets init (créera un modèle minimal)"
    # Chiffrer avec SOPS
    if sops --encrypt --in-place "$secrets_file"; then
        success "Fichier chiffré avec SOPS"
        info "Le fichier est maintenant sécurisé et prêt pour Git"
    else
        error "Échec du chiffrement SOPS"
        exit 1
    fi
}

cmd_secrets_decrypt() {
    step "Déchiffrement du fichier des secrets..."
    
    local secrets_file="ansible/vars/secrets.yml"
    
    # Vérifier SOPS
    if ! command -v sops >/dev/null 2>&1; then
        error "SOPS n'est pas installé"
        exit 1
    fi
    
    if [[ ! -f "$secrets_file" ]]; then
        error "Fichier des secrets non trouvé: $secrets_file"
        exit 1
    fi
    
    # Vérifier si chiffré avec SOPS
    if sops --decrypt "$secrets_file" >/dev/null 2>&1; then
        # Déchiffrer en place
        if sops --decrypt --in-place "$secrets_file"; then
            success "Fichier des secrets déchiffré"
            warning "⚠️  ATTENTION: Le fichier est maintenant en clair - Ne pas le committer !"
            info "Pour re-chiffrer: noah secrets encrypt"
        else
            error "Échec du déchiffrement"
            exit 1
        fi
    else
        warning "Le fichier n'est pas chiffré avec SOPS ou les clés sont manquantes"
        info "Vérifiez les clés Age dans ~/.config/sops/age/keys.txt"
    fi
}

cmd_secrets_edit() {
    step "Édition du fichier des secrets avec SOPS..."
    
    local secrets_file="ansible/vars/secrets.yml"
    
    # Vérifier SOPS
    if ! command -v sops >/dev/null 2>&1; then
        error "SOPS n'est pas installé"
        exit 1
    fi
    
    # Créer le fichier s'il n'existe pas
    if [[ ! -f "$secrets_file" ]]; then
        warning "Fichier des secrets non trouvé - Création d'un nouveau fichier"
        
        # Vérifier la configuration SOPS
        if [[ ! -f ".sops.yaml" ]]; then
            error "Configuration SOPS manquante (.sops.yaml)"
            info "Exécutez la migration: ./script/deprecated-shell-secrets/migrate-to-sops.sh"
            exit 1
        fi
        
        # Créer un fichier template
        mkdir -p "$(dirname "$secrets_file")"
        cat > "$secrets_file" << 'EOF'
# Secrets NOAH - Gestion avec SOPS
# Ajoutez vos secrets ci-dessous

# Exemples:
# vault_postgres_password: "changeme"
# vault_keycloak_admin_password: "changeme"
EOF
        info "Fichier template créé: $secrets_file"
    fi
    
    # Éditer avec SOPS
    if sops "$secrets_file"; then
        success "Édition terminée"
        info "Le fichier est automatiquement chiffré avec SOPS"
    else
        error "Échec de l'édition SOPS"
        exit 1
    fi
}

cmd_secrets_view() {
    step "Affichage du fichier des secrets..."
    
    local secrets_file="ansible/vars/secrets.yml"
    
    # Vérifier SOPS
    if ! command -v sops >/dev/null 2>&1; then
        error "SOPS n'est pas installé"
        exit 1
    fi
    
    if [[ ! -f "$secrets_file" ]]; then
        error "Fichier des secrets non trouvé: $secrets_file"
        info "Créez le fichier avec: noah secrets edit"
        exit 1
    fi
    
    # Afficher avec SOPS
    if sops --decrypt "$secrets_file"; then
        success "Affichage terminé"
    else
        error "Impossible de déchiffrer le fichier"
        info "Vérifiez les clés Age dans ~/.config/sops/age/keys.txt"
        exit 1
    fi
}

cmd_secrets_rotate() {
    step "Rotation des secrets NOAH..."
    
    # Utiliser le nouveau script SOPS simplifié
    if [[ -f "script/sops-secrets-manager.sh" ]]; then
        ./script/sops-secrets-manager.sh rotate
        success "Rotation des secrets terminée"
    else
        warning "Script SOPS non trouvé - Rotation manuelle"
        info "Pour rotation manuelle:"
        info "1. noah secrets edit"
        info "2. Modifier les valeurs des secrets"
        info "3. Sauvegarder (SOPS chiffre automatiquement)"
    fi
}

cmd_secrets_status() {
    step "Vérification du statut SOPS..."
    
    local secrets_file="ansible/vars/secrets.yml"
    local status_ok=true
    
    echo -e "${CYAN}=== STATUT SOPS NOAH ===${NC}"
    echo ""
    
    # Vérifier SOPS
    if command -v sops >/dev/null 2>&1; then
        local sops_version=$(sops --version 2>/dev/null | head -1)
        success "✅ SOPS installé: $sops_version"
    else
        error "❌ SOPS non installé"
        status_ok=false
    fi
    
    # Vérifier Age
    if command -v age >/dev/null 2>&1; then
        local age_version=$(age --version 2>/dev/null)
        success "✅ Age installé: $age_version"
    else
        error "❌ Age non installé"
        status_ok=false
    fi
    
    # Vérifier la configuration SOPS
    if [[ -f ".sops.yaml" ]]; then
        success "✅ Configuration SOPS (.sops.yaml)"
        local rules_count=$(grep -c "path_regex:" .sops.yaml)
        info "   → $rules_count règles configurées"
    else
        error "❌ Configuration SOPS manquante (.sops.yaml)"
        status_ok=false
    fi
    
    # Vérifier les clés Age
    if [[ -f "$HOME/.config/sops/age/keys.txt" ]]; then
        success "✅ Clés Age disponibles"
        local key_count=$(grep -c "AGE-SECRET-KEY" "$HOME/.config/sops/age/keys.txt" 2>/dev/null || echo "0")
        info "   → $key_count clé(s) privée(s)"
    else
        error "❌ Clés Age manquantes (~/.config/sops/age/keys.txt)"
        status_ok=false
    fi
    
    # Vérifier le fichier des secrets
    if [[ -f "$secrets_file" ]]; then
        if sops --decrypt "$secrets_file" >/dev/null 2>&1; then
            success "✅ Fichier secrets chiffré avec SOPS"
            local secrets_count=$(sops --decrypt "$secrets_file" 2>/dev/null | grep -c "^vault_" || echo "0")
            info "   → $secrets_count secret(s) détecté(s)"
        else
            error "❌ Fichier secrets non chiffré ou inaccessible"
            status_ok=false
        fi
    else
        warning "⚠️  Fichier secrets non trouvé ($secrets_file)"
        info "   → Créez-le avec: noah secrets edit"
    fi
    
    # Vérifier Helm-Secrets plugin
    if command -v helm >/dev/null 2>&1; then
        if helm plugin list 2>/dev/null | grep -q "secrets"; then
            success "✅ Plugin Helm-Secrets installé"
        else
            warning "⚠️  Plugin Helm-Secrets non installé"
            info "   → Installation: helm plugin install https://github.com/jkroepke/helm-secrets"
        fi
    fi
    
    echo ""
    if [[ "$status_ok" == "true" ]]; then
        success "🎉 Configuration SOPS complète et fonctionnelle"
        echo ""
        echo -e "${YELLOW}Commandes disponibles:${NC}"
        echo "  noah secrets edit    # Éditer les secrets"
        echo "  noah secrets view    # Voir les secrets"
        echo "  noah secrets rotate  # Rotation des secrets"
    else
        error "⚠️  Configuration SOPS incomplète"
        echo ""
        echo -e "${YELLOW}Actions recommandées:${NC}"
        echo "  1. Installer les outils manquants"
        echo "  2. Voir: docs/SOPS_INTEGRATION.md"
        echo "  3. Ou exécuter: ./script/deprecated-shell-secrets/migrate-to-sops.sh"
    fi
}

# ===================================================================
# COMMANDES PIPELINE SETUP
# ===================================================================

# Initialisation du pipeline
cmd_init_pipeline() {
    step "Initialisation du pipeline NOAH..."
    
    local auto_mode=false
    local dry_run=false
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --auto)
            auto_mode=true
            AUTO_MODE=true
            shift
            ;;
        --dry-run)
            dry_run=true
            DRY_RUN=true
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
        --help)
            echo "Usage: noah init-pipeline [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --auto          Mode automatique"
            echo "  --dry-run       Simulation sans exécution"
            echo "  --domain=VALUE  Domaine personnalisé"
            echo "  --master=IP     IP du serveur master"
            echo "  --worker=IP     IP du serveur worker"
            echo "  --ingress=IP    IP de l'ingress"
            echo "  --help          Afficher cette aide"
            return 0
            ;;
        *)
            warning "Option inconnue: $1"
            shift
            ;;
        esac
    done
    
    check_pipeline_requirements
    interactive_pipeline_setup
    install_ansible_collections
    setup_kubespray
    validate_pipeline_config
    display_pipeline_summary
    
    success "Initialisation du pipeline terminée"
}

# Configuration du pipeline
cmd_configure_pipeline() {
    step "Configuration du pipeline NOAH..."
    
    local auto_mode=false
    local dry_run=false
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --auto)
            auto_mode=true
            AUTO_MODE=true
            shift
            ;;
        --dry-run)
            dry_run=true
            DRY_RUN=true
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
        --help)
            echo "Usage: noah configure-pipeline [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --auto          Mode automatique"
            echo "  --dry-run       Simulation sans exécution"
            echo "  --domain=VALUE  Domaine personnalisé"
            echo "  --master=IP     IP du serveur master"
            echo "  --worker=IP     IP du serveur worker"
            echo "  --ingress=IP    IP de l'ingress"
            echo "  --help          Afficher cette aide"
            return 0
            ;;
        *)
            warning "Option inconnue: $1"
            shift
            ;;
        esac
    done
    
    check_pipeline_requirements
    interactive_pipeline_setup
    setup_vault_password
    generate_ssh_keys
    update_inventory
    update_domains
    encrypt_secrets
    validate_pipeline_config
    display_pipeline_summary
    
    success "Configuration du pipeline terminée"
}

# Configuration complète du pipeline
cmd_setup_pipeline() {
    step "Configuration complète du pipeline NOAH..."
    
    local auto_mode=false
    local dry_run=false
    
    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        --auto)
            auto_mode=true
            AUTO_MODE=true
            shift
            ;;
        --dry-run)
            dry_run=true
            DRY_RUN=true
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
        --help)
            echo "Usage: noah setup-pipeline [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --auto          Mode automatique"
            echo "  --dry-run       Simulation sans exécution"
            echo "  --domain=VALUE  Domaine personnalisé"
            echo "  --master=IP     IP du serveur master"
            echo "  --worker=IP     IP du serveur worker"
            echo "  --ingress=IP    IP de l'ingress"
            echo "  --help          Afficher cette aide"
            return 0
            ;;
        *)
            warning "Option inconnue: $1"
            shift
            ;;
        esac
    done
    
    # Étape 1: Initialisation
    info "Étape 1/2: Initialisation du pipeline"
    check_pipeline_requirements
    interactive_pipeline_setup
    install_ansible_collections
    setup_kubespray
    
    # Étape 2: Configuration
    info "Étape 2/2: Configuration du pipeline"
    setup_vault_password
    generate_ssh_keys
    update_inventory
    update_domains
    encrypt_secrets
    
    validate_pipeline_config
    display_pipeline_summary
    
    success "Configuration complète du pipeline terminée"
}

# ===================================================================
# FONCTION PRINCIPALE
# ===================================================================

# Fonction principale
main() {
    # Gestion des arguments globaux
    local verbose=false
    local quiet=false
    local dry_run=false
    
    # Parser les arguments globaux
    while [[ $# -gt 0 ]]; do
        case $1 in
        -h|--help)
            load_infrastructure_config
            show_banner
            show_help
            exit 0
            ;;
        --version)
            echo "NOAH CLI v${NOAH_VERSION}"
            exit 0
            ;;
        -v|--verbose)
            verbose=true
            shift
            ;;
        -q|--quiet)
            quiet=true
            shift
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        -*)
            error "Option globale inconnue: $1"
            echo "Utilisez --help pour voir les options disponibles"
            exit 1
            ;;
        *)
            break
            ;;
        esac
    done
    
    # Configuration du mode verbose/quiet
    if [[ "$verbose" == "true" ]]; then
        set -x
    fi
    
    if [[ "$quiet" == "true" ]]; then
        exec 1>/dev/null
    fi
    
    # Charger la configuration d'infrastructure
    load_infrastructure_config
    
    # Afficher le banner si pas en mode quiet
    if [[ "$quiet" != "true" ]]; then
        show_banner
    fi
    
    # Vérifier l'environnement
    check_environment
    
    # Si aucune commande, afficher l'aide
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    # Router vers la bonne commande
    local command="$1"
    shift
    
    case "$command" in
    init)
        check_prerequisites
        cmd_init "$@"
        ;;
    init-pipeline)
        cmd_init_pipeline "$@"
        ;;
    configure)
        check_prerequisites
        cmd_configure "$@"
        ;;
    configure-pipeline)
        cmd_configure_pipeline "$@"
        ;;
    setup-pipeline)
        cmd_setup_pipeline "$@"
        ;;
    infrastructure)
        configure_infrastructure_type
        ;;
    deploy)
        check_prerequisites
        cmd_deploy "$@"
        ;;
    status)
        cmd_status "$@"
        ;;
    logs)
        cmd_logs "$@"
        ;;
    start)
        cmd_start "$@"
        ;;
    stop)
        cmd_stop "$@"
        ;;
    restart)
        cmd_restart "$@"
        ;;
    validate)
        check_prerequisites
        cmd_validate "$@"
        ;;
    test)
        check_prerequisites
        cmd_test "$@"
        ;;
    secrets)
        check_prerequisites
        cmd_secrets "$@"
        ;;
    health)
        cmd_status --detailed "$@"
        ;;
    dashboard)
        info "Ouverture du dashboard Grafana..."
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open "https://grafana.noah.local"
        elif command -v open >/dev/null 2>&1; then
            open "https://grafana.noah.local"
        else
            info "Accédez manuellement à: https://grafana.noah.local"
        fi
        ;;
    backup|restore|update|metrics|alerts|config|lint|debug)
        warning "Commande '$command' pas encore implémentée dans cette version"
        info "Fonctionnalité prévue pour une future version"
        ;;
    *)
        error "Commande inconnue: $command"
        echo ""
        echo "Commandes disponibles:"
        echo "  init, init-pipeline, configure, configure-pipeline, setup-pipeline"
        echo "  deploy, status, logs, start, stop, restart"
        echo "  validate, test, health, dashboard, infrastructure, secrets"
        echo ""
        echo "Utilisez 'noah --help' pour plus d'informations"
        exit 1
        ;;
    esac
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
