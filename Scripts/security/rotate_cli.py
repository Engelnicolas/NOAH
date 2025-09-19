#!/usr/bin/env python3
"""Commande CLI pour rotation des secrets canoniques.

Sépare la logique de rotation depuis noah.py afin d'alléger le fichier principal.
"""
import click  # type: ignore
from Scripts.security import ensure_security_initialized  # type: ignore
from Scripts.security.canonical_store import get_canonical_store  # type: ignore


def register_rotate_command(secrets_group):
    """Enregistre la commande rotate sur le groupe secrets.

    Args:
        secrets_group: objet Click group (secrets)
    """

    @secrets_group.command(name='rotate')  # type: ignore
    @click.option('--service', required=True, help='Service dont on veut faire tourner les secrets (authentik, cilium, etc)')
    @click.option('--keys', help='Liste de clés spécifiques séparées par des virgules (défaut: toutes)')
    @click.option('--show', is_flag=True, help='Afficher les métadonnées après rotation (valeurs masquées)')
    @click.pass_context
    def rotate_canonical(ctx, service, keys, show):  # noqa: D401
        """Fait tourner un ou plusieurs secrets (store canonique)."""
        ensure_security_initialized(ctx)
        key_list = [k.strip() for k in keys.split(',')] if keys else None
        rotated = ctx.obj['secrets'].rotate_service_secrets_canonical(service, key_list)
        if not rotated:
            click.echo(f"❌ Aucune rotation effectuée pour {service}")
            return
        click.echo(f"✅ Rotation effectuée pour {service}: {', '.join(key_list) if key_list else 'TOUTES les clés'}")
        if show:
            store = get_canonical_store()
            svc = store.data.get('services', {}).get(service, {})
            click.echo(f"\n[{service} mis à jour]")
            for k, v in sorted(svc.items()):
                if isinstance(v, dict) and 'value' in v:
                    display_val = (v['value'][:4] + '...') if v.get('value') else ''
                    click.echo(f"  {k}: {display_val} (v{v.get('version')} rotated:{v.get('rotated_at')})")
                else:
                    display_val = (v[:4] + '...') if v else ''
                    click.echo(f"  {k}: {display_val}")

    return rotate_canonical
