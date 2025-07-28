#!/usr/bin/env python3
"""
Script pour corriger la syntaxe des templates Helm.
Remplace { { par {{ et } } par }} dans tous les fichiers template.
"""

import os
import re
from pathlib import Path


def fix_helm_templates():
    """Corrige la syntaxe des templates Helm."""
    helm_dir = Path(__file__).parent.parent / "helm"

    # Pattern pour trouver les mauvaises syntaxes
    pattern_open = re.compile(r'{ {')
    pattern_close = re.compile(r'} }')

    fixed_files = []

    # Parcourir tous les fichiers template
    for template_file in helm_dir.rglob("templates/*.yaml"):
        print(f"Vérification: {template_file}")

        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Corriger les syntaxes
            content = pattern_open.sub('{{', content)
            content = pattern_close.sub('}}', content)

            # Sauvegarder si modifié
            if content != original_content:
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(template_file)
                print(f"✅ Corrigé: {template_file}")

        except Exception as e:
            print(f"❌ Erreur avec {template_file}: {e}")

    print(f"\n🎉 {len(fixed_files)} fichiers corrigés:")
    for file in fixed_files:
        print(f"  - {file}")


if __name__ == "__main__":
    fix_helm_templates()
