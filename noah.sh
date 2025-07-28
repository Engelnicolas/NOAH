#!/bin/bash
# NOAH CLI - Interface pour les pipelines CI/CD modernes
# Ce script remplace l'ancien CLI Python par une interface pour les pipelines Ansible/Helm/Kubernetes

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
NOAH_VERSION="2.0.0"
PIPELINE_MODE="modern"

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
    echo "║                        🚀 NOAH CLI v${NOAH_VERSION}                        ║"
    echo "║              Network Operations & Automation Hub              ║"
    echo "║                   Pipeline CI/CD Moderne                     ║"
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

# Fonction d'aide principale
show_help() {
    echo -e "${BOLD}NOAH CLI - Network Operations & Automation Hub${NC}"
    echo ""
    echo -e "${YELLOW}COMMANDES PRINCIPALES:${NC}"
    echo ""
    echo -e "${CYAN}🚀 Déploiement${NC}"
    echo "  init              Initialiser l'environnement de déploiement"
    echo "  configure         Configurer les paramètres de déploiement"  
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
    echo "  secrets           Gérer les secrets"
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
    echo "  noah init                    # Initialiser l'environnement"
    echo "  noah configure --auto        # Configuration automatique"
    echo "  noah deploy --profile prod   # Déploiement en production"
    echo "  noah status --all            # État complet du système"
    echo "  noah backup --schedule daily # Sauvegarde quotidienne"
    echo ""
    echo -e "${BLUE}Pour plus d'informations sur une commande:${NC}"
    echo "  noah <commande> --help"
    echo ""
}

# Initialisation de l'environnement
cmd_init() {
    step "Initialisation de l'environnement NOAH..."
    
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
    
    # Lancer le script d'initialisation
    if [[ -f "script/setup-pipeline.sh" ]]; then
        info "Lancement du script d'initialisation..."
        ./script/setup-pipeline.sh
    else
        error "Script d'initialisation non trouvé: script/setup-pipeline.sh"
        exit 1
    fi
    
    success "Initialisation terminée"
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
    
    # Vérifier que la configuration est prête
    if [[ ! -f "ansible/.vault_pass" ]]; then
        error "Environnement non configuré. Lancez d'abord: noah configure"
        exit 1
    fi
    
    # Mode dry-run
    if [[ "$dry_run" == "true" ]]; then
        info "Mode simulation activé"
        local dry_run_flag="--check"
    else
        local dry_run_flag=""
    fi
    
    cd ansible || {
        error "Répertoire ansible non trouvé"
        exit 1
    }
    
    # Étapes de déploiement
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
    if [[ "$dry_run" != "true" ]]; then
        step "Vérification du déploiement..."
        ansible-playbook playbooks/05-verify-deployment.yml -i inventory/mycluster/hosts.yaml || {
            warning "Vérification échouée, mais déploiement peut être OK"
        }
    fi
    
    cd ..
    success "Déploiement terminé!"
    
    if [[ "$dry_run" != "true" ]]; then
        info "Applications disponibles:"
        info "  • Keycloak: https://keycloak.noah.local"
        info "  • GitLab: https://gitlab.noah.local"
        info "  • Nextcloud: https://nextcloud.noah.local"
        info "  • Mattermost: https://mattermost.noah.local"
        info "  • Grafana: https://grafana.noah.local"
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
    configure)
        check_prerequisites
        cmd_configure "$@"
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
    backup|restore|update|metrics|alerts|config|secrets|lint|debug)
        warning "Commande '$command' pas encore implémentée dans cette version"
        info "Fonctionnalité prévue pour une future version"
        ;;
    *)
        error "Commande inconnue: $command"
        echo ""
        echo "Commandes disponibles:"
        echo "  init, configure, deploy, status, logs, start, stop, restart"
        echo "  validate, test, health, dashboard"
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
