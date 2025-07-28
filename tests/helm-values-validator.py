#!/usr/bin/env python3
"""
NOAH helm Values Validator
Validates YAML syntax and structure of helm values files

Author: NOAH Team
Version: 1.0.0
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple

import yaml


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


class HelmValuesValidator:
    def __init__(self, values_dir: Optional[str] = None):
        if values_dir is None:
            # Use relative path from tests directory to values
            script_dir = Path(__file__).parent
            values_dir = str(script_dir / "values")
        self.values_dir = Path(values_dir)
        self.required_sections = ["replicaCount", "securityContext", "resources"]
        self.recommended_sections = [
            "persistence",
            "service",
            "ingress",
            "serviceMonitor",
            "autoscaling",
            "global",
        ]

    def print_banner(self):
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("██╗   ██╗ █████╗ ██╗     ██╗██████╗  █████╗ ████████╗ ██████╗ ██████╗ ")
        print("██║   ██║██╔══██╗██║     ██║██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗")
        print("██║   ██║███████║██║     ██║██║  ██║███████║   ██║   ██║   ██║██████╔╝")
        print("╚██╗ ██╔╝██╔══██║██║     ██║██║  ██║██╔══██║   ██║   ██║   ██║██╔══██╗")
        print(" ╚████╔╝ ██║  ██║███████╗██║██████╔╝██║  ██║   ██║   ╚██████╔╝██║  ██║")
        print("  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝")
        print(f"{Colors.END}")
        print(f"{Colors.BOLD}NOAH helm Values Validator{Colors.END}")
        print("=" * 50)

    def validate_yaml_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Validate YAML syntax"""
        try:
            with open(file_path, "r") as f:
                yaml.safe_load(f)
            return True, "Valid YAML syntax"
        except yaml.YAMLError as e:
            return False, f"YAML syntax error: {e}"
        except Exception as e:
            return False, f"File error: {e}"

    def validate_structure(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate helm values structure"""
        try:
            with open(file_path, "r") as f:
                content = yaml.safe_load(f)

            if not isinstance(content, dict):
                return False, ["Root level must be a dictionary"]

            issues = []

            # Check required sections
            for section in self.required_sections:
                if section not in content:
                    issues.append(f"Missing required section: {section}")

            # Check recommended sections
            missing_recommended = []
            for section in self.recommended_sections:
                if section not in content:
                    missing_recommended.append(section)

            if missing_recommended:
                issues.append(
                    f"Missing recommended sections: {', '.join(missing_recommended)}"
                )

            # Validate security context
            if "securityContext" in content:
                sec_ctx = content["securityContext"]
                if not isinstance(sec_ctx, dict):
                    issues.append("securityContext must be a dictionary")
                else:
                    required_sec_fields = ["runAsUser", "runAsGroup", "fsGroup"]
                    for field in required_sec_fields:
                        if field not in sec_ctx:
                            issues.append(f"Missing securityContext field: {field}")

            # Validate resources
            if "resources" in content:
                resources = content["resources"]
                if not isinstance(resources, dict):
                    issues.append("resources must be a dictionary")
                else:
                    if "requests" not in resources:
                        issues.append("Missing resources.requests")
                    if "limits" not in resources:
                        issues.append("Missing resources.limits")

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"Structure validation error: {e}"]

    def validate_security(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate security configuration"""
        try:
            with open(file_path, "r") as f:
                content = yaml.safe_load(f)

            issues = []

            # Check for security best practices
            if "securityContext" in content:
                sec_ctx = content["securityContext"]

                # Check for privilege escalation (allow for compatibility profiles)
                if sec_ctx.get("allowPrivilegeEscalation") == True:
                    # Only flag as warning for minimal/root profiles (not error)
                    if "minimal" in file_path.name or "root" in file_path.name:
                        # This is acceptable for compatibility profiles
                        pass
                    else:
                        issues.append(
                            "Privilege escalation should be disabled for security"
                        )

                # Check for read-only root filesystem in compatible profiles
                if (
                    "root" in file_path.name
                    and sec_ctx.get("readOnlyRootFilesystem") == True
                ):
                    issues.append(
                        "Root profile should allow write access to root filesystem"
                    )

            # Check for network policies in production profiles
            if "root" in file_path.name:
                if (
                    "networkPolicy" in content
                    and content["networkPolicy"].get("enabled") == True
                ):
                    issues.append(
                        "Root profile should disable network policies for compatibility"
                    )

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"Security validation error: {e}"]

    def validate_file(self, file_path: Path) -> Dict:
        """Validate a single file"""
        print(f"\n{Colors.BLUE}Validating: {file_path.name}{Colors.END}")

        result = {
            "file": file_path.name,
            "syntax": {"valid": False, "message": ""},
            "structure": {"valid": False, "issues": []},
            "security": {"valid": False, "issues": []},
            "overall": False,
        }

        # Validate YAML syntax
        syntax_valid, syntax_message = self.validate_yaml_syntax(file_path)
        result["syntax"] = {"valid": syntax_valid, "message": syntax_message}

        if syntax_valid:
            print(f"  {Colors.GREEN}✓{Colors.END} YAML syntax: {syntax_message}")

            # Validate structure
            structure_valid, structure_issues = self.validate_structure(file_path)
            result["structure"] = {"valid": structure_valid, "issues": structure_issues}

            if structure_valid:
                print(f"  {Colors.GREEN}✓{Colors.END} Structure: Valid")
            else:
                print(f"  {Colors.YELLOW}⚠{Colors.END} Structure issues:")
                for issue in structure_issues:
                    print(f"    - {issue}")

            # Validate security
            security_valid, security_issues = self.validate_security(file_path)
            result["security"] = {"valid": security_valid, "issues": security_issues}

            if security_valid:
                print(f"  {Colors.GREEN}✓{Colors.END} Security: Valid")
            else:
                print(f"  {Colors.YELLOW}⚠{Colors.END} Security issues:")
                for issue in security_issues:
                    print(f"    - {issue}")

            result["overall"] = syntax_valid and structure_valid and security_valid

        else:
            print(f"  {Colors.RED}✗{Colors.END} YAML syntax: {syntax_message}")

        return result

    def validate_all(self) -> Dict:
        """Validate all values files"""
        self.print_banner()

        if not self.values_dir.exists():
            print(
                f"{Colors.RED}Error: Values directory not found: {self.values_dir}{Colors.END}"
            )
            return {}

        yaml_files = list(self.values_dir.glob("*.yaml"))
        if not yaml_files:
            print(
                f"{Colors.RED}Error: No YAML files found in {self.values_dir}{Colors.END}"
            )
            return {}

        results = {}

        for file_path in sorted(yaml_files):
            results[file_path.name] = self.validate_file(file_path)

        # Print summary
        print(f"\n{Colors.BOLD}VALIDATION SUMMARY{Colors.END}")
        print("=" * 50)

        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r["overall"])

        for filename, result in results.items():
            status = (
                f"{Colors.GREEN}✓{Colors.END}"
                if result["overall"]
                else f"{Colors.RED}✗{Colors.END}"
            )
            print(f"{status} {filename}")

        print(
            f"\n{Colors.BOLD}Results: {valid_files}/{total_files} files passed validation{Colors.END}"
        )

        if valid_files == total_files:
            print(f"{Colors.GREEN}🎉 All files validated successfully!{Colors.END}")
            return results
        else:
            print(
                f"{Colors.YELLOW}⚠ Some files have issues that should be addressed{Colors.END}"
            )
            return results


def main():
    validator = HelmValuesValidator()
    results = validator.validate_all()

    # Exit with error code if validation failed
    if not all(r["overall"] for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
