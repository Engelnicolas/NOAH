import yaml
import sys

# Test the prometheus values.yaml file
try:
    with open('/home/nicolas/Documents/Infra open-source/NOAH/Helm/prometheus/values.yaml', 'r') as f:
        data = yaml.safe_load(f)
    print("✅ Prometheus values.yaml: VALID")
except Exception as e:
    print(f"❌ Prometheus values.yaml: ERROR - {e}")
    sys.exit(1)

# Test all chart files
charts = [
    'gitlab', 'grafana', 'keycloak', 'mattermost', 'nextcloud',
    'oauth2-proxy', 'openedr', 'prometheus', 'samba4', 'wazuh'
]

for chart in charts:
    try:
        # Test Chart.yaml
        with open(f'/home/nicolas/Documents/Infra open-source/NOAH/Helm/{chart}/Chart.yaml', 'r') as f:
            yaml.safe_load(f)
        
        # Test values.yaml
        with open(f'/home/nicolas/Documents/Infra open-source/NOAH/Helm/{chart}/values.yaml', 'r') as f:
            yaml.safe_load(f)
        
        print(f"✅ {chart}: VALID")
    except Exception as e:
        print(f"❌ {chart}: ERROR - {e}")

print("\n🎉 Helm chart validation complete!")
