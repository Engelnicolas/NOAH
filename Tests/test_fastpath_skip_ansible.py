#!/usr/bin/env python3
"""Test NOAH_SKIP_ANSIBLE fast path in `deploy all`.
Ensures:
- Encrypted or plaintext canonical secrets file created
- Authentik credential block printed
- Ansible playbook NOT invoked (inferred by absence of typical playbook output token)
"""

import os
from pathlib import Path
from click.testing import CliRunner
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import noah  # type: ignore

PLAINTEXT = Path('Secrets/canonical-secrets.yaml')
ENCRYPTED = Path('Secrets/canonical-secrets.enc.yaml')

def test_fastpath_skip_ansible():
    # Clean previous artifacts
    if PLAINTEXT.exists():
        PLAINTEXT.unlink()
    if ENCRYPTED.exists():
        ENCRYPTED.unlink()

    os.environ['NOAH_SKIP_ANSIBLE'] = 'true'

    runner = CliRunner()
    result = runner.invoke(noah.cli, ['deploy', 'all', '--domain', 'example.fast'])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert PLAINTEXT.exists() or ENCRYPTED.exists(), "Canonical secrets file not created in fast path"
    out = result.output
    assert 'AUTHENTIK ADMIN ACCESS' in out, "Credential header missing"
    # Heuristic: playbook output phrase used in full run should be absent after early exit
    assert 'Running optimized deployment playbook' not in out, "Playbook run text should not appear in fast path"
