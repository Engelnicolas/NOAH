#!/usr/bin/env python3
"""
NOAH Workflow Test Simulation
Test script to simulate GitHub Workflow actions and validate project structure.
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path


def run_command(command, description):
    """Run a shell command and return success status."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}")
            return True
        else:
            print(f"❌ {description} - Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        return False


def test_python_syntax():
    """Test Python syntax validation for all Python files."""
    print("📍 Testing Python syntax...")
    
    # Test main noah.py file
    if not run_command("python -m py_compile noah.py", "noah.py syntax validation"):
        return False
    
    # Test all Scripts/*.py files
    scripts_dir = Path("Scripts")
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.py"):
            if not run_command(f"python -m py_compile {script_file}", f"{script_file.name} syntax validation"):
                return False
    
    return True


def test_noah_cli():
    """Test NOAH CLI functionality."""
    print("\n📍 Testing NOAH CLI...")
    return run_command("python noah.py --help > /dev/null 2>&1", "NOAH CLI functionality")


def test_module_imports():
    """Test module imports."""
    print("\n📍 Testing module imports...")
    
    import_test = """
import sys
sys.path.append('Scripts')
from config_loader import ConfigLoader
from security_manager import NoahSecurityManager
from cluster_manager import ClusterManager
from helm_deployer import HelmDeployer
from ansible_runner import AnsibleRunner
print('All modules imported successfully')
"""
    
    try:
        exec(import_test)
        print("✅ Module imports successful")
        return True
    except Exception as e:
        print(f"❌ Module import errors: {e}")
        return False


def test_ansible_playbooks():
    """Test Ansible playbook syntax."""
    print("\n📍 Testing Ansible playbooks...")
    
    ansible_dir = Path("Ansible")
    if not ansible_dir.exists():
        print("⚠️  Ansible directory not found")
        return True
    
    success = True
    for playbook in ansible_dir.glob("*.yml"):
        if not run_command(f"ansible-playbook --syntax-check {playbook} > /dev/null 2>&1", f"{playbook.name} syntax validation"):
            success = False
    
    return success


def test_workflow_yaml():
    """Test workflow YAML file validation."""
    print("\n📍 Testing workflow YAML files...")
    
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print("❌ .github/workflows directory not found")
        return False
    
    success = True
    for workflow_file in workflows_dir.glob("*.yml"):
        try:
            with open(workflow_file, 'r') as f:
                yaml.safe_load(f)
            print(f"✅ {workflow_file.name} valid YAML")
        except Exception as e:
            print(f"❌ {workflow_file.name} YAML error: {e}")
            success = False
    
    return success


def check_documentation():
    """Check documentation files."""
    print("\n📍 Checking documentation...")
    
    docs_dir = Path("Docs")
    if not docs_dir.exists():
        print("⚠️  Docs directory not found")
        return True
    
    doc_count = 0
    for doc_file in docs_dir.glob("*.md"):
        try:
            line_count = len(doc_file.read_text().splitlines())
            print(f"✅ {doc_file.name} exists ({line_count} lines)")
            doc_count += 1
        except Exception as e:
            print(f"❌ Error reading {doc_file.name}: {e}")
    
    print(f"📚 Found {doc_count} documentation files")
    return True


def check_directory_structure():
    """Check required directory structure."""
    print("\n📍 Checking directory structure...")
    
    required_dirs = ["Scripts", "Ansible", "Helm", "Docs", "Tests", ".github/workflows"]
    
    for directory in required_dirs:
        dir_path = Path(directory)
        if dir_path.exists():
            print(f"✅ {directory}/ directory exists")
        else:
            print(f"⚠️  {directory}/ directory missing")
    
    return True


def generate_statistics():
    """Generate project statistics."""
    print("\n📍 Generating statistics...")
    
    try:
        # Count Python files
        python_files = len(list(Path(".").rglob("*.py")))
        
        # Count Ansible playbooks
        ansible_files = len(list(Path("Ansible").glob("*.yml"))) if Path("Ansible").exists() else 0
        
        # Count Helm charts (directories with templates/)
        helm_charts = len([d for d in Path("Helm").iterdir() 
                          if d.is_dir() and (d / "templates").exists()]) if Path("Helm").exists() else 0
        
        # Count documentation files
        doc_files = len(list(Path("Docs").glob("*.md"))) if Path("Docs").exists() else 0
        
        # Count workflow files
        workflow_files = len(list(Path(".github/workflows").glob("*.yml"))) if Path(".github/workflows").exists() else 0
        
        print(f"📊 Statistics:")
        print(f"   - Python files: {python_files}")
        print(f"   - Ansible playbooks: {ansible_files}")
        print(f"   - Helm charts: {helm_charts}")
        print(f"   - Documentation files: {doc_files}")
        print(f"   - Workflow files: {workflow_files}")
        
    except Exception as e:
        print(f"❌ Error generating statistics: {e}")


def main():
    """Main test function."""
    print("🧪 NOAH Workflow Test Simulation")
    print("================================")
    
    # Change to project root directory
    os.chdir(Path(__file__).parent.parent)
    
    # Run all tests
    tests = [
        test_python_syntax,
        test_noah_cli,
        test_module_imports,
        test_ansible_playbooks,
        test_workflow_yaml,
        check_documentation,
        check_directory_structure
    ]
    
    all_passed = True
    for test_func in tests:
        if not test_func():
            all_passed = False
    
    # Generate statistics regardless of test results
    generate_statistics()
    
    # Final result
    if all_passed:
        print("\n🎉 All tests completed successfully!")
        print("🚀 Workflows are ready for GitHub Actions")
        return 0
    else:
        print("\n❌ Some tests failed!")
        print("🔧 Please fix the issues before deploying workflows")
        return 1


if __name__ == "__main__":
    sys.exit(main())
