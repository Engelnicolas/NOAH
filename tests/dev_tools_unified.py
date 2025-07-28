#!/usr/bin/env python3
"""
NOAH Development Tools Suite

Unified suite combining formatting, linting, and validation tools.
Consolidates functionality from:
- python-formatter.py
- yaml-formatter.py  
- helm-values-validator.py
- fix-helm-templates.py
- noah-linter.py (parts)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    PURPLE = "\033[95m"
    END = "\033[0m"
    BOLD = "\033[1m"


class NoahDevTools:
    """Unified development tools for NOAH project."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.script_dir = Path(__file__).parent
        self.stats = {
            'formatted': 0,
            'validated': 0,
            'fixed': 0,
            'errors': 0,
            'skipped': 0
        }

    def print_banner(self, tool_name: str):
        """Print a banner for the current tool."""
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("=" * 60)
        print(f"NOAH {tool_name}")
        print("=" * 60)
        print(f"{Colors.END}")

    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        exclude_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules"}
        
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories from search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files

    def find_yaml_files(self) -> List[Path]:
        """Find all YAML files in the project."""
        yaml_files = []
        exclude_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules"}
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith(('.yaml', '.yml')):
                    yaml_files.append(Path(root) / file)
        
        return yaml_files

    def format_python_files(self, files: Optional[List[Path]] = None) -> bool:
        """Format Python files using black and isort."""
        self.print_banner("Python Formatter")
        
        if files is None:
            files = self.find_python_files()
        
        if not files:
            print(f"{Colors.YELLOW}No Python files found{Colors.END}")
            return True

        success = True
        
        # Check if formatting tools are available
        for tool in ['black', 'isort']:
            if not self._check_tool_available(tool):
                print(f"{Colors.RED}❌ {tool} not found. Install with: pip install {tool}{Colors.END}")
                return False

        for file_path in files:
            try:
                print(f"Formatting: {file_path}")
                
                # Run black
                result = subprocess.run(
                    ['black', '--line-length', '88', str(file_path)],
                    capture_output=True, text=True
                )
                
                if result.returncode != 0:
                    print(f"  {Colors.RED}❌ Black failed: {result.stderr}{Colors.END}")
                    self.stats['errors'] += 1
                    success = False
                    continue
                
                # Run isort
                result = subprocess.run(
                    ['isort', str(file_path)],
                    capture_output=True, text=True
                )
                
                if result.returncode != 0:
                    print(f"  {Colors.RED}❌ isort failed: {result.stderr}{Colors.END}")
                    self.stats['errors'] += 1
                    success = False
                    continue
                
                print(f"  {Colors.GREEN}✅ Formatted successfully{Colors.END}")
                self.stats['formatted'] += 1
                
            except Exception as e:
                print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                self.stats['errors'] += 1
                success = False
        
        return success

    def format_yaml_files(self, files: Optional[List[Path]] = None) -> bool:
        """Format YAML files."""
        self.print_banner("YAML Formatter")
        
        if files is None:
            files = self.find_yaml_files()
        
        if not files:
            print(f"{Colors.YELLOW}No YAML files found{Colors.END}")
            return True

        success = True
        
        for file_path in files:
            try:
                print(f"Formatting: {file_path}")
                
                # Skip multi-document YAML files
                if self._is_multi_document_yaml(file_path):
                    print(f"  {Colors.YELLOW}⏭️  Skipped (multi-document){Colors.END}")
                    self.stats['skipped'] += 1
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if data is None:
                    print(f"  {Colors.YELLOW}⏭️  Skipped (empty file){Colors.END}")
                    self.stats['skipped'] += 1
                    continue
                
                # Format and write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, 
                             allow_unicode=True, sort_keys=False, indent=2)
                
                print(f"  {Colors.GREEN}✅ Formatted successfully{Colors.END}")
                self.stats['formatted'] += 1
                
            except yaml.YAMLError as e:
                print(f"  {Colors.RED}❌ YAML Error: {e}{Colors.END}")
                self.stats['errors'] += 1
                success = False
            except Exception as e:
                print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                self.stats['errors'] += 1
                success = False
        
        return success

    def validate_helm_values(self, values_dir: Optional[str] = None) -> bool:
        """Validate Helm values files."""
        self.print_banner("Helm Values Validator")
        
        if values_dir is None:
            values_dir = self.script_dir / "values"
        else:
            values_dir = Path(values_dir)
        
        if not values_dir.exists():
            print(f"{Colors.RED}❌ Values directory not found: {values_dir}{Colors.END}")
            return False

        required_sections = ["replicaCount", "securityContext", "resources"]
        recommended_sections = [
            "persistence", "service", "ingress", "serviceMonitor", 
            "autoscaling", "global"
        ]
        
        success = True
        
        for values_file in values_dir.glob("*.yaml"):
            try:
                print(f"Validating: {values_file}")
                
                with open(values_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not isinstance(data, dict):
                    print(f"  {Colors.RED}❌ Invalid structure (not a dict){Colors.END}")
                    self.stats['errors'] += 1
                    success = False
                    continue
                
                # Check required sections
                missing_required = [s for s in required_sections if s not in data]
                if missing_required:
                    print(f"  {Colors.RED}❌ Missing required sections: {missing_required}{Colors.END}")
                    self.stats['errors'] += 1
                    success = False
                
                # Check recommended sections
                missing_recommended = [s for s in recommended_sections if s not in data]
                if missing_recommended:
                    print(f"  {Colors.YELLOW}⚠️  Missing recommended sections: {missing_recommended}{Colors.END}")
                
                if not missing_required:
                    print(f"  {Colors.GREEN}✅ Valid structure{Colors.END}")
                    self.stats['validated'] += 1
                
            except yaml.YAMLError as e:
                print(f"  {Colors.RED}❌ YAML Error: {e}{Colors.END}")
                self.stats['errors'] += 1
                success = False
            except Exception as e:
                print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                self.stats['errors'] += 1
                success = False
        
        return success

    def fix_helm_templates(self) -> bool:
        """Fix Helm template syntax issues."""
        self.print_banner("Helm Template Fixer")
        
        helm_dir = self.project_root / "helm"
        if not helm_dir.exists():
            print(f"{Colors.RED}❌ Helm directory not found: {helm_dir}{Colors.END}")
            return False

        pattern_open = re.compile(r'{ {')
        pattern_close = re.compile(r'} }')
        fixed_files = []

        for template_file in helm_dir.rglob("templates/*.yaml"):
            try:
                print(f"Checking: {template_file}")
                
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                content = pattern_open.sub('{{', content)
                content = pattern_close.sub('}}', content)

                if content != original_content:
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(template_file)
                    print(f"  {Colors.GREEN}✅ Fixed template syntax{Colors.END}")
                    self.stats['fixed'] += 1
                else:
                    print(f"  {Colors.BLUE}ℹ️  No issues found{Colors.END}")

            except Exception as e:
                print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                self.stats['errors'] += 1

        return True

    def _check_tool_available(self, tool: str) -> bool:
        """Check if a command-line tool is available."""
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _is_multi_document_yaml(self, file_path: Path) -> bool:
        """Check if YAML file contains multiple documents."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content.count('\n---\n') > 0 or content.count('\n--- ') > 0
        except Exception:
            return False

    def print_stats(self):
        """Print final statistics."""
        print(f"\n{Colors.BOLD}Final Statistics:{Colors.END}")
        print(f"  Formatted: {Colors.GREEN}{self.stats['formatted']}{Colors.END}")
        print(f"  Validated: {Colors.BLUE}{self.stats['validated']}{Colors.END}")
        print(f"  Fixed: {Colors.CYAN}{self.stats['fixed']}{Colors.END}")
        print(f"  Skipped: {Colors.YELLOW}{self.stats['skipped']}{Colors.END}")
        print(f"  Errors: {Colors.RED}{self.stats['errors']}{Colors.END}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="NOAH Development Tools Suite")
    parser.add_argument('--format-python', action='store_true', 
                       help='Format Python files')
    parser.add_argument('--format-yaml', action='store_true', 
                       help='Format YAML files')
    parser.add_argument('--validate-helm', action='store_true',
                       help='Validate Helm values files')
    parser.add_argument('--fix-templates', action='store_true',
                       help='Fix Helm template syntax')
    parser.add_argument('--all', action='store_true',
                       help='Run all tools')
    parser.add_argument('--project-root', type=str,
                       help='Project root directory')
    
    args = parser.parse_args()
    
    if not any([args.format_python, args.format_yaml, args.validate_helm, 
                args.fix_templates, args.all]):
        parser.print_help()
        return 1

    tools = NoahDevTools(args.project_root)
    success = True
    
    if args.all or args.format_python:
        success &= tools.format_python_files()
    
    if args.all or args.format_yaml:
        success &= tools.format_yaml_files()
    
    if args.all or args.validate_helm:
        success &= tools.validate_helm_values()
    
    if args.all or args.fix_templates:
        success &= tools.fix_helm_templates()
    
    tools.print_stats()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
