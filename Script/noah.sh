#!/bin/bash

# =============================================================================
# NOAH - Next Open-source Architecture Hub CLI
# =============================================================================
#
# DESCRIPTION:
#   This is the main CLI entry point for NOAH project operations.
#   It acts as a unified interface that routes commands to specialized scripts.
#
# PURPOSE:
#   - Provide a single, consistent interface for all NOAH operations
#   - Route commands to appropriate specialized scripts
#   - Maintain backward compatibility while enabling script evolution
#   - Offer help and version information
#
# ARCHITECTURE:
#   The CLI follows a command-dispatch pattern where:
#   1. Main script receives and parses commands
#   2. Commands are routed to specialized Python/Bash scripts
#   3. All arguments are passed through to the target script
#   4. Error handling and script validation is centralized
#
# AUTHOR: NOAH Team
# VERSION: 4.0.0
# DATE: July 16, 2025
# =============================================================================

# Strict error handling
set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Script metadata
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_VERSION="4.0.0"
readonly SCRIPT_NAME="noah"
readonly SCRIPT_DESCRIPTION="Next Open-source Architecture Hub CLI"

# Terminal colors for enhanced output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# =============================================================================
# SCRIPT MAPPING AND DOCUMENTATION
# =============================================================================

# This section documents what each script does and how it's invoked
declare -A SCRIPT_COMMANDS=(
    # Command structure: [command]="script_path:execution_method:description"

    ["fix"]="noah-fix.py:python3:Fix common issues automatically with intelligent repairs"
    ["infra"]="noah-deploy.py:python3:Infrastructure management (setup, deploy, status, teardown)"
    ["monitoring"]="noah-monitoring.py:python3:Monitoring stack management (Prometheus, Grafana)"
    ["linting"]="noah-linter.py:python3:Linting validation and setup for code quality"
    ["deps"]="noah-deps-manager:python3:Dependencies management and security checks"
    ["setup"]="noah-setup:python3:Quick setup and environment initialization"
    ["requirements"]="noah-tech-requirements:python3:Technical requirements validation"
)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Print colored output with consistent formatting
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Display the NOAH banner
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
███    ██  ██████   █████  ██   ██
████   ██ ██    ██ ██   ██ ██   ██
██ ██  ██ ██    ██ ███████ ███████
██  ██ ██ ██    ██ ██   ██ ██   ██
██   ████  ██████  ██   ██ ██   ██

Next Open-source Architecture Hub
EOF
    echo -e "${NC}"
}

# =============================================================================
# ROOT PRIVILEGES MANAGEMENT
# =============================================================================

# Check if running as root and request elevation if needed
check_root_privileges() {
    local command="$1"

    # Commands that require root privileges
    declare -a root_commands=("infra" "monitoring" "deps" "setup")

    # Check if current command requires root
    local requires_root=false
    for cmd in "${root_commands[@]}"; do
        if [[ "$command" == "$cmd" ]]; then
            requires_root=true
            break
        fi
    done

    # If command doesn't require root, continue normally
    if [[ "$requires_root" == "false" ]]; then
        return 0
    fi

    # Check if already running as root
    if [[ $EUID -eq 0 ]]; then
        print_success "Running with root privileges ✓"
        return 0
    fi

    # Request root privileges
    print_warning "La commande '$command' nécessite des privilèges root"
    print_info "Les opérations suivantes nécessitent des privilèges administrateur :"
    print_info "  • Installation de packages système"
    print_info "  • Configuration de services réseau"
    print_info "  • Gestion des conteneurs Docker/Kubernetes"
    print_info "  • Modification des configurations système"
    echo ""

    # Prompt user for confirmation
    echo -e "${YELLOW}Voulez-vous continuer avec sudo ? [y/N]${NC}"
    read -r response

    case "$response" in
        [yY]|[yY][eE][sS]|[oO]|[oO][uU][iI])
            print_info "Relancement avec sudo..."
            # Re-execute the entire script with sudo
            exec sudo bash "$0" "$command" "$@"
            ;;
        *)
            print_error "Opération annulée par l'utilisateur"
            print_info "Pour exécuter sans interaction, utilisez :"
            print_info "  sudo ./noah $command"
            exit 1
            ;;
    esac
}

# Alternative function for non-interactive environments
ensure_root_privileges() {
    local command="$1"

    # Commands that require root privileges
    declare -a root_commands=("infra" "monitoring" "deps" "setup")

    # Check if current command requires root
    local requires_root=false
    for cmd in "${root_commands[@]}"; do
        if [[ "$command" == "$cmd" ]]; then
            requires_root=true
            break
        fi
    done

    # If command doesn't require root, continue normally
    if [[ "$requires_root" == "false" ]]; then
        return 0
    fi

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "Cette commande doit être exécutée en tant que root"
        print_error "Utilisez: sudo ./noah $command"
        print_info ""
        print_info "Commandes nécessitant root: ${root_commands[*]}"
        exit 1
    fi

    print_success "Privilèges root confirmés ✓"
}

# =============================================================================
# HELP SYSTEM
# =============================================================================

show_help() {
    show_banner
    echo -e "${BLUE}$SCRIPT_DESCRIPTION${NC}"
    echo -e "${BLUE}Version: $SCRIPT_VERSION${NC}"
    echo ""
    echo -e "${YELLOW}USAGE:${NC}"
    echo "    ./noah COMMAND [OPTIONS]"
    echo ""
    echo -e "${YELLOW}AVAILABLE COMMANDS:${NC}"
    echo ""

    # Infrastructure Management
    echo -e "${PURPLE}📦 Infrastructure Management:${NC}"
    echo -e "  ${GREEN}infra${NC}          Infrastructure lifecycle management"
    echo "                   Options:"
    echo "                   • --namespace NAME    - Kubernetes namespace (default: noah)"
    echo "                   • --timeout TIME      - Helm deployment timeout (default: 600s)"
    echo "                   • --dry-run           - Show what would be deployed"
    echo "                   • --priority-only     - Deploy only priority infrastructure"
    echo "                   • --list-charts       - List all available charts"
    echo "                   • --verbose, -v       - Enable verbose output"
    echo ""

    # Monitoring & Observability
    echo -e "${PURPLE}📊 Monitoring & Observability:${NC}"
    echo -e "  ${GREEN}monitoring${NC}     Monitoring stack operations"
    echo "                   Actions: deploy, status, teardown"
    echo "                   Options:"
    echo "                   • -e ENV              - Environment (dev, staging, prod)"
    echo "                   • -n NAMESPACE        - Kubernetes namespace (default: noah-monitoring)"
    echo "                   • --dry-run           - Show what would be done"
    echo "                   • --save-report       - Save status report to file"
    echo "                   • -v, --verbose       - Enable verbose output"
    echo ""

    # Code Quality & Validation
    echo -e "${PURPLE}🔍 Code Quality & Validation:${NC}"
    echo -e "  ${GREEN}fix${NC}            Automated issue resolution"
    echo "                   Options:"
    echo "                   • -t TYPES            - File types: yaml, shell, mkdocs"
    echo "                   • -v, --verbose       - Enable verbose output"
    echo "                   • -n, --dry-run       - Show what would be fixed"
    echo "                   • file                - Specific file to fix"
    echo ""
    echo -e "  ${GREEN}linting${NC}        Code linting and style checking"
    echo "                   Actions: setup, lint, precommit, report, help"
    echo "                   Options:"
    echo "                   • --all               - Run on all files"
    echo "                   • --hook-id ID        - Specific pre-commit hook"
    echo "                   • --save              - Save report to file"
    echo "                   • -v, --verbose       - Enable verbose output"
    echo ""

    # Dependencies & Setup
    echo -e "${PURPLE}🔧 Dependencies & Setup:${NC}"
    echo -e "  ${GREEN}deps${NC}           Dependencies management and security"
    echo "                   Options:"
    echo "                   • --auto-install     - Auto-check and install missing dependencies"
    echo "                   • --upgrade           - Upgrade all dependencies"
    echo "                   • --check-security    - Check for security vulnerabilities"
    echo "                   • --report            - Generate dependency report"
    echo "                   • --cleanup           - Clean up unused dependencies"
    echo "                   • -v, --verbose       - Enable verbose output"
    echo ""
    echo -e "  ${GREEN}setup${NC}          Quick setup and environment initialization"
    echo "                   Options:"
    echo "                   • --profile PROFILE   - Deployment profile (minimal, root)"
    echo "                   • --dev               - Include development dependencies"
    echo "                   • --deps-only         - Only install dependencies"
    echo "                   • --check-only        - Only run validation checks"
    echo "                   • -v, --verbose       - Enable verbose output"
    echo ""
    echo -e "  ${GREEN}requirements${NC}   Technical requirements validation"
    echo "                   Options:"
    echo "                   • --profile PROFILE   - Deployment profile (minimal, root)"
    echo ""

    echo -e "${YELLOW}SCRIPT EXECUTION DETAILS:${NC}"
    echo ""
    for cmd in "${!SCRIPT_COMMANDS[@]}"; do
        IFS=':' read -r script_path execution_method description <<< "${SCRIPT_COMMANDS[$cmd]}"
        if [[ "$execution_method" == "placeholder" ]]; then
            echo -e "  ${YELLOW}$cmd${NC} → ${RED}(To be implemented)${NC}"
        else
            echo -e "  ${GREEN}$cmd${NC} → ${BLUE}$script_path${NC} (${execution_method})"
        fi
        echo "      $description"
        echo ""
    done

    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo ""
    echo -e "${BLUE}Infrastructure Management:${NC}"
    echo "    ./noah infra --list-charts           # List all available Helm charts"
    echo "    ./noah infra --dry-run               # See what would be deployed"
    echo "    ./noah infra --priority-only         # Deploy only priority infrastructure"
    echo "    ./noah infra --namespace mynoah      # Deploy to custom namespace"
    echo "    ./noah infra --timeout 900s          # Use custom timeout"
    echo ""
    echo -e "${BLUE}Monitoring Operations:${NC}"
    echo "    ./noah monitoring deploy             # Deploy monitoring stack"
    echo "    ./noah monitoring status             # Check monitoring health"
    echo "    ./noah monitoring teardown           # Remove monitoring infrastructure"
    echo "    ./noah monitoring status --save-report  # Save status to file"
    echo "    ./noah monitoring deploy -e prod     # Deploy for production"
    echo ""
    echo -e "${BLUE}Code Quality & Fixes:${NC}"
    echo "    ./noah fix --verbose                 # Fix issues with detailed output"
    echo "    ./noah fix -t yaml                   # Fix only YAML files"
    echo "    ./noah fix --dry-run                 # Preview fixes without applying"
    echo "    ./noah fix myfile.yml                # Fix specific file"
    echo ""
    echo -e "${BLUE}Linting Operations:${NC}"
    echo "    ./noah linting setup                 # Setup linting environment"
    echo "    ./noah linting lint                  # Run linting on changed files"
    echo "    ./noah linting lint --all            # Run linting on all files"
    echo "    ./noah linting report --save         # Generate and save linting report"
    echo "    ./noah linting precommit             # Run pre-commit hooks"
    echo ""
    echo -e "${BLUE}Dependencies & Setup:${NC}"
    echo "    ./noah deps --auto-install           # Auto-install missing dependencies"
    echo "    ./noah deps --upgrade                # Upgrade all dependencies"
    echo "    ./noah deps --check-security         # Check for security vulnerabilities"
    echo "    ./noah deps --report                 # Generate dependency report"
    echo "    ./noah setup --profile root          # Setup for root deployment"
    echo "    ./noah setup --dev                   # Include development dependencies"
    echo "    ./noah requirements --profile minimal  # Validate minimal requirements"
    echo ""
    echo -e "${YELLOW}GLOBAL OPTIONS:${NC}"
    echo "    -v, --verbose     Enable verbose output"
    echo "    -h, --help       Show this help message"
    echo "    --version        Show version information"
    echo "    --force-root     Force non-interactive root privilege check"
    echo ""
    echo -e "${YELLOW}ROOT PRIVILEGES:${NC}"
    echo "    Some commands (infra, monitoring, deps, setup) require root privileges."
    echo "    The script will automatically prompt for sudo when needed."
    echo "    Use --force-root for non-interactive environments."
    echo ""
    echo -e "${YELLOW}For command-specific help, run:${NC}"
    echo "    ./noah COMMAND --help"
    echo ""
}

# =============================================================================
# SCRIPT VALIDATION AND EXECUTION
# =============================================================================

# Validate script exists and is executable
check_script() {
    local script_path="$1"
    local script_name="$2"

    # Check if script exists
    if [[ ! -f "$script_path" ]]; then
        print_error "Script not found: $script_path"
        print_info "Available scripts in $SCRIPT_DIR:"
        ls -la "$SCRIPT_DIR" | grep -E "(noah-|\.py$|\.sh$)" || echo "No scripts found"
        return 1
    fi

    # Make script executable if needed
    if [[ ! -x "$script_path" ]]; then
        print_warning "Making script executable: $script_name"
        chmod +x "$script_path" || {
            print_error "Failed to make script executable: $script_path"
            return 1
        }
    fi

    return 0
}

# Execute script with proper method
execute_script() {
    local script_path="$1"
    local execution_method="$2"
    local script_name="$3"
    shift 3

    print_info "Executing: $script_name"

    case "$execution_method" in
        "python3")
            if ! command -v python3 &> /dev/null; then
                print_error "Python 3 is required but not installed"
                return 1
            fi
            exec python3 "$script_path" "$@"
            ;;
        "bash")
            exec bash "$script_path" "$@"
            ;;
        "direct")
            exec "$script_path" "$@"
            ;;
        *)
            print_error "Unknown execution method: $execution_method"
            return 1
            ;;
    esac
}

# =============================================================================
# COMMAND ROUTING
# =============================================================================

# Main command dispatcher
route_command() {
    local command="$1"
    shift

    # Check if command exists in mapping
    if [[ -z "${SCRIPT_COMMANDS[$command]:-}" ]]; then
        print_error "Unknown command: $command"
        echo ""
        print_info "Available commands:"
        for cmd in "${!SCRIPT_COMMANDS[@]}"; do
            IFS=':' read -r script_path execution_method description <<< "${SCRIPT_COMMANDS[$cmd]}"
            echo "  $cmd - $description"
        done
        echo ""
        echo "Run './noah --help' for detailed usage information"
        return 1
    fi

    # Check root privileges if needed for this command (skip for --help)
    if [[ "$1" != "--help" && "$1" != "-h" ]]; then
        check_root_privileges "$command" "$@"
    fi

    # Parse command information
    IFS=':' read -r script_path execution_method description <<< "${SCRIPT_COMMANDS[$command]}"

    # Handle placeholder commands
    if [[ "$execution_method" == "placeholder" ]]; then
        print_warning "Command '$command' is not yet implemented"
        print_info "$description"
        return 0
    fi

    # Build full script path
    local full_script_path="$SCRIPT_DIR/$script_path"

    # Validate and execute script
    if check_script "$full_script_path" "$script_path"; then
        execute_script "$full_script_path" "$execution_method" "$command" "$@"
    else
        print_error "Failed to execute command: $command"
        return 1
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Handle no arguments
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi

    # Global flags
    local force_root_check=false

    # Parse global options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version|--version)
                echo "NOAH CLI v$SCRIPT_VERSION"
                echo "Script: $SCRIPT_NAME"
                echo "Description: $SCRIPT_DESCRIPTION"
                exit 0
                ;;
            --force-root)
                force_root_check=true
                shift
                continue
                ;;
            -*)
                print_error "Unknown global option: $1"
                print_info "Use './noah --help' for usage information"
                exit 1
                ;;
            *)
                # First non-option argument is the command
                break
                ;;
        esac
        shift
    done

    # Get command
    local command="$1"
    shift

    # Use non-interactive root check if --force-root is specified
    if [[ "$force_root_check" == "true" ]]; then
        ensure_root_privileges "$command"
    fi

    # Route to appropriate script
    if ! route_command "$command" "$@"; then
        print_error "Command execution failed: $command"
        exit 1
    fi
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Execute main function with all arguments
main "$@"
