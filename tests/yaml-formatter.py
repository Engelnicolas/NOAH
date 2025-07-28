#!/usr/bin/env python3
"""
Script pour formater automatiquement tous les fichiers YAML du projet NOAH
avec une mise en forme cohérente.
"""

import glob
import os
import sys
from pathlib import Path
from typing import List

import yaml


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


class YAMLFormatter:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.formatted_count = 0
        self.error_count = 0
        
    def _is_multi_document_yaml(self, file_path: Path) -> bool:
        """Vérifie si le fichier YAML contient plusieurs documents (séparés par ---)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Compter les séparateurs de documents
                return content.count('\n---\n') > 0 or content.count('\n--- ') > 0
        except Exception:
            return False
        
    def print_banner(self):
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("██╗   ██╗ █████╗ ███╗   ███╗██╗         ███████╗ ██████╗ ██████╗ ███╗   ███╗ █████╗ ████████╗")
        print("╚██╗ ██╔╝██╔══██╗████╗ ████║██║         ██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝")
        print(" ╚████╔╝ ███████║██╔████╔██║██║         █████╗  ██║   ██║██████╔╝██╔████╔██║███████║   ██║   ")
        print("  ╚██╔╝  ██╔══██║██║╚██╔╝██║██║         ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║   ██║   ")
        print("   ██║   ██║  ██║██║ ╚═╝ ██║███████╗    ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║   ██║   ")
        print("   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝    ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ")
        print(f"{Colors.END}")
        print(f"{Colors.BOLD}NOAH YAML Formatter{Colors.END}")
        print("=" * 80)

    def find_yaml_files(self) -> List[Path]:
        """Trouve tous les fichiers YAML dans le projet, en excluant les templates Helm."""
        yaml_files = []
        
        # Patterns de recherche
        patterns = ["**/*.yaml", "**/*.yml"]
        
        # Répertoires à exclure
        exclude_dirs = {
            ".git", "__pycache__", "node_modules", "venv", ".venv",
            "build", "dist", ".pytest_cache"
        }
        
        # Répertoires de templates Helm à exclure
        exclude_template_dirs = {
            "templates"  # Exclut tous les répertoires templates (Helm)
        }
        
        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                # Vérifier que le fichier n'est pas dans un répertoire exclu
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue
                    
                # Exclure les templates Helm
                if any(template_dir in file_path.parts for template_dir in exclude_template_dirs):
                    continue
                    
                # Exclure les fichiers manifests multi-documents (contiennent ---)
                if self._is_multi_document_yaml(file_path):
                    print(f"  {Colors.YELLOW}Skipping multi-document:{Colors.END} {file_path.relative_to(self.project_root)}")
                    continue
                    
                yaml_files.append(file_path)
        
        return sorted(yaml_files)

    def format_yaml_file(self, file_path: Path) -> bool:
        """Formate un fichier YAML avec une mise en forme cohérente."""
        try:
            print(f"  {Colors.BLUE}Formatting:{Colors.END} {file_path.relative_to(self.project_root)}")
            
            # Lire le fichier
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Conserver les commentaires en tête du fichier
            lines = content.split('\n')
            header_comments = []
            yaml_start = 0
            
            for i, line in enumerate(lines):
                if line.strip().startswith('#') or line.strip() == '':
                    header_comments.append(line)
                    yaml_start = i + 1
                else:
                    break
            
            # Parser le YAML
            try:
                yaml_content = yaml.safe_load(content)
                if yaml_content is None:
                    print(f"    {Colors.YELLOW}⚠{Colors.END} Empty or comment-only file, skipping")
                    return True
                    
            except yaml.YAMLError as e:
                print(f"    {Colors.RED}✗{Colors.END} YAML parsing error: {e}")
                return False
            
            # Formater avec PyYAML
            formatted_yaml = yaml.dump(
                yaml_content,
                default_flow_style=False,
                indent=2,
                width=120,
                sort_keys=False,  # Préserver l'ordre original
                allow_unicode=True,
                explicit_start=False,
                explicit_end=False
            )
            
            # Reconstituer le fichier avec les commentaires d'en-tête
            final_content = []
            if header_comments:
                # Ajouter les commentaires d'en-tête
                final_content.extend(header_comments)
                # Ajouter une ligne vide si le dernier commentaire n'est pas vide
                if header_comments and header_comments[-1].strip():
                    final_content.append('')
            
            # Ajouter le YAML formaté
            final_content.extend(formatted_yaml.rstrip().split('\n'))
            
            # Écrire le fichier formaté
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(final_content) + '\n')
            
            print(f"    {Colors.GREEN}✓{Colors.END} Successfully formatted")
            return True
            
        except Exception as e:
            print(f"    {Colors.RED}✗{Colors.END} Error: {e}")
            return False

    def format_all(self) -> None:
        """Formate tous les fichiers YAML du projet."""
        self.print_banner()
        
        print(f"{Colors.CYAN}Searching for YAML files...{Colors.END}")
        yaml_files = self.find_yaml_files()
        
        if not yaml_files:
            print(f"{Colors.YELLOW}No YAML files found.{Colors.END}")
            return
        
        print(f"{Colors.CYAN}Found {len(yaml_files)} YAML files{Colors.END}")
        print()
        
        for file_path in yaml_files:
            if self.format_yaml_file(file_path):
                self.formatted_count += 1
            else:
                self.error_count += 1
        
        # Résumé
        print()
        print(f"{Colors.BOLD}FORMATTING SUMMARY{Colors.END}")
        print("=" * 50)
        print(f"Total files: {len(yaml_files)}")
        print(f"{Colors.GREEN}Successfully formatted: {self.formatted_count}{Colors.END}")
        if self.error_count > 0:
            print(f"{Colors.RED}Errors: {self.error_count}{Colors.END}")
        else:
            print(f"{Colors.GREEN}🎉 All YAML files formatted successfully!{Colors.END}")


def main():
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # Utiliser le répertoire parent du script (projet NOAH)
        project_root = Path(__file__).parent.parent
    
    formatter = YAMLFormatter(project_root)
    formatter.format_all()
    
    # Code de sortie
    sys.exit(0 if formatter.error_count == 0 else 1)


if __name__ == "__main__":
    main()
