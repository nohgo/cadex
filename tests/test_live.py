"""Unlicensed tests. Every socket/session below is an explicitly created fixture."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cadex_client', ROOT / 'live/client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
sys.modules['client'] = client
sys.path.insert(0, str(ROOT / 'live'))


def parse_call(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    def value():
        token = tokens.pop(0)
        if token.startswith('"'):
            return json.loads(token)
        if token == 'nil': return None
        if token == 't': return True
        if token == '(' or token == 'list':
            if token == '(':
                assert tokens.pop(0) == 'list'
            else:
                assert tokens.pop(0) == '('
            values = []
            while tokens[0] != ')': values.append(value())
            tokens.pop(0)
            return values
        try: return int(token)
        except ValueError: return float(token)
    name = tokens.pop(0)
    assert tokens.pop(0) == '('
    values = []
    while tokens[0] != ')': values.append(value())
    return name, values


class Fixture:
    """Models responses, NOT the untested Cadence database/window implementation."""
    def __init__(self, root):
        self.root = client.private_directory(root)
        self.id = 'cadex_' + uuid.uuid4().hex
        self.token = uuid.uuid4().hex + uuid.uuid4().hex
        self.requests = []
        self.origin = [1.0, 2.0]
        self.open = True
        self.hang = False
        self.wrong_identity = False
        fixture = self
        class Handler(socketserver.BaseRequestHandler):
            def exact(self, count):
                result = bytearray()
                while len(result) < count:
                    part = self.request.recv(count - len(result))
                    if not part: return None
                    result.extend(part)
                return bytes(result)
            def handle(self):
                while True:
                    header = self.exact(10)
                    if not header: return
                    data = self.exact(int(header))
                    if not data or data == b'$close': return
                    name, args = parse_call(data.decode())
                    fixture.requests.append((name, args))
                    if name == 'load':
                        answer = True
                    elif name == 'cadexJobRun':
                        token, lib, cell, view, path, run_dir, save, allow, inspection = args
                        assert token == fixture.token
                        answer = [lib, cell, view, False, [0, 0] if save else None, [0, 0] if save else None, bool(save), [['fixture', 'managed']], [['modified', False]]]
                    elif name == 'cadexLiveIdentity':
                        answer = [fixture.id, 'wrong' if fixture.wrong_identity else fixture.token,
                                  socket.gethostname(), os.getpid()]
                    elif name == 'cadexLiveRun':
                        if fixture.hang:
                            time.sleep(0.4)
                            return
                        token, lib, cell, view, operations, save = args
                        assert token == fixture.token
                        changes = []
                        reused = fixture.open
                        fixture.open = True
                        for op in operations:
                            if op[0] == 'move':
                                changes.append(['move', op[1], fixture.origin, op[2]])
                                fixture.origin = op[2]
                            elif op[0] == 'parameter':
                                changes.append(['parameter', op[1], op[2], '1u', op[3]])
                            else:
                                changes.append(['inspect', op[1], 'fixture_pdk', 'device', fixture.origin, []])
                        answer = [lib, cell, view, 'a', reused, changes, bool(save)]
                    else:
                        raise AssertionError('Unexpected function: ' + name)
                    response = ('success ' + repr(answer)).encode()
                    packet = ('{:10}'.format(len(response))).encode() + response
                    # Exercise fragmented header reads with the real SkillBridge translator.
                    self.request.sendall(packet[:3])
                    self.request.sendall(packet[3:])
        class Server(socketserver.ThreadingUnixStreamServer):
            daemon_threads = True
        self.path = client.socket_path(self.id)
        self.server = Server(str(self.path), Handler)
        self.path.chmod(0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        pid = os.getpid()
        self.record = {'schema': 1, 'opted_in': True, 'id': self.id, 'token': self.token,
                       'host': socket.gethostname(), 'uid': os.getuid(), 'gui_pid': pid,
                       'gui_start': client.process_stamp(pid), 'server_pid': pid,
                       'server_start': client.process_stamp(pid)}
        self.write_record()
    def write_record(self):
        directory = client.private_directory(self.root / 'sessions')
        path = directory / (self.id + '.json')
        path.write_text(json.dumps(self.record))
        path.chmod(0o600)
    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.path.unlink()
        self.thread.join()


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cadex-fixture-')
        self.root = Path(self.temp.name)
        self.fixtures = []
    def tearDown(self):
        for fixture in self.fixtures: fixture.close()
        self.temp.cleanup()
    def fixture(self):
        f = Fixture(self.root)
        self.fixtures.append(f)
        return f
    def job(self, **overrides):
        job = {'library': 'fixture_lib', 'cell': 'fixture_cell', 'view': 'layout',
               'operations': [{'action': 'move', 'instance': 'I3', 'origin': [10, 20]}]}
        job.update(overrides)
        return job
    def test_missing_session_does_not_scan_or_connect(self):
        self.assertEqual(client.records(self.root), [])
        with self.assertRaisesRegex(client.LiveError, 'No opted-in'):
            client.select_record([])
    def test_status_is_metadata_only(self):
        f = self.fixture()
        entries = client.records(self.root)
        self.assertEqual(entries[0]['state'], 'registered')
        self.assertEqual(f.requests, [])
    def test_real_skillbridge_reconnect_move_reverse_closed_view_fixture(self):
        f = self.fixture()
        result = client.run_job(self.root, f.record, self.job())
        self.assertTrue(result['reused_window'])
        self.assertEqual(result['changes'][0][3], [10, 20])
        self.assertFalse(result['saved'])
        # A completely new short-lived workspace reconnects; GUI fixture stays alive.
        f.open = False
        result = client.run_job(self.root, f.record, self.job(operations=[{
            'action': 'move', 'instance': 'I3', 'origin': [1, 2], 'expect_origin': [10, 20]}]))
        self.assertFalse(result['reused_window'])
        self.assertEqual(f.origin, [1, 2])
        self.assertTrue(f.thread.is_alive())
    def test_installed_helper_cli_reconnects_to_fixture_only(self):
        f = self.fixture()
        home = self.root / 'installed-home'
        install = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(home)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(install.returncode, 0, install.stderr)
        helper = home / '.codex/scripts/virtuoso-live'
        job = self.root / 'edit.json'
        job.write_text(json.dumps(self.job()))
        def run():
            return subprocess.run([str(helper), '--state-dir', str(self.root), 'run', str(job)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        first = run()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)['changes'][0][3], [10, 20])
        f.open = False
        job.write_text(json.dumps(self.job(operations=[{'action': 'move', 'instance': 'I3', 'origin': [1, 2]}])))
        second = run()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout)['reused_window'])
        self.assertEqual(f.origin, [1, 2])
        self.assertTrue(f.thread.is_alive())

    def test_upstream_server_wrapper_with_fake_skill_ipc(self):
        # Real SkillBridge server + real client; ONLY the SKILL interpreter is a fixture.
        home = self.root / 'server-home'
        installed = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(home)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        sid = 'cadex_' + uuid.uuid4().hex
        token = uuid.uuid4().hex + uuid.uuid4().hex
        path = client.socket_path(sid)
        child = subprocess.Popen([sys.executable, str(home / '.codex/share/cadex-live/server.py'),
                                  sid, 'WARNING', '--single', '--timeout', '2'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 universal_newlines=True)
        def fake_skill():
            for line in child.stdout:
                name, args = parse_call(line.strip())
                if name == 'cadexLiveIdentity':
                    answer = [sid, token, socket.gethostname(), os.getpid()]
                else:
                    nonce, lib, cell, view, operations, save = args
                    op = operations[0]
                    answer = [lib, cell, view, 'a', True,
                              [['move', op[1], [1, 2], op[2]]], bool(save)]
                try:
                    child.stdin.write('success ' + repr(answer) + '\n')
                    child.stdin.flush()
                except BrokenPipeError:
                    return
        pump = threading.Thread(target=fake_skill, daemon=True)
        pump.start()
        try:
            deadline = time.monotonic() + 5
            while not path.exists() and time.monotonic() < deadline and child.poll() is None:
                time.sleep(0.02)
            self.assertTrue(path.exists())
            record = {'schema': 1, 'opted_in': True, 'id': sid, 'token': token,
                      'host': socket.gethostname(), 'uid': os.getuid(), 'gui_pid': os.getpid(),
                      'gui_start': client.process_stamp(os.getpid()), 'server_pid': child.pid,
                      'server_start': client.process_stamp(child.pid)}
            for origin in [[10, 20], [1, 2]]:
                result = client.run_job(self.root, record, self.job(operations=[{
                    'action': 'move', 'instance': 'I3', 'origin': origin}]))
                self.assertEqual(result['changes'][0][3], origin)
                self.assertIsNone(child.poll(), 'Client disconnect must not kill the bridge')
        finally:
            child.terminate()  # Only this fixture's own Python server; never a GUI.
            child.wait(timeout=5)
            for stream in [child.stdin, child.stdout, child.stderr]: stream.close()
            if path.exists(): path.unlink()
            pump.join(timeout=2)

    def test_parameter_units_and_explicit_save_are_transmitted(self):
        f = self.fixture()
        job = self.job(view='schematic', save=True, operations=[{
            'action': 'parameter', 'instance': 'MP0', 'name': 'w', 'value': '2u'}])
        result = client.run_job(self.root, f.record, job)
        self.assertTrue(result['saved'])
        self.assertEqual(result['changes'][0][-1], '2u')
    def test_ambiguous_requires_explicit_selection(self):
        first, second = self.fixture(), self.fixture()
        with self.assertRaisesRegex(client.LiveError, 'Ambiguous'):
            client.select_record(client.records(self.root))
        self.assertEqual(client.select_record(client.records(self.root), second.id)['id'], second.id)
        self.assertEqual(first.requests + second.requests, [])
    def test_stale_pid_foreign_host_and_private_permissions(self):
        f = self.fixture()
        for key, value in [('gui_start', '0'), ('host', 'another-host'), ('opted_in', False)]:
            previous = f.record[key]
            f.record[key] = value
            f.write_record()
            self.assertEqual(client.records(self.root)[0]['state'], 'invalid')
            f.record[key] = previous
        f.write_record()
        f.path.chmod(0o666)
        self.assertEqual(client.records(self.root)[0]['state'], 'invalid')
        self.assertEqual(f.requests, [])
    def test_handshake_mismatch_never_sends_edit(self):
        f = self.fixture()
        f.wrong_identity = True
        with self.assertRaisesRegex(client.LiveError, 'handshake'):
            client.run_job(self.root, f.record, self.job())
        self.assertEqual([r[0] for r in f.requests], ['cadexLiveIdentity'])
    def test_serialization_busy_fails_without_connecting(self):
        f = self.fixture()
        with client.session_lock(self.root, f.id):
            with self.assertRaisesRegex(client.LiveError, 'busy'):
                client.run_job(self.root, f.record, self.job())
        self.assertEqual(f.requests, [])
    def test_timeout_does_not_resend_edit(self):
        f = self.fixture()
        f.hang = True
        with self.assertRaises((OSError, client.LiveError)):
            client.run_job(self.root, f.record, self.job(), timeout=0.1)
        self.assertEqual([r[0] for r in f.requests].count('cadexLiveRun'), 1)
    def test_schema_rejects_code_and_invalid_geometry(self):
        for job in [self.job(code='exit()'), self.job(operations=[{'action': 'eval', 'instance': 'I3'}]),
                    self.job(operations=[{'action': 'move', 'instance': 'I3', 'origin': [float('nan'), 0]}]),
                    self.job(save='yes')]:
            with self.assertRaises(client.LiveError): client.validate_job(job)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cadex-install-')
        self.home = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def install(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(self.home)] + list(extra),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    def test_install_reinstall_helpers_and_no_activation(self):
        first = self.install()
        self.assertEqual(first.returncode, 0, first.stderr)
        bootstrap = self.home / '.codex/share/cadex-live/bootstrap.il'
        self.assertIn('pyRunScript', bootstrap.read_text())
        self.assertFalse((self.home / '.cdsinit').exists())
        self.assertFalse((self.home / '.bashrc').exists())
        self.assertEqual(list((self.home / '.local/state/cadex/live/sessions').iterdir()), [])
        second = self.install()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn('Installed:', second.stdout)
        helper = self.home / '.codex/scripts/virtuoso-live'
        status = subprocess.run([str(helper), 'status'], stdout=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(status.returncode, 0)
        self.assertEqual(json.loads(status.stdout)['sessions'], [])
        job = self.home / 'job.json'
        job.write_text(json.dumps({'library': 'fixture', 'cell': 'cell', 'view': 'layout',
                                   'operations': [{'action': 'inspect', 'instance': 'I3'}]}))
        missing = subprocess.run([str(helper), 'run', str(job)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn('No opted-in', missing.stderr)
        self.assertIn(str(bootstrap), missing.stderr)
    def test_installer_does_not_touch_legacy_project_files(self):
        legacy = self.home / 'cadence_work/codex-virtuoso/virtuoso-batch.sh'
        legacy.parent.mkdir(parents=True)
        legacy.write_text('leave my project alone\n')
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(legacy.read_text(), 'leave my project alone\n')

    def test_live_setup_resolves_real_resource_without_cli_banner(self):
        import skillbridge
        venv = self.home / '.venvs/cadex-live'
        subprocess.check_call([sys.executable, '-m', 'venv', '--without-pip', str(venv)])
        binary = venv / 'bin/python'
        site = Path(subprocess.check_output([str(binary), '-c', 'import site; print(site.getsitepackages()[0])'], universal_newlines=True).strip())
        (site / 'fixture-skillbridge.pth').write_text(str(Path(skillbridge.__file__).parent.parent) + '\n')
        installed = self.install('--live', '--live-python', sys.executable)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        bootstrap = (self.home / '.codex/share/cadex-live/bootstrap.il').read_text()
        self.assertNotIn('Path to Skill server', bootstrap)
        for line in bootstrap.splitlines():
            if line.startswith('load('):
                self.assertTrue(Path(json.loads(line[len('load('):-1])).is_file())
        self.assertEqual(list((self.home / '.local/state/cadex/live/sessions').iterdir()), [])

    def test_local_changes_are_not_overwritten(self):
        self.assertEqual(self.install().returncode, 0)
        helper = self.home / '.codex/share/cadex-live/client.py'
        helper.write_text('user changes\n')
        again = self.install()
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(helper.read_text(), 'user changes\n')
    def test_attach_refuses_ordinary_shell_before_gui_calls(self):
        self.assertEqual(self.install().returncode, 0)
        attach = self.home / '.codex/share/cadex-live/attach.py'
        result = subprocess.run([sys.executable, str(attach)], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CIW bootstrap', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
