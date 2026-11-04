"""Managed command tests use only disposable test endpoints and homes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_live import Fixture, ROOT, client
import managed


class ManagedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cadex-managed-')
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)
        self.job = self.root / 'source.il'
        self.job.write_text('cadexReport(list("fixture-result"))\n')
        self.target = {'library': 'fixture_lib', 'cell': 'fixture_cell', 'view': 'schematic'}
    def tearDown(self):
        self.fixture.close()
        self.temp.cleanup()
    def test_new_job_is_private_and_outside_project(self):
        result = managed.new_job(self.root, 'test / name')
        path = Path(result['job'])
        self.assertTrue(path.is_relative_to(self.root / 'jobs'))
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertIn('cadexReport', path.read_text())
        self.assertEqual(self.fixture.requests, [])
    def test_verified_api_reference_and_invented_api_rejection(self):
        data = managed.api_help('dbFindOpenCellViewByName', docroot=str(self.root))
        self.assertIn('libName', data['signature'])
        with self.assertRaises(client.LiveError): managed.api_help('dbFindOpenCellViewByType', docroot=str(self.root))
        with self.assertRaises(client.LiveError): managed.api_help('../../etc/passwd')
        self.assertEqual(self.fixture.requests, [])
    def test_lifecycle_save_and_nested_load_guards(self):
        for text in ['exit(0)', '(quit)', 'dbSave(cadexCV)', 'load("bad.il")', 'hiCloseWindow(cadexWindow)']:
            self.job.write_text(text)
            with self.assertRaises(client.LiveError): managed.validate_script(self.job)
        self.job.write_text('; exit(0) is forbidden\ncadexReport("exit(0) is just text")')
        managed.validate_script(self.job)
        self.assertEqual(self.fixture.requests, [])
    def test_managed_identity_audit_and_check_save_contract(self):
        result = managed.execute(self.root, self.fixture.record, self.job, self.target, save=True)
        self.assertTrue(result['saved'])
        self.assertEqual(result['final_check'], [0, 0])
        run = Path(result['run'])
        request = json.loads((run / 'request.json').read_text())
        self.assertNotIn('token', request)
        self.assertEqual(request['sha256'], hashlib.sha256(self.job.read_bytes()).hexdigest())
        self.assertEqual((run / 'status').read_text(), '0\n')
        self.assertTrue((run / 'completion.ok').exists())
        self.assertEqual([r[0] for r in self.fixture.requests], ['cadexLiveIdentity', 'load', 'load', 'cadexJobRun'])
        args = self.fixture.requests[-1][1]
        self.assertEqual(args[1:4], ['fixture_lib', 'fixture_cell', 'schematic'])
        self.assertEqual(args[-3:], [True, None, None])
        self.assertTrue(self.fixture.thread.is_alive())
    def test_failed_identity_does_not_load_or_run_and_records_failure(self):
        self.fixture.wrong_identity = True
        with self.assertRaisesRegex(client.LiveError, 'handshake'):
            managed.execute(self.root, self.fixture.record, self.job, self.target)
        self.assertEqual([r[0] for r in self.fixture.requests], ['cadexLiveIdentity'])
        runs = list((self.root / 'runs').iterdir())
        self.assertEqual((runs[0] / 'status').read_text(), '2\n')
        self.assertTrue((runs[0] / 'failure.json').exists())
        self.assertFalse((runs[0] / 'completion.ok').exists())
    def test_installed_managed_commands_use_fixture_only(self):
        home = self.root / 'installed'
        installed = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(home)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        helper = home / '.codex/scripts/virtuoso-live'
        common = [str(helper), '--state-dir', str(self.root)]
        generated = subprocess.run(common + ['new-job', '--name', 'isolated'], capture_output=True, text=True)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.assertTrue(Path(json.loads(generated.stdout)['job']).is_file())
        inspected = subprocess.run(common + ['inspect', '--library', 'fixture_lib', '--cell', 'fixture_cell', '--view', 'schematic'], capture_output=True, text=True)
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        self.assertFalse(json.loads(inspected.stdout)['saved'])
        self.assertTrue(self.fixture.requests[-1][1][-1])
        executed = subprocess.run(common + ['skill', str(self.job), '--library', 'fixture_lib', '--cell', 'fixture_cell', '--view', 'schematic', '--save'], capture_output=True, text=True)
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertTrue(json.loads(executed.stdout)['saved'])
        self.assertTrue(self.fixture.thread.is_alive())


if __name__ == '__main__':
    unittest.main(verbosity=2)
