#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH - Network Operations & Automation Hub
# Copyright (C) 2026 Nicolas Engel <contact@nicolasengel.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
    @click.option('--service', required=True, prompt='Service dont on veut faire tourner les secrets',
                  help='Service dont on veut faire tourner les secrets (authentik, cilium, etc)')
    @click.option('--keys', help='Liste de clés spécifiques séparées par des virgules (défaut: toutes)')
    @click.option('--show', is_flag=True, help='Afficher les métadonnées après rotation (valeurs masquées)')
    @click.option('--apply', 'do_apply', is_flag=True, help='Appliquer les secrets au cluster en cours (sans re-bootstrap)')
    @click.pass_context
    def rotate_canonical(ctx, service, keys, show, do_apply):  # noqa: D401
        """Fait tourner un ou plusieurs secrets (store canonique)."""
        ensure_security_initialized(ctx)
        key_list = [k.strip() for k in keys.split(',')] if keys else None
        rotated = ctx.obj['secrets'].rotate_service_secrets_canonical(service, key_list)
        if not rotated:
            click.echo(f"❌ Aucune rotation effectuée pour {service}")
            return
        click.echo(f"✅ Rotation effectuée pour {service}: {', '.join(key_list) if key_list else 'TOUTES les clés'}")
        if do_apply:
            from Scripts.gitops.gitops_init import apply_app_secrets
            try:
                apply_app_secrets(print_status=lambda m, lvl='INFO': click.echo(m))
                click.echo("✅ Secrets appliqués au cluster (aucun re-bootstrap nécessaire).")
            except Exception as e:  # noqa: BLE001
                click.echo(f"❌ Échec de l'application au cluster: {e}")
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
