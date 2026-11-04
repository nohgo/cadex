"""Batch launcher regression with fake tools; no Cadence execution or license."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BatchHarnessTests(unittest.TestCase):
    def test_smoke_status_marker_and_failure_propagation(self):
        with tempfile.TemporaryDirectory(prefix='cadex-batch-fixture-') as name:
            root = Path(name)
            project = root / 'project'
            project.mkdir()
            (project / 'cds.lib').write_text('; isolated fixture\n')
            launcher = root / 'batch.sh'
            # Redirect only the diagnostic output root; never repurpose HOME.
            launcher.write_text((ROOT / 'scripts/virtuoso-batch.sh').read_text().replace(
                '$HOME/.local/state/codex/virtuoso', str(root / 'diagnostics')))
            tool = root / 'virtuoso-fixture'
            tool.write_text('''#!/bin/bash
if [[ "$1" == -W ]]; then echo 'IC618 fixture'; exit 0; fi
if [[ "${CADEX_FIXTURE_EXIT:-0}" != 0 ]]; then exit "$CADEX_FIXTURE_EXIT"; fi
if [[ "${CADEX_FIXTURE_NO_MARKER:-0}" != 1 ]]; then
  printf 'CODEX_VIRTUOSO_COMPLETE %s\\n' "$CODEX_VIRTUOSO_RUN" > "$CODEX_VIRTUOSO_RUN/completion.ok"
  printf 'CODEX_VIRTUOSO_SMOKE_OK\\nLIBRARY_COUNT 1\\n' > "$CODEX_VIRTUOSO_RUN/smoke.txt"
fi
''')
            tool.chmod(0o700)
            driver = root / 'driver.sh'
            driver.write_text('''#!/bin/bash
cadence_env() { return 0; }
xrun() { echo 'TOOL: xrun 23.09 fixture'; }
type() { if [[ "$1" == -P && "$2" == virtuoso ]]; then printf '%s\\n' "$CADEX_FIXTURE_TOOL"; else builtin type "$@"; fi; }
export -f cadence_env xrun type
exec bash "$1" --project "$2"
''')
            env = dict(os.environ, CADEX_FIXTURE_TOOL=str(tool))
            def run(**overrides):
                return subprocess.run(['bash', str(driver), str(launcher), str(project)],
                                      env=dict(env, **overrides), stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, universal_newlines=True)
            success = run()
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertIn('CODEX_VIRTUOSO_SMOKE_OK', success.stdout)
            self.assertIn('STATUS=0', success.stdout)
            failed = run(CADEX_FIXTURE_EXIT='23')
            self.assertEqual(failed.returncode, 23)
            self.assertIn('STATUS=23', failed.stdout)
            missing = run(CADEX_FIXTURE_NO_MARKER='1')
            self.assertEqual(missing.returncode, 65)
            self.assertFalse((project / 'runs').exists())
            self.assertFalse((project / '.cdsinit').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
