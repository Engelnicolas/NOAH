"""
Test de base pour vérifier que l'environnement Python fonctionne correctement.
"""

import sys
from pathlib import Path

import pytest


def test_python_version():
    """Vérifie que la version de Python est correcte."""
    assert sys.version_info >= (3, 8), "Python 3.8+ est requis"


def test_noah_scripts_directory_exists():
    """Vérifie que le répertoire Script existe."""
    script_dir = Path(__file__).parent.parent / "Script"
    assert script_dir.exists(), "Le répertoire Script doit exister"


def test_requirements_file_exists():
    """Vérifie que le fichier requirements.txt existe."""
    requirements_file = Path(__file__).parent.parent / "Script" / "requirements.txt"
    assert requirements_file.exists(), "Le fichier requirements.txt doit exister"


def test_imports_basic_modules():
    """Teste l'importation des modules de base."""
    import json
    import os
    import sys

    import psutil
    import requests
    import yaml

    # Si on arrive ici, les imports ont réussi
    assert True


if __name__ == "__main__":
    pytest.main([__file__])
