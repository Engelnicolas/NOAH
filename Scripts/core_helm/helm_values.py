#!/usr/bin/env python3
"""Helm values generation utilities for NOAH services.

Extracted from noah.py to reduce main CLI size and centralize Helm values logic.

Provides:
    get_helm_values_for_service(service: str, namespace: str, domain: str) -> dict
"""
from __future__ import annotations

from Scripts.security import get_security_config  # type: ignore
from Scripts.utils.config_loader import ConfigLoader  # type: ignore


def get_helm_values_for_service(service: str, namespace: str, domain: str):
    """Generate Helm values for a specific service with enhanced ConfigLoader support.

    Resolution order:
      1. If service is registered in ConfigLoader.service_configs => delegate to ConfigLoader.generate_helm_values
      2. Fallback: construct legacy values (backward compatibility)
    """
    config_loader = ConfigLoader()

    # nginx-ingress: dedicated values generation (not a standard ingress-backed service)
    if service == 'nginx-ingress':
        return config_loader.get_nginx_ingress_helm_values()

    # Preferred dynamic path via ConfigLoader
    if service in config_loader.service_configs:
        return config_loader.generate_helm_values(service)

    security_config = get_security_config(domain)

    base_values = {
        'global': {
            'domain': domain,
            'namespace': namespace
        },
        'security': security_config,
        'secrets': {
            'enabled': security_config['secrets']['age']['enabled'],
            'managed': True,
            'backend': 'sops',
            'age': {
                'enabled': security_config['secrets']['age']['enabled'],
                'publicKey': security_config['secrets']['age']['public_key_path']
            }
        },
        'tls': {
            'enabled': security_config['certificates']['enabled'],
            'domain': domain,
            'selfSigned': True,
            'certificateSecret': f"{service}-tls",
            'ca': {
                'enabled': True,
                'secretName': 'noah-ca-certificate'
            }
        }
    }

    if service == 'authentik':
        base_values.update({
            'authentik': {
                'secret_key': {
                    'secretName': 'authentik-secret',
                    'secretKey': 'secret-key'
                },
                'postgresql': {
                    'password': {
                        'secretName': 'authentik-postgresql',
                        'secretKey': 'password'
                    }
                },
                'redis': {
                    'password': {
                        'secretName': 'authentik-redis',
                        'secretKey': 'password'
                    }
                }
            },
            'ingress': {
                'enabled': True,
                'hosts': [{
                    'host': f"auth.{domain}",
                    'paths': [{
                        'path': '/',
                        'pathType': 'Prefix'
                    }]
                }],
                'tls': [{
                    'secretName': 'authentik-tls',
                    'hosts': [f"auth.{domain}"]
                }]
            }
        })
    elif service == 'cilium':
        base_values.update({
            'hubble': {
                'relay': {
                    'enabled': True,
                    'tls': {
                        'server': {
                            'enabled': True,
                            'secretName': 'hubble-server-certs'
                        }
                    }
                },
                'ui': {
                    'enabled': True,
                    'ingress': {
                        'enabled': True,
                        'hosts': [f"hubble.{domain}"],
                        'tls': [{
                            'secretName': 'hubble-ui-tls',
                            'hosts': [f"hubble.{domain}"]
                        }]
                    }
                }
            }
        })

    return base_values
