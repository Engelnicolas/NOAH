#!/usr/bin/env python3
"""
NOAH - Next Open-source Architecture Hub CLI

This is the main CLI entry point for NOAH project operations.
It acts as a unified interface that routes commands to specialized scripts.

AUTHOR: NOAH Team
VERSION: 0.9
DATE: July 18, 2025
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import importlib.util
import inspect


class Colors:
    """Terminal color constants."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class NoahCLI:
    """Main NOAH CLI class."""

    def __init__(self):
        """Initialize the NOAH CLI."""
        self.script_dir = Path(__file__).parent.resolve()
        self.version = "0.9"
        self.name = "noah"
        self.description = "Next Open-source Architecture Hub CLI"
        
        # Discover all Python scripts in the script directory
        self.script_commands = self._discover_scripts()

    def _discover_scripts(self) -> Dict[str, Dict]:
        """Discover all Python scripts in the script directory."""
        commands = {}
        
        # Scan for Python files
        for script_path in self.script_dir.glob("noah-*.py"):
            if script_path.is_file():
                command_name = script_path.stem.replace("noah-", "")
                
                # Try to extract description from docstring
                description = self._extract_description(script_path)
                
                commands[command_name] = {
                    "script_path": script_path,
                    "execution_method": "python",
                    "description": description,
                    "requires_root": self._check_requires_root(script_path),
                    "requires_subcommand": self._check_requires_subcommand(script_path),
                    "subcommands": self._get_script_subcommands(script_path)
                }
        
        # Scan for executable scripts without .py extension
        for script_path in self.script_dir.glob("noah-*"):
            if (script_path.is_file() and 
                os.access(script_path, os.X_OK) and 
                not script_path.suffix == ".py"):
                
                command_name = script_path.stem.replace("noah-", "")
                
                if command_name not in commands:  # Don't override Python scripts
                    # Check if it's a Python script based on shebang
                    is_python_script = self._is_python_script(script_path)
                    
                    commands[command_name] = {
                        "script_path": script_path,
                        "execution_method": "python" if is_python_script else "executable",
                        "description": f"Script exécutable: {script_path.name}",
                        "requires_root": self._check_requires_root(script_path),
                        "requires_subcommand": self._check_requires_subcommand(script_path) if is_python_script else False,
                        "subcommands": self._get_script_subcommands(script_path) if is_python_script else []
                    }
        
        return commands

    def _extract_description(self, script_path: Path) -> str:
        """Extract description from script docstring or comments."""
        try:
            if script_path.suffix == ".py":
                # For Python files, try to get module docstring
                spec = importlib.util.spec_from_file_location("module", script_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if module.__doc__:
                        # Get first line of docstring
                        return module.__doc__.strip().split('\n')[0]
            
            # Fallback: read first few lines for description
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]
                for line in lines:
                    line = line.strip()
                    if line.startswith('"""') and len(line) > 3:
                        return line[3:].strip().rstrip('"""').strip()
                    elif line.startswith('#') and 'description' in line.lower():
                        return line.lstrip('#').strip()
                        
        except Exception:
            pass
        
        return f"Script NOAH: {script_path.stem}"

    def _check_requires_root(self, script_path: Path) -> bool:
        """Check if script requires root privileges."""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for common indicators
                root_indicators = [
                    "require.*root", "sudo", "privilege", "docker", 
                    "kubernetes", "systemctl", "service", "mount"
                ]
                content_lower = content.lower()
                return any(indicator in content_lower for indicator in root_indicators)
        except Exception:
            return False

    def _check_requires_subcommand(self, script_path: Path) -> bool:
        """Check if script requires sub-commands."""
        try:
            if script_path.suffix == ".py":
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for argparse with choices or subparsers
                    if ('choices=' in content and 'argparse' in content) or 'add_subparsers' in content:
                        return True
        except Exception:
            pass
        return False

    def _get_script_subcommands(self, script_path: Path) -> List[str]:
        """Extract subcommands from script if available."""
        subcommands = []
        try:
            if script_path.suffix == ".py":
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for choices in argparse
                    import re
                    choices_match = re.search(r'choices=\[([^\]]+)\]', content)
                    if choices_match:
                        choices_str = choices_match.group(1)
                        # Extract quoted strings
                        subcommands = re.findall(r'"([^"]+)"', choices_str)
                        if not subcommands:
                            subcommands = re.findall(r"'([^']+)'", choices_str)
        except Exception:
            pass
        return subcommands

    def _is_python_script(self, script_path: Path) -> bool:
        """Check if executable script is actually a Python script."""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # Check for Python shebang
                return 'python' in first_line and first_line.startswith('#!')
        except Exception:
            return False

    def _check_linter_setup(self) -> bool:
        """Check if linter setup has been completed."""
        try:
            # Check if .pre-commit-config.yaml exists
            pre_commit_config = self.script_dir.parent / ".pre-commit-config.yaml"
            if not pre_commit_config.exists():
                return False
            
            # Check if .git directory exists
            git_dir = self.script_dir.parent / ".git"
            if not git_dir.exists():
                return False
                
            # Check if pre-commit hooks are installed in .git/hooks
            git_hooks_dir = git_dir / "hooks"
            if not git_hooks_dir.exists():
                return False
                
            pre_commit_hook = git_hooks_dir / "pre-commit"
            if not pre_commit_hook.exists():
                return False
                
            # Check if the hook contains pre-commit content
            try:
                with open(pre_commit_hook, 'r') as f:
                    content = f.read()
                    if 'pre-commit' not in content:
                        return False
            except:
                return False
                
            return True
            
        except Exception:
            return False

    def print_colored(self, message: str, color: str = Colors.NC) -> None:
        """Print colored message."""
        print(f"{color}{message}{Colors.NC}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        self.print_colored(f"[INFO] {message}", Colors.BLUE)

    def print_success(self, message: str) -> None:
        """Print success message."""
        self.print_colored(f"[SUCCESS] {message}", Colors.GREEN)

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.print_colored(f"[WARNING] {message}", Colors.YELLOW)

    def print_error(self, message: str) -> None:
        """Print error message."""
        self.print_colored(f"[ERROR] {message}", Colors.RED)

    def show_banner(self) -> None:
        """Display the NOAH banner."""
        banner = f"""{Colors.CYAN}
███    ██  ██████   █████  ██   ██
████   ██ ██    ██ ██   ██ ██   ██
██ ██  ██ ██    ██ ███████ ███████
██  ██ ██ ██    ██ ██   ██ ██   ██
██   ████  ██████  ██   ██ ██   ██

Next Open-source Architecture Hub
{Colors.NC}"""
        print(banner)

    def check_root_privileges(self, command: str) -> bool:
        """Check and request root privileges if needed."""
        if command not in self.script_commands:
            return True
            
        if not self.script_commands[command]["requires_root"]:
            return True
            
        # Check if already running as root
        if os.geteuid() == 0:
            self.print_success("Running with root privileges ✓")
            return True
            
        self.print_warning(f"La commande '{command}' nécessite des privilèges root")
        self.print_info("Les opérations suivantes nécessitent des privilèges administrateur :")
        self.print_info("  • Installation de packages système")
        self.print_info("  • Configuration de services réseau")
        self.print_info("  • Gestion des conteneurs Docker/Kubernetes")
        self.print_info("  • Modification des configurations système")
        print()
        
        response = input(f"{Colors.YELLOW}Voulez-vous continuer avec sudo ? [y/N]{Colors.NC} ")
        
        if response.lower() in ['y', 'yes', 'o', 'oui']:
            self.print_info("Relancement avec sudo...")
            # Re-execute with sudo
            args = ["sudo", "python3"] + sys.argv
            os.execvp("sudo", args)
        else:
            self.print_error("Opération annulée par l'utilisateur")
            self.print_info("Pour exécuter sans interaction, utilisez :")
            self.print_info(f"  sudo python3 {sys.argv[0]} {command}")
            return False
            
        return True

    def execute_script(self, command: str, args: List[str]) -> int:
        """Execute the specified script with arguments."""
        if command not in self.script_commands:
            self.print_error(f"Commande inconnue: {command}")
            self.print_info("Commandes disponibles:")
            for cmd in sorted(self.script_commands.keys()):
                self.print_info(f"  • {cmd}")
            return 1
            
        script_info = self.script_commands[command]
        script_path = script_info["script_path"]
        execution_method = script_info["execution_method"]
        
        # Check if script exists
        if not script_path.exists():
            self.print_error(f"Script non trouvé: {script_path}")
            return 1
            
        # Special handling for scripts that require sub-commands
        if script_info.get("requires_subcommand", False) and not args:
            self.print_error(f"Le script {command} nécessite une sous-commande")
            
            # Special handling for linter - check if setup has been done
            if command == "linter":
                setup_status = self._check_linter_setup()
                if not setup_status:
                    self.print_warning("L'environnement de linting n'a pas encore été configuré")
                    self.print_info("Voulez-vous exécuter la configuration maintenant ?")
                    response = input(f"{Colors.YELLOW}Exécuter 'noah linter setup' ? [y/N]{Colors.NC} ")
                    if response.lower() in ['y', 'yes', 'o', 'oui']:
                        self.print_info("Exécution de la configuration du linter...")
                        return self.execute_script(command, ["setup"])
                    else:
                        self.print_info("Configuration annulée.")
                else:
                    self.print_success("Environnement de linting déjà configuré ✓")
            
            subcommands = script_info.get("subcommands", [])
            if subcommands:
                self.print_info("Sous-commandes disponibles:")
                for subcmd in subcommands:
                    self.print_info(f"  • {subcmd}")
            else:
                # Fallback for known commands
                if command == "linter":
                    self.print_info("Sous-commandes disponibles:")
                    self.print_info("  • setup     - Configurer l'environnement de linting")
                    self.print_info("  • lint      - Exécuter le linting sur les fichiers")
                    self.print_info("  • precommit - Exécuter les hooks pre-commit")
                    self.print_info("  • report    - Générer un rapport de linting")
                    self.print_info("  • help      - Afficher l'aide détaillée")
                else:
                    self.print_info("Utilisez --help pour voir les options disponibles")
            
            self.print_info("")
            self.print_info("Exemples:")
            if command == "linter":
                self.print_info("  ./noah linter setup")
                self.print_info("  ./noah linter lint --all")
                self.print_info("  ./noah linter precommit")
            else:
                self.print_info(f"  ./noah {command} --help")
            return 1
            
        # Check root privileges if needed
        if not self.check_root_privileges(command):
            return 1
            
        # Build command
        if execution_method == "python":
            cmd = [sys.executable, str(script_path)] + args
        else:
            cmd = [str(script_path)] + args
            
        self.print_info(f"Exécution: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=self.script_dir.parent)
            return result.returncode
        except KeyboardInterrupt:
            self.print_warning("Interruption par l'utilisateur")
            return 130
        except Exception as e:
            self.print_error(f"Erreur lors de l'exécution: {e}")
            return 1

    def show_help(self) -> None:
        """Show help information."""
        self.show_banner()
        self.print_colored(self.description, Colors.BLUE)
        self.print_colored(f"Version: {self.version}", Colors.BLUE)
        print()
        
        print(f"{Colors.YELLOW}USAGE:{Colors.NC}")
        print(f"    ./noah COMMAND [SUB-COMMAND] [OPTIONS]")
        print()
        print(f"{Colors.YELLOW}COMMANDES PRINCIPALES:{Colors.NC}")
        print(f"    ./noah --help                           # Cette aide")
        print(f"    ./noah --list                           # Liste détaillée des scripts")
        print(f"    ./noah --version                        # Version de NOAH")
        print()
        
        print(f"{Colors.YELLOW}COMMANDES DISPONIBLES:{Colors.NC}")
        print()
        
        # Group commands by category
        categories = {
            "Infrastructure": ["deploy", "infra"],
            "Monitoring": ["monitoring"],
            "Code Quality": ["fix", "linter", "linting"],
            "Dependencies": ["deps", "deps-manager"],
            "Setup": ["tech-requirements", "requirements"]
        }
        
        for category, commands in categories.items():
            available_commands = [cmd for cmd in commands if cmd in self.script_commands]
            if available_commands:
                print(f"{Colors.PURPLE}📦 {category}:{Colors.NC}")
                for cmd in available_commands:
                    script_info = self.script_commands[cmd]
                    root_indicator = " 🔒" if script_info["requires_root"] else ""
                    print(f"  {Colors.GREEN}{cmd:<15}{Colors.NC} {script_info['description']}{root_indicator}")
                print()
        
        # Show other commands
        shown_commands = set()
        for commands in categories.values():
            shown_commands.update(commands)
            
        other_commands = [cmd for cmd in self.script_commands.keys() if cmd not in shown_commands]
        if other_commands:
            print(f"{Colors.PURPLE}🔧 Autres commandes:{Colors.NC}")
            for cmd in sorted(other_commands):
                script_info = self.script_commands[cmd]
                root_indicator = " 🔒" if script_info["requires_root"] else ""
                print(f"  {Colors.GREEN}{cmd:<15}{Colors.NC} {script_info['description']}{root_indicator}")
            print()
        
        print(f"{Colors.YELLOW}DÉTAILS D'EXÉCUTION:{Colors.NC}")
        print()
        for cmd in sorted(self.script_commands.keys()):
            script_info = self.script_commands[cmd]
            execution_method = script_info["execution_method"]
            script_path = script_info["script_path"]
            print(f"  {Colors.GREEN}{cmd}{Colors.NC} → {Colors.BLUE}{script_path.name}{Colors.NC} ({execution_method})")
        print()
        
        print(f"{Colors.YELLOW}EXEMPLES:{Colors.NC}")
        print()
        print(f"{Colors.BLUE}Infrastructure:{Colors.NC}")
        print("    ./noah deploy --help                    # Aide pour le déploiement")
        print()
        print(f"{Colors.BLUE}Monitoring:{Colors.NC}")
        print("    ./noah monitoring status                # État du monitoring")
        print()
        print(f"{Colors.BLUE}Code Quality:{Colors.NC}")
        print("    ./noah linter setup                     # Configurer l'environnement")
        print("    ./noah linter lint --all                # Linting sur tous les fichiers")
        print("    ./noah linter precommit                 # Hooks pre-commit")
        print()
        print(f"{Colors.BLUE}Gestion des dépendances:{Colors.NC}")
        print("    ./noah deps-manager --check             # Vérifier les dépendances")
        print("    ./noah tech-requirements --report       # Rapport des prérequis")
        print()
        
        print(f"{Colors.YELLOW}LÉGENDE:{Colors.NC}")
        print("    🔒 = Nécessite des privilèges root")
        print()
        print(f"{Colors.YELLOW}Pour l'aide spécifique d'une commande:{Colors.NC}")
        print("    ./noah COMMANDE --help")
        print()
        print(f"{Colors.YELLOW}Commandes avec sous-commandes:{Colors.NC}")
        print("    ./noah linter [setup|lint|precommit|report|help]")
        print("    ./noah monitoring [status|deploy|teardown]")
        print("    ./noah deploy [--profile|--verbose|--dry-run]")
        print()

    def list_scripts(self) -> None:
        """List all available scripts with details."""
        print(f"{Colors.CYAN}Scripts NOAH disponibles:{Colors.NC}")
        print()
        
        for cmd, info in sorted(self.script_commands.items()):
            script_path = info["script_path"]
            execution_method = info["execution_method"]
            requires_root = info["requires_root"]
            description = info["description"]
            
            root_indicator = f"{Colors.RED} [ROOT]{Colors.NC}" if requires_root else ""
            method_color = Colors.GREEN if execution_method == "python" else Colors.YELLOW
            
            print(f"  {Colors.BLUE}{cmd:<20}{Colors.NC} {description}")
            print(f"    └─ {method_color}{script_path.name}{Colors.NC} ({execution_method}){root_indicator}")
            print()

    def validate_script(self, script_path: Path) -> bool:
        """Validate that a script is executable."""
        if not script_path.exists():
            self.print_error(f"Script non trouvé: {script_path}")
            return False
            
        if not os.access(script_path, os.R_OK):
            self.print_error(f"Script non lisible: {script_path}")
            return False
            
        if script_path.suffix == ".py":
            # Check Python syntax
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), script_path, 'exec')
                return True
            except SyntaxError as e:
                self.print_error(f"Erreur de syntaxe Python dans {script_path}: {e}")
                return False
        else:
            # Check if executable
            if not os.access(script_path, os.X_OK):
                self.print_warning(f"Script non exécutable: {script_path}")
                return False
                
        return True

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with given arguments."""
        if args is None:
            args = sys.argv[1:]
            
        # Handle special cases
        if not args or args[0] in ['-h', '--help', 'help']:
            self.show_help()
            return 0
            
        if args[0] in ['--version', 'version']:
            print(f"{self.name} {self.version}")
            return 0
            
        if args[0] in ['--list', 'list']:
            self.list_scripts()
            return 0
            
        # Extract command and remaining arguments
        command = args[0]
        remaining_args = args[1:]
        
        # Execute the command
        return self.execute_script(command, remaining_args)


def main() -> int:
    """Main entry point."""
    try:
        cli = NoahCLI()
        return cli.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interruption par l'utilisateur{Colors.NC}")
        return 130
    except Exception as e:
        print(f"{Colors.RED}[ERROR] Erreur inattendue: {e}{Colors.NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
