import os
import sys
import subprocess
import shutil
import pytest


@pytest.mark.skipif(
    not sys.platform.startswith('win'),
    reason='Windows-only launcher script'
)
def test_run_all_bat_dev_smoke():
    """Smoke test: launcher in dev mode headless; no batch parse errors.

    Acceptance:
      - Exit code 0
      - Output contains 'UI launch URL='
      - Output NOT contains 'was unexpected at this time'
    NOTE: First run may be slow (npm install). If npm missing, xfail.
    """
    if shutil.which('npm') is None:
        pytest.xfail('npm not installed – skipping launcher smoke test')
    env = os.environ.copy()
    # Headless: no browser pop, ensure we do not pause at end
    env['MIA_NO_BROWSER'] = '1'
    env['MIA_LAUNCH_STAY'] = '0'
    # Fast-path: skip all UI build/start for speed in CI
    env['MIA_LAUNCH_SMOKE'] = '1'
    # Reuse existing venv; creation handled by script.
    cmd = [r'scripts\launch\run_all.bat', 'dev']
    proc = subprocess.run(
        cmd, capture_output=True, text=True, env=env, timeout=600
    )
    stdout = proc.stdout + '\n' + proc.stderr
    assert proc.returncode == 0, (
        f'launcher exited {proc.returncode}\n--- OUTPUT ---\n{stdout[:2000]}'
    )
    assert 'UI launch URL=' in stdout, (
        f'Missing UI launch URL line. Head:\n{stdout[:1200]}'
    )
    assert (
        'was unexpected at this time' not in stdout.lower()
    ), 'Batch parser error detected'


def test_launcher_script_no_forbidden_if_parenthesis():
    """Guard: ensure script does not contain problematic 'if (' pattern.

    Batch `if (` constructs often arise from POSIX->CMD adaptations and can
    trigger 'was unexpected at this time' errors with delayed expansion.
    """
    path = os.path.join('scripts', 'launch', 'run_all.bat')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'if (' not in content, (
        "Forbidden pattern 'if (' found in run_all.bat"
    )


def test_launcher_smoke_echo_has_no_parentheses():
    """Guard: SMOKE echo line has no parentheses."""
    path = os.path.join('scripts', 'launch', 'run_all.bat')
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Identify the SMOKE block line
    target = [ln for ln in lines if 'SMOKE mode enabled' in ln]
    assert target, 'SMOKE echo line not found'
    for ln in target:
        assert '(' not in ln and ')' not in ln, (
            'Parentheses found in SMOKE echo line'
        )
