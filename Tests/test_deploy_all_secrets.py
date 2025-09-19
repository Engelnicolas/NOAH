#!/usr/bin/env python3
"""End-to-end (mocked) test for `deploy all` ensuring Authentik secrets are generated
before credential retrieval. Uses NOAH_SKIP_ANSIBLE to bypass real Ansible execution.
"""

import os
from pathlib import Path
from click.testing import CliRunner

# Ensure project root is on path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import noah  # type: ignore

CANONICAL_FILE = Path('Secrets/canonical-secrets.yaml')


def test_deploy_all_generates_authentik_secrets():
    # Remove canonical file if exists to simulate fresh run
    if CANONICAL_FILE.exists():
        CANONICAL_FILE.unlink()

    # Set env to skip actual Ansible
    os.environ['NOAH_SKIP_ANSIBLE'] = 'true'

    runner = CliRunner()
    result = runner.invoke(noah.cli, ['deploy', 'all', '--domain', 'example.local'])

    # Basic CLI success
    assert result.exit_code == 0, f"CLI exited with non-zero: {result.output}"

    # Canonical secrets file should exist now
    assert CANONICAL_FILE.exists(), "canonical-secrets.yaml was not created during deploy all"

    content = CANONICAL_FILE.read_text()
    assert 'authentik:' in content, "Authentik service section missing in canonical secrets file"
    assert 'bootstrap_password:' in content, "bootstrap_password entry missing for Authentik"

    # Credential display block should reference AUTHENTIK ADMIN ACCESS
    assert 'AUTHENTIK ADMIN ACCESS' in result.output, "Credential block not printed"

    # Should not show retrieval error
    assert 'Could not retrieve credentials' not in result.output, f"Unexpected credential retrieval error: {result.output}"

    print('✓ deploy all generates authentik secrets and displays credentials (mocked)')

if __name__ == '__main__':
    test_deploy_all_generates_authentik_secrets()
