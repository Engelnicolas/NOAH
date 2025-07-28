# Configuration des domaines pour NOAH
# Ce fichier vous aide à configurer vos domaines selon votre environnement

## 🏠 Configuration pour environnement local/développement

### Option 1 : Domaines .local (recommandé pour dev)
```yaml
global:
  domain: noah.local
  
# Applications accessibles via :
# - https://keycloak.noah.local
# - https://gitlab.noah.local  
# - https://nextcloud.noah.local
# - https://mattermost.noah.local
# - https://grafana.noah.local
```

### Option 2 : Domaines avec IP (pour tests rapides)
```yaml
global:
  domain: 192-168-1-100.nip.io    # Remplacez 192-168-1-100 par votre IP d'ingress
  
# Applications accessibles via :
# - https://keycloak.192-168-1-100.nip.io
# - https://gitlab.192-168-1-100.nip.io
```

## 🌐 Configuration pour environnement de production

### Option 3 : Domaine d'entreprise
```yaml
global:
  domain: noah.mycompany.com
  
# Applications accessibles via :
# - https://keycloak.noah.mycompany.com
# - https://gitlab.noah.mycompany.com
# - https://nextcloud.noah.mycompany.com
```

### Option 4 : Sous-domaines séparés
```yaml
# Dans ce cas, configurez chaque service individuellement :
keycloak:
  ingress:
    hostname: auth.mycompany.com
    
gitlab:
  global:
    hosts:
      gitlab:
        name: git.mycompany.com
        
nextcloud:
  nextcloud:
    host: files.mycompany.com
```

## 🔧 Configuration DNS requise

### Pour domaines .local (développement)
Ajoutez à votre /etc/hosts :
```bash
# Remplacez INGRESS_IP par l'IP de votre ingress controller
INGRESS_IP keycloak.noah.local
INGRESS_IP gitlab.noah.local
INGRESS_IP nextcloud.noah.local
INGRESS_IP mattermost.noah.local
INGRESS_IP grafana.noah.local
```

### Pour domaines publics (production)
Configurez vos enregistrements DNS :
```
Type  | Nom                    | Valeur
------|------------------------|------------------
A     | keycloak.noah.company  | IP_INGRESS
A     | gitlab.noah.company    | IP_INGRESS
A     | nextcloud.noah.company | IP_INGRESS
A     | mattermost.noah.company| IP_INGRESS
A     | grafana.noah.company   | IP_INGRESS
```

## 🔐 Configuration SSL/TLS

### Let's Encrypt automatique (recommandé)
```yaml
# Déjà configuré dans values-prod.yaml
annotations:
  cert-manager.io/cluster-issuer: letsencrypt-prod
```

### Certificats personnalisés
```yaml
# Stockez vos certificats dans Ansible Vault (secrets.yml)
vault_tls_cert: |
  -----BEGIN CERTIFICATE-----
  Votre certificat SSL ici
  -----END CERTIFICATE-----
  
vault_tls_key: |
  -----BEGIN PRIVATE KEY-----
  Votre clé privée SSL ici  
  -----END PRIVATE KEY-----
```

## 🚀 Script de configuration rapide

Pour configurer automatiquement vos domaines :

```bash
#!/bin/bash
# Configuration rapide des domaines NOAH

DOMAIN="noah.local"                    # 🔧 Changez selon vos besoins
INGRESS_IP="192.168.1.100"            # 🔧 IP de votre ingress controller

echo "Configuration des domaines pour $DOMAIN..."

# Mise à jour du fichier values
sed -i "s/domain: noah.local/domain: $DOMAIN/g" values/values-prod.yaml

# Mise à jour du /etc/hosts pour dev local
if [[ "$DOMAIN" == *.local ]]; then
    echo "Ajout des entrées DNS locales..."
    sudo tee -a /etc/hosts << EOF
$INGRESS_IP keycloak.$DOMAIN
$INGRESS_IP gitlab.$DOMAIN
$INGRESS_IP nextcloud.$DOMAIN
$INGRESS_IP mattermost.$DOMAIN
$INGRESS_IP grafana.$DOMAIN
EOF
fi

echo "✅ Configuration terminée pour $DOMAIN"
```
