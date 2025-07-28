#!/usr/bin/env python3
"""
Script pour formater automatiquement tous les fichiers Python du projet NOAH
avec Black, isort et autopep8 pour une mise en forme cohérente.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


class PythonFormatter:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.formatted_count = 0
        self.error_count = 0
        self.skipped_count = 0

    def print_banner(self):
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("██████╗ ██╗   ██╗████████╗██╗  ██╗ ██████╗ ███╗   ██╗")
        print("██╔══██╗╚██╗ ██╔╝╚══██╔══╝██║  ██║██╔═══██╗████╗  ██║")
        print("██████╔╝ ╚████╔╝    ██║   ███████║██║   ██║██╔██╗ ██║")
        print("██╔═══╝   ╚██╔╝     ██║   ██╔══██║██║   ██║██║╚██╗██║")
        print("██║        ██║      ██║   ██║  ██║╚██████╔╝██║ ╚████║")
        print("╚═╝        ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝")
        print(f"{Colors.END}")
        print(f"{Colors.BOLD}NOAH Python Formatter{Colors.END}")
        print("=" * 60)

    def find_python_files(self) -> List[Path]:
        """Trouve tous les fichiers Python dans le projet."""
        python_files = []

        # Répertoires à exclure
        exclude_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
            "build",
            "dist",
            ".pytest_cache",
            ".tox",
            "env",
        }

        for py_file in self.project_root.rglob("*.py"):
            # Vérifier que le fichier n'est pas dans un répertoire exclu
            if not any(excluded in py_file.parts for excluded in exclude_dirs):
                python_files.append(py_file)

        return sorted(python_files)

    def check_tool_availability(self) -> bool:
        """Vérifie que les outils de formatage sont disponibles."""
        tools = {
            "black": "pip install black",
            "isort": "pip install isort",
            "autopep8": "pip install autopep8",
        }

        all_available = True
        for tool, install_cmd in tools.items():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", tool, "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"  {Colors.GREEN}✓{Colors.END} {tool} disponible")
                else:
                    print(
                        f"  {
                            Colors.RED}✗{
                            Colors.END} {tool} non disponible - {install_cmd}"
                    )
                    all_available = False
            except FileNotFoundError:
                print(
                    f"  {
                        Colors.RED}✗{
                        Colors.END} {tool} non disponible - {install_cmd}"
                )
                all_available = False

        return all_available

    def install_tools(self) -> bool:
        """Installe automatiquement les outils de formatage."""
        tools = ["black", "isort", "autopep8"]

        print(f"{Colors.YELLOW}Installation des outils de formatage...{Colors.END}")

        for tool in tools:
            try:
                print(f"  Installation de {tool}...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", tool],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"    {Colors.GREEN}✓{Colors.END} {tool} installé")
                else:
                    print(
                        f"    {
                            Colors.RED}✗{
                            Colors.END} Échec d'installation de {tool}"
                    )
                    print(f"    {result.stderr}")
                    return False
            except Exception as e:
                print(
                    f"    {
                        Colors.RED}✗{
                        Colors.END} Erreur lors de l'installation de {tool}: {e}"
                )
                return False

        return True

    def format_with_autopep8(self, file_path: Path) -> bool:
        """Formate un fichier avec autopep8 (corrections PEP8 de base)."""
        try:
            cmd = [
                sys.executable,
                "-m",
                "autopep8",
                "--in-place",
                "--aggressive",
                "--aggressive",
                "--max-line-length=88",  # Compatible avec Black
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            print(f"    {Colors.RED}✗{Colors.END} Erreur autopep8: {e}")
            return False

    def format_with_isort(self, file_path: Path) -> bool:
        """Formate les imports avec isort."""
        try:
            cmd = [
                sys.executable,
                "-m",
                "isort",
                "--profile=black",  # Compatible avec Black
                "--line-length=88",
                "--multi-line=3",
                "--trailing-comma",
                "--force-grid-wrap=0",
                "--combine-as",
                "--split-on-trailing-comma",
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            print(f"    {Colors.RED}✗{Colors.END} Erreur isort: {e}")
            return False

    def format_with_black(self, file_path: Path) -> bool:
        """Formate un fichier avec Black."""
        try:
            cmd = [
                sys.executable,
                "-m",
                "black",
                "--line-length=88",
                "--target-version=py38",
                "--skip-string-normalization",  # Préserver les quotes existantes
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            print(f"    {Colors.RED}✗{Colors.END} Erreur Black: {e}")
            return False

    def format_python_file(self, file_path: Path) -> bool:
        """Formate un fichier Python avec tous les outils."""
        try:
            print(
                f"  {
                    Colors.BLUE}Formatting:{
                    Colors.END} {
                    file_path.relative_to(
                        self.project_root)}"
            )

            # Vérifier que le fichier est syntaxiquement correct
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), file_path, 'exec')
            except SyntaxError as e:
                print(f"    {Colors.RED}✗{Colors.END} Erreur de syntaxe Python: {e}")
                return False

            success = True

            # 1. Autopep8 pour les corrections PEP8 de base
            if not self.format_with_autopep8(file_path):
                success = False

            # 2. isort pour organiser les imports
            if not self.format_with_isort(file_path):
                success = False

            # 3. Black pour le formatage final
            if not self.format_with_black(file_path):
                success = False

            if success:
                print(f"    {Colors.GREEN}✓{Colors.END} Successfully formatted")
                return True
            else:
                print(f"    {Colors.YELLOW}⚠{Colors.END} Partially formatted")
                return False

        except Exception as e:
            print(f"    {Colors.RED}✗{Colors.END} Error: {e}")
            return False

    def format_all(self) -> None:
        """Formate tous les fichiers Python du projet."""
        self.print_banner()

        print(f"{Colors.CYAN}Vérification des outils de formatage...{Colors.END}")
        if not self.check_tool_availability():
            print(f"{Colors.YELLOW}Tentative d'installation automatique...{Colors.END}")
            if not self.install_tools():
                print(
                    f"{Colors.RED}Impossible d'installer les outils requis.{Colors.END}"
                )
                print(f"{Colors.YELLOW}Installez manuellement:{Colors.END}")
                print("  pip install black isort autopep8")
                return

        print(f"{Colors.CYAN}Recherche des fichiers Python...{Colors.END}")
        python_files = self.find_python_files()

        if not python_files:
            print(f"{Colors.YELLOW}Aucun fichier Python trouvé.{Colors.END}")
            return

        print(f"{Colors.CYAN}Trouvé {len(python_files)} fichiers Python{Colors.END}")
        print()

        for file_path in python_files:
            if self.format_python_file(file_path):
                self.formatted_count += 1
            else:
                self.error_count += 1

        # Résumé
        print()
        print(f"{Colors.BOLD}FORMATTING SUMMARY{Colors.END}")
        print("=" * 50)
        print(f"Total files: {len(python_files)}")
        print(
            f"{Colors.GREEN}Successfully formatted: {self.formatted_count}{Colors.END}"
        )
        if self.error_count > 0:
            print(f"{Colors.RED}Errors: {self.error_count}{Colors.END}")
        else:
            print(
                f"{Colors.GREEN}🎉 All Python files formatted successfully!{Colors.END}"
            )

        # Suggestions d'amélioration
        print()
        print(f"{Colors.BOLD}NEXT STEPS{Colors.END}")
        print("=" * 50)
        print("1. Vérifiez les fichiers modifiés avec git diff")
        print("2. Testez que votre code fonctionne toujours")
        print("3. Considérez l'ajout de pre-commit hooks pour maintenir le formatage")
        print("4. Configurez votre éditeur pour formater automatiquement")


def main():
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # Utiliser le répertoire parent du script (projet NOAH)
        project_root = Path(__file__).parent.parent

    formatter = PythonFormatter(project_root)
    formatter.format_all()

    # Code de sortie
    sys.exit(0 if formatter.error_count == 0 else 1)


if __name__ == "__main__":
    main()
