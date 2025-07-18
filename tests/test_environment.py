"""Test de base pour vérifier que l'environnement Python fonctionne correctement."""

import sys
from pathlib import Path

import pytest


def test_python_version():
    """Vérifie que la version de Python est correcte."""
    assert sys.version_info >= (3, 8), "Python 3.8+ est requis"


def test_noah_scripts_directory_exists():
    """Vérifie que le répertoire script existe."""
    script_dir = Path(__file__).parent.parent / "script"
    assert script_dir.exists(), "Le répertoire script doit exister"


def test_requirements_file_exists():
    """Vérifie que le fichier requirements.txt existe."""
    requirements_file = Path(__file__).parent.parent / "script" / "requirements.txt"
    assert requirements_file.exists(), "Le fichier requirements.txt doit exister"


def test_imports_basic_modules():
    """Teste l'importation des modules de base."""
    try:
        import json  # noqa: F401
        import os  # noqa: F401
        import sys  # noqa: F401

        import psutil  # noqa: F401
        import requests  # noqa: F401
        import yaml  # noqa: F401
    except ImportError as e:
        pytest.fail(f"Échec de l'import d'un module requis: {e}")

    # Si on arrive ici, les imports ont réussi
    assert True


if __name__ == "__main__":
    pytest.main([__file__])
