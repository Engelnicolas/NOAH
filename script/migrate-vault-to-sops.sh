#!/bin/bash
# Migration automatique d'Ansible Vault vers SOPS
# NOAH Platform - Migration des secrets

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
step() { echo -e "${CYAN}[STEP]${NC} $1"; }

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Migration Ansible Vault → SOPS                 ║"
echo "║                    NOAH Platform                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

step "Migration des secrets de Ansible Vault vers SOPS..."

# Vérifications préalables
if [[ ! -f "ansible/vars/secrets.yml" ]]; then
    error "Fichier secrets Ansible non trouvé"
    exit 1
fi

if [[ ! -f "ansible/.vault_pass" ]]; then
    error "Fichier de mot de passe Ansible Vault non trouvé"
    exit 1
fi

if ! command -v sops >/dev/null 2>&1; then
    error "SOPS n'est pas installé"
    exit 1
fi

# Sauvegarder le fichier actuel
step "Sauvegarde du fichier existant..."
cp ansible/vars/secrets.yml ansible/vars/secrets.yml.backup
success "Sauvegarde créée: ansible/vars/secrets.yml.backup"

# Déchiffrer avec Ansible Vault
step "Déchiffrement avec Ansible Vault..."
if ansible-vault decrypt ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass; then
    success "Fichier déchiffré avec succès"
else
    error "Échec du déchiffrement Ansible Vault"
    exit 1
fi

# Chiffrer avec SOPS
step "Chiffrement avec SOPS..."
if sops --encrypt --in-place ansible/vars/secrets.yml; then
    success "Fichier chiffré avec SOPS"
else
    error "Échec du chiffrement SOPS"
    # Restaurer le fichier original
    mv ansible/vars/secrets.yml.backup ansible/vars/secrets.yml
    exit 1
fi

# Mettre à jour ansible.cfg pour supprimer vault_password_file
step "Mise à jour de la configuration Ansible..."
if grep -q "vault_password_file" ansible/ansible.cfg; then
    sed -i '/vault_password_file = .vault_pass/d' ansible/ansible.cfg
    success "Configuration Ansible mise à jour"
else
    info "Configuration Ansible déjà à jour"
fi

# Supprimer le fichier de mot de passe
step "Nettoyage des fichiers Ansible Vault..."
if [[ -f "ansible/.vault_pass" ]]; then
    rm ansible/.vault_pass
    success "Fichier .vault_pass supprimé"
fi

# Mettre à jour le fichier .gitignore
step "Mise à jour .gitignore..."
if grep -q "ansible/.vault_pass" .gitignore 2>/dev/null; then
    sed -i '/ansible\/.vault_pass/d' .gitignore
    success ".gitignore mis à jour"
fi

echo ""
success "🎉 Migration terminée avec succès!"
echo ""
info "Actions effectuées:"
info "  ✅ Secrets déchiffrés d'Ansible Vault"
info "  ✅ Secrets rechiffrés avec SOPS"
info "  ✅ Configuration Ansible mise à jour"
info "  ✅ Fichiers de mot de passe supprimés"
echo ""
info "Actions recommandées:"
info "  1. Tester: sops -d ansible/vars/secrets.yml"
info "  2. Vérifier: ansible-playbook --syntax-check playbooks/*.yml"
info "  3. Valider: ./noah.sh secrets validate"
echo ""
warning "La sauvegarde est disponible: ansible/vars/secrets.yml.backup"
