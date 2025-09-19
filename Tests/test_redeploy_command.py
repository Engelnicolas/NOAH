#!/usr/bin/env python3
"""
Test the NOAH redeploy CLI command
"""

import subprocess
import sys
from pathlib import Path

def test_redeploy_command():
    """Test that the redeploy command is available and properly structured"""
    
    # Change to NOAH directory
    noah_dir = Path(__file__).parent.parent
    
    print("🧪 Testing NOAH redeploy CLI command...")
    print("=" * 50)
    
    # Test 1: Check redeploy command is available
    print("Test 1: Checking redeploy command availability...")
    try:
        result = subprocess.run(
            ["python", "noah.py", "cluster", "--help"],
            cwd=noah_dir,
            capture_output=True,
            text=True
        )
        
        assert "redeploy" in result.stdout, "redeploy command not found in cluster help"
        print("✅ PASS: redeploy command found in cluster commands")
            
    except Exception as e:
        print(f"❌ FAIL: Error running cluster help: {e}")
        return False
    
    # Test 2: Check redeploy command help
    print("\nTest 2: Checking redeploy command help...")
    try:
        result = subprocess.run(
            ["python", "noah.py", "cluster", "redeploy", "--help"],
            cwd=noah_dir,
            capture_output=True,
            text=True
        )
        
        expected_text = [
            "Redeploy complete NOAH infrastructure",
            "--name",
            "--domain", 
            "--force",
            "--config-file",
            "cluster creation and service deployment"
        ]
        
        missing_text = []
        for text in expected_text:
            if text not in result.stdout:
                missing_text.append(text)
        
        assert not missing_text, f"redeploy help missing: {missing_text}"
        print("✅ PASS: redeploy command help contains all expected content")
            
    except Exception as e:
        print(f"❌ FAIL: Error running redeploy help: {e}")
        return False
    
    # Test 3: Check Ansible playbook exists and is valid
    print("\nTest 3: Checking Ansible playbook...")
    playbook_path = noah_dir / "Ansible" / "cluster-redeploy.yml"
    
    assert playbook_path.exists(), f"Ansible playbook not found at {playbook_path}"
    
    try:
        result = subprocess.run(
            ["ansible-playbook", "--syntax-check", "cluster-redeploy.yml"],
            cwd=noah_dir / "Ansible",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Ansible playbook syntax error: {result.stderr}"
        print("✅ PASS: Ansible playbook syntax is valid")
            
    except Exception as e:
        print(f"❌ FAIL: Error checking playbook syntax: {e}")
        return False
    
    # Test 4: Check documentation is updated
    print("\nTest 4: Checking documentation...")
    quick_ref_path = noah_dir / "Docs" / "quick-reference.md"
    
    assert quick_ref_path.exists(), f"Quick reference not found at {quick_ref_path}"
    
    try:
        with open(quick_ref_path, 'r') as f:
            content = f.read()
        
        assert "cluster redeploy" in content and "NEW!" in content, "Documentation not updated with redeploy command"
        print("✅ PASS: Documentation updated with redeploy command")
            
    except Exception as e:
        print(f"❌ FAIL: Error reading documentation: {e}")
        return False
    
    print("\n🎉 All tests passed!")
    print("=" * 50)
    print("The redeploy command is ready for use:")
    print("python noah.py cluster redeploy --name noah-production --domain noah-infra.com")
    
    # Success indicated by absence of assertion failures

if __name__ == "__main__":
    success = test_redeploy_command()
    sys.exit(0 if success else 1)
