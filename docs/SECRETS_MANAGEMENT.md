# Gestion des Secrets NOAH Platform avec SOPS

Ce document explique comment gérer les secrets dans le projet NOAH de manière sécurisée avec **SOPS** (Mozilla).

## 📋 Vue d'ensemble

Le projet NOAH utilise **SOPS (Secrets OPerationS)** avec **Age encryption** pour chiffrer les secrets sensibles. Cette approche moderne remplace Ansible Vault et offre une meilleure intégration GitOps. Tous les mots de passe, clés API, certificats et autres informations sensibles sont stockés dans le fichier `ansible/vars/secrets.yml` qui est automatiquement chiffré avec SOPS.

## 🔐 Architecture des secrets

### Fichiers principaux
- `ansible/vars/secrets.yml` - **Fichier principal des secrets (Chiffré SOPS)**
- `ansible/vars/global.yml` - Variables non sensibles
- `.sops.yaml` - Configuration SOPS (règles de chiffrement)
- `~/.config/sops/age/keys.txt` - Clés privées Age

### Templates de configuration
- `ansible/templates/keycloak-secrets.yml.j2` - Secrets Keycloak
- `ansible/templates/oauth2-proxy-secrets.yml.j2` - Secrets OAuth2 Proxy
- `ansible/templates/postgresql-secrets.yml.j2` - Secrets PostgreSQL
- `ansible/templates/tls-secrets.yml.j2` - Certificats TLS

## 🚀 Démarrage rapide

### 1. Installation SOPS & Age

```bash
# Installation automatique via le CLI NOAH
noah secrets status

# Ou installation manuelle
sudo apt update
sudo apt install age sops

# Vérifier l'installation
sops --version
age --version
```

### 2. Configuration initiale

```bash
# Générer une nouvelle paire de clés Age
age-keygen -o ~/.config/sops/age/keys.txt

# Extraire la clé publique
age-keygen -y ~/.config/sops/age/keys.txt

# Configuration .sops.yaml sera créée automatiquement
```

### 3. Éditer les secrets

```bash
# Édition directe avec SOPS (recommandé)
noah secrets edit

# Ou directement avec SOPS
sops ansible/vars/secrets.yml
```

### 4. Valider les secrets

```bash
# Validation complète avec diagnostic
noah secrets status

# Validation spécifique
noah secrets validate
```

## 🔧 Commandes SOPS via NOAH CLI

### Gestion moderne des secrets

```bash
# Éditer les secrets (chiffrement automatique)
noah secrets edit

# Voir le contenu déchiffré
noah secrets view

# Statut complet du système SOPS
noah secrets status

# Validation de la configuration
noah secrets validate

# Génération de nouveaux secrets
noah secrets generate

# Rotation des secrets
noah secrets rotate
```

### Commandes SOPS directes

```bash
# Éditer un fichier chiffré
sops ansible/vars/secrets.yml

# Voir le contenu sans modification
sops --decrypt ansible/vars/secrets.yml

# Chiffrer un nouveau fichier
sops --encrypt --in-place nouveau-fichier.yml

# Re-chiffrer avec nouvelles clés
sops --rotate --in-place ansible/vars/secrets.yml
```

## 🗂️ Catégories de secrets

### 🏗️ Infrastructure
- `vault_ssh_private_key` - Clé SSH pour l'accès aux serveurs
- `vault_ssh_public_key` - Clé SSH publique  
- `vault_cluster_name` - Nom du cluster (si différent du défaut)
- `vault_domain_name` - Domaine principal NOAH

### 🗄️ Bases de données
- `vault_postgres_password` - Mot de passe superutilisateur PostgreSQL
- `vault_noah_db_password` - Mot de passe base NOAH
- `vault_keycloak_db_password` - Mot de passe base Keycloak
- `vault_gitlab_db_password` - Mot de passe base GitLab
- `vault_nextcloud_db_password` - Mot de passe base Nextcloud
- `vault_mattermost_db_password` - Mot de passe base Mattermost
- `vault_grafana_db_password` - Mot de passe base Grafana
- `vault_redis_password` - Mot de passe Redis

### 🔐 Authentification (Keycloak)
- `vault_keycloak_admin_password` - Mot de passe admin Keycloak
- `vault_keycloak_client_secrets.*` - Secrets des clients OAuth2
- `vault_oauth2_proxy_client_id` - Client ID OAuth2 Proxy
- `vault_oauth2_proxy_client_secret` - Client Secret OAuth2 Proxy
- `vault_oauth2_proxy_cookie_secret` - Secret cookie OAuth2 Proxy

### 📱 Applications
- `vault_gitlab_root_password` - Mot de passe root GitLab
- `vault_gitlab_runner_token` - Token GitLab Runner
- `vault_nextcloud_admin_password` - Mot de passe admin Nextcloud
- `vault_mattermost_admin_password` - Mot de passe admin Mattermost
- `vault_mattermost_system_console_password` - Console système Mattermost
- `vault_grafana_admin_password` - Mot de passe admin Grafana

### 🛡️ Sécurité & Monitoring
- `vault_wazuh_manager_password` - Mot de passe Wazuh Manager
- `vault_wazuh_api_password` - API Wazuh
- `vault_openedr_admin_password` - Mot de passe admin OpenEDR
- `vault_openedr_api_key` - Clé API OpenEDR
- `vault_tls_cert` - Certificat TLS wildcard
- `vault_tls_key` - Clé privée TLS
- `vault_ca_cert` - Certificat CA interne

### 🔑 Chiffrement & Sessions
- `vault_jwt_secret` - Secret JWT global
- `vault_session_secret` - Secret de session
- `vault_encryption_key` - Clé de chiffrement données
- `vault_backup_encryption_key` - Clé chiffrement sauvegardes
- `vault_master_key` - Clé maître NOAH

### � Services externes
- `vault_smtp_username` - Utilisateur SMTP
- `vault_smtp_password` - Mot de passe SMTP  
- `vault_s3_access_key` - Clé d'accès S3
- `vault_s3_secret_key` - Clé secrète S3
- `vault_ldap_bind_password` - Mot de passe bind LDAP

## 🔒 Bonnes pratiques SOPS

### ✅ Avantages SOPS vs Ansible Vault

| Aspect | SOPS | Ansible Vault |
|--------|------|---------------|
| **Chiffrement** | Valeurs individuelles | Fichier complet |
| **Git diff** | ✅ Possible | ❌ Impossible |
| **Gestion clés** | Age/GPG standard | Mot de passe unique |
| **GitOps** | ✅ Natif | ❌ Complexe |
| **Rotation** | ✅ Simple | ❌ Compliquée |
| **Audit** | ✅ Par valeur | ❌ Global |
| **Intégration CI/CD** | ✅ Transparente | ❌ Manuelle |

### ✅ À faire avec SOPS

1. **Utiliser Age encryption** - Plus simple que GPG
2. **Chiffrement par valeur** - Seuls les secrets sont chiffrés
3. **Commits transparents** - Les diffs Git sont lisibles
4. **Clés sauvegardées** - Backup des clés Age privées
5. **Configuration centralisée** - .sops.yaml pour tous les fichiers
6. **Rotation régulière** - `sops --rotate` pour nouvelles clés
7. **Validation automatique** - Tests CI/CD intégrés

### ❌ À éviter

1. **Ne jamais** committer les clés privées Age
2. **Ne jamais** partager ~/.config/sops/age/keys.txt
3. **Ne pas** éditer le fichier .yml chiffré manuellement
4. **Ne pas** utiliser GPG si Age suffit
5. **Ne pas** oublier de sauvegarder les clés Age
6. **Ne pas** ignorer les erreurs de déchiffrement

## 🔄 Rotation des secrets avec SOPS

### Planification automatisée
- **Critique** (DB, admin) : Tous les 3 mois
- **Standard** (applications) : Tous les 6 mois  
- **Clés Age** : Tous les 12 mois
- **Certificats** : Selon expiration

### Procédure de rotation moderne

```bash
# 1. Status avant rotation
noah secrets status

# 2. Rotation des clés Age (si nécessaire)
sops --rotate --in-place ansible/vars/secrets.yml

# 3. Rotation des secrets applicatifs
noah secrets rotate

# 4. Validation de la nouvelle configuration
noah secrets validate

# 5. Test de déploiement
noah deploy --dry-run

# 6. Déploiement des nouveaux secrets
noah deploy
```

### Rotation des clés Age

```bash
# Générer nouvelles clés Age
age-keygen -o ~/.config/sops/age/keys-new.txt

# Extraire la nouvelle clé publique
NEW_KEY=$(age-keygen -y ~/.config/sops/age/keys-new.txt)

# Mettre à jour .sops.yaml avec la nouvelle clé
# Puis re-chiffrer le fichier
sops --rotate --in-place ansible/vars/secrets.yml

# Remplacer l'ancienne clé
mv ~/.config/sops/age/keys-new.txt ~/.config/sops/age/keys.txt
```

## 🚨 Gestion des incidents SOPS

### Si les clés Age sont perdues

1. **Si backup disponible** : Restaurer depuis la sauvegarde
2. **Si pas de backup** : Régénérer complètement
3. **Procédure de récupération** :
   ```bash
   # Générer nouvelles clés Age
   age-keygen -o ~/.config/sops/age/keys.txt
   
   # Extraire la clé publique
   NEW_KEY=$(age-keygen -y ~/.config/sops/age/keys.txt)
   
   # Mettre à jour .sops.yaml avec la nouvelle clé
   # Puis régénérer tous les secrets
   noah secrets generate
   
   # Redéployer complètement
   noah deploy
   ```

### Si secrets.yml compromis

1. **Immédiatement** : Changer tous les mots de passe
2. **Audit** : Vérifier les logs d'accès
3. **Rotation complète** :
   ```bash
   # Rotation immédiate de tous les secrets
   noah secrets rotate
   
   # Validation
   noah secrets validate
   
   # Re-déploiement sécurisé
   noah deploy
   ```
4. **Post-incident** : Analyser les causes et renforcer la sécurité

### Perte d'accès au cluster

```bash
# Vérifier la configuration SOPS
noah secrets status

# Test de déchiffrement
noah secrets view

# Re-génération si nécessaire
noah secrets generate

# Test de connectivité
noah test
```

## 🧪 Tests et validation SOPS

### Tests automatiques avec NOAH CLI

```bash
# Diagnostic complet du système SOPS
noah secrets status

# Validation de la configuration des secrets
noah secrets validate

# Test de déchiffrement
noah secrets view >/dev/null && echo "✅ Déchiffrement OK"

# Test de rotation
noah secrets rotate --dry-run
```

### Tests SOPS directs

```bash
# Validation de la configuration SOPS
sops --config .sops.yaml

# Test de déchiffrement
sops --decrypt ansible/vars/secrets.yml >/dev/null && echo "✅ SOPS OK"

# Vérification des clés Age
ls -la ~/.config/sops/age/keys.txt

# Test d'édition
sops --decrypt ansible/vars/secrets.yml | head -5
```

### Tests d'intégration

```bash
# Test avec Ansible
ansible-playbook --syntax-check ansible/main.yml

# Test avec Helm (si plugin helm-secrets installé)
helm secrets view helm/keycloak/values.yaml

# Test de déploiement dry-run
noah deploy --dry-run
```

### Tests de connectivité applicative

```bash
# Test des bases de données
kubectl exec -it postgresql-0 -- psql -U noah -d noah -c "SELECT version();"

# Test Keycloak
curl -k https://keycloak.noah.local/realms/noah/.well-known/openid_configuration

# Test applications
noah test
```

## 🔧 Migration depuis Ansible Vault

Si vous avez encore des fichiers Ansible Vault, voici comment migrer :

### Migration automatique

```bash
# Utiliser le script de migration fourni
./script/deprecated-shell-secrets/migrate-to-sops.sh

# Ou migration manuelle étape par étape
```

### Migration manuelle

```bash
# 1. Déchiffrer l'ancien fichier Ansible Vault
ansible-vault decrypt ansible/vars/secrets.yml

# 2. Configurer SOPS pour ce fichier
# (Assurer que .sops.yaml existe)

# 3. Chiffrer avec SOPS
sops --encrypt --in-place ansible/vars/secrets.yml

# 4. Vérifier que le chiffrement SOPS fonctionne
noah secrets validate

# 5. Supprimer l'ancien mot de passe vault
rm -f ansible/.vault_pass

# 6. Tester le déploiement
noah deploy --dry-run
```

## 🔄 Intégration GitOps

### Avantages SOPS pour GitOps

- **Diffs lisibles** : Git peut montrer les changements de structure
- **Merge simplifié** : Pas de conflits binaires comme avec Ansible Vault
- **Audit trail** : Historique des modifications par secret
- **CI/CD natif** : Intégration transparente avec les pipelines

### Configuration ArgoCD (exemple)

```yaml
# argocd-repo-server configmap
data:
  sops.age.key: |
    # AGE-SECRET-KEY-1...
    # (clé Age privée pour ArgoCD)
```

### Configuration GitLab CI (exemple)

```yaml
# .gitlab-ci.yml
variables:
  SOPS_AGE_KEY_FILE: /tmp/sops-age-key

before_script:
  - echo "$SOPS_AGE_KEY" > $SOPS_AGE_KEY_FILE
  - chmod 600 $SOPS_AGE_KEY_FILE

deploy:
  script:
    - noah secrets validate
    - noah deploy
```

## 📚 Ressources supplémentaires

### Documentation officielle
- [SOPS Documentation](https://github.com/mozilla/sops)
- [Age Encryption](https://age-encryption.org/)
- [Helm-Secrets Plugin](https://github.com/jkroepke/helm-secrets)

### Guides NOAH spécifiques
- `docs/SOPS_INTEGRATION.md` - Guide détaillé d'intégration SOPS
- `docs/NOAH_CLI_SOPS_REFACTORING.md` - Migration du CLI vers SOPS
- `script/deprecated-shell-secrets/` - Scripts de migration

### Sécurité et standards
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Insufficient_Cryptography)
- [Kubernetes Secrets Best Practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [GitOps Security Best Practices](https://www.weave.works/technologies/gitops/)

## 📞 Support et dépannage

### Problèmes courants

1. **SOPS non installé** : `noah secrets status` puis suivre les instructions
2. **Clés Age manquantes** : Régénérer avec `age-keygen`
3. **Configuration .sops.yaml** : Vérifier les règles de chiffrement
4. **Permissions** : `chmod 600 ~/.config/sops/age/keys.txt`

### Démarche de dépannage

```bash
# 1. Diagnostic complet
noah secrets status

# 2. Validation configuration
noah secrets validate

# 3. Test de déchiffrement
noah secrets view | head -5

# 4. Vérification logs
noah logs --service keycloak

# 5. Test déploiement
noah deploy --dry-run
```

### Aide experte

En cas de problème complexe :

1. **Consulter** les logs détaillés avec `noah secrets status`
2. **Vérifier** la configuration dans `docs/SOPS_INTEGRATION.md`
3. **Tester** en mode dry-run avec `noah deploy --dry-run`
4. **Examiner** les fichiers de migration dans `script/deprecated-shell-secrets/`

---

🔐 **NOUVELLE APPROCHE SOPS** : Chiffrement moderne, GitOps-ready, et maintien transparent. Plus besoin de gérer des mots de passe vault - SOPS et Age encryption s'occupent de tout !
