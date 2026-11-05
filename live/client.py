"""Cadex opt-in live client. Discovery never scans or attaches to GUI processes."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys
import time


class LiveError(RuntimeError):
    pass


class NoConnectionError(LiveError):
    pass


def load_config():
    return json.loads((Path(__file__).parent / 'config.json').read_text())


def process_stamp(pid):
    # /proc names may contain spaces or parentheses; field 22 is starttime.
    text = Path('/proc/{}/stat'.format(int(pid))).read_text()
    return text[text.rfind(')') + 2:].split()[19]


def private_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    s = path.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o077:
        raise LiveError('State directory must be a private, owned directory: {}'.format(path))
    return path


def socket_path(session_id):
    if not re.fullmatch(r'cadex_[a-f0-9]{32}', session_id):
        raise LiveError('Invalid Cadex session id')
    return Path('/tmp/skill-server-{}.sock'.format(session_id))


def check_record(record):
    required = {'schema', 'opted_in', 'id', 'token', 'host', 'uid', 'gui_pid',
                'gui_start', 'server_pid', 'server_start'}
    if not isinstance(record, dict) or not required.issubset(record):
        raise LiveError('Invalid session record')
    if record['schema'] != 1 or record['opted_in'] is not True:
        raise LiveError('Session was not explicitly opted in')
    if record['host'] != socket.gethostname():
        raise LiveError('Session belongs to host {}'.format(record['host']))
    if record['uid'] != os.getuid():
        raise LiveError('Session belongs to another account')
    if not re.fullmatch(r'[a-f0-9]{64}', record['token']):
        raise LiveError('Invalid session nonce')
    for label in ['gui', 'server']:
        try:
            if process_stamp(record[label + '_pid']) != record[label + '_start']:
                raise LiveError('Stale {} process identity'.format(label))
        except (OSError, ValueError, IndexError):
            raise LiveError('Stale {} process'.format(label))
    path = socket_path(record['id'])
    try:
        s = path.lstat()
    except OSError:
        raise LiveError('Stale session: bridge socket is missing')
    if not stat.S_ISSOCK(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o077:
        raise LiveError('Bridge socket is not private and owned')
    return record


def records(state_dir):
    directory = Path(state_dir) / 'sessions'
    if not directory.exists():
        return []
    private_directory(directory)
    result = []
    for path in sorted(directory.glob('*.json')):
        entry = {'id': path.stem, 'state': 'invalid'}
        try:
            s = path.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o077:
                raise LiveError('Session record is not private and owned')
            if s.st_size > 8192:
                raise LiveError('Oversized session record')
            record = json.loads(path.read_text())
            if record.get('id') != path.stem:
                raise LiveError('Session filename/identity mismatch')
            check_record(record)
            entry.update(state='registered', host=record['host'], gui_pid=record['gui_pid'])
            entry['_record'] = record
        except (LiveError, OSError, ValueError, KeyError, TypeError) as exc:
            entry['reason'] = str(exc)
        result.append(entry)
    return result


def select_record(entries, session_id=None):
    if session_id:
        matches = [e for e in entries if e['id'] == session_id]
        if not matches:
            raise LiveError('Requested session is not registered')
        if matches[0]['state'] != 'registered':
            raise LiveError(matches[0].get('reason', 'Invalid session'))
        return matches[0]['_record']
    valid = [e for e in entries if e['state'] == 'registered']
    if len(valid) > 1:
        raise LiveError('Ambiguous sessions; choose --session from status: ' +
                        ', '.join(e['id'] for e in valid))
    # Do not silently ignore stale/foreign entries and select some other GUI.
    if any(e['state'] != 'registered' for e in entries):
        raise LiveError('Stale or foreign session records; inspect status and choose --session explicitly')
    if not valid:
        raise NoConnectionError('No opted-in live GUI connection')
    return valid[0]['_record']


@contextmanager
def session_lock(state_dir, session_id):
    directory = private_directory(Path(state_dir) / 'locks')
    path = directory / (session_id + '.lock')
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        s = os.fstat(fd)
        if s.st_uid != os.getuid() or s.st_mode & 0o077:
            raise LiveError('Request lock is not private and owned')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LiveError('Session is busy; another Cadex request is running')
        yield
    finally:
        os.close(fd)


def open_workspace(record, timeout):
    # Real SkillBridge translator/API, with bounded I/O and no implicit resend.
    # A failed edit is never retried automatically: it may already have applied.
    from skillbridge import Workspace
    from skillbridge.client.channel import create_channel_class

    class BoundedChannel(create_channel_class()):
        def _send_only(self, data):
            data = data.encode()
            if len(data) > self.max_transmission_length:
                raise LiveError('Request exceeds SkillBridge transmission limit')
            self.socket.sendall(('{:10}'.format(len(data))).encode() + data)

        def close(self):
            try:
                if self.connected:
                    self.socket.sendall(b'         6$close')
            except OSError:
                pass
            finally:
                self.socket.close()
                self.connected = False

        def receive_exact(self, count):
            result = bytearray()
            while len(result) < count:
                part = self.socket.recv(count - len(result))
                if not part:
                    raise LiveError('Bridge disconnected; outcome may be partial; inspect before retrying')
                result.extend(part)
            return bytes(result)

        def _receive_only(self):
            count = int(self.receive_exact(10))
            if count < 0 or count > 1000000:
                raise LiveError('Invalid response length')
            return self.decode_response(self.receive_exact(count).decode())

    channel = BoundedChannel(record['id'])
    channel.socket.settimeout(timeout)
    peer_pid, peer_uid, _ = struct.unpack('3i', channel.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    if peer_pid != record['server_pid'] or peer_uid != record['uid']:
        channel.close()
        raise LiveError('Bridge peer process/account identity changed')
    return Workspace(channel, record['id'])


def validate_job(job):
    if not isinstance(job, dict) or set(job) - {'library', 'cell', 'view', 'operations', 'save'}:
        raise LiveError('Job must contain only library, cell, view, operations, and optional save')
    for key in ['library', 'cell', 'view']:
        if not isinstance(job.get(key), str) or not job[key] or len(job[key]) > 255:
            raise LiveError('Missing or invalid ' + key)
    if job['view'] not in ['schematic', 'layout']:
        raise LiveError('Only named schematic/layout views are supported')
    if type(job.get('save', False)) is not bool:
        raise LiveError('save must be an explicit boolean')
    operations = job.get('operations')
    if not isinstance(operations, list) or not 1 <= len(operations) <= 100:
        raise LiveError('Provide 1 to 100 named operations')
    wire = []
    for op in operations:
        if not isinstance(op, dict) or not isinstance(op.get('instance'), str) or not op['instance']:
            raise LiveError('Each operation needs an exact instance name')
        action = op.get('action')
        allowed = {'action', 'instance'}
        if action == 'move':
            allowed |= {'origin', 'expect_origin'}
            for key in ['origin', 'expect_origin']:
                value = op.get(key)
                if key == 'expect_origin' and value is None:
                    continue
                if not isinstance(value, list) or len(value) != 2 or any(type(n) not in [int, float] or not math.isfinite(n) for n in value):
                    raise LiveError(key + ' must be two finite user-unit coordinates')
            wire.append([action, op['instance'], op['origin'], op.get('expect_origin')])
        elif action == 'parameter':
            allowed |= {'name', 'value', 'expect_value'}
            if not isinstance(op.get('name'), str) or not op['name']:
                raise LiveError('Parameter name is required')
            value = op.get('value')
            if type(value) not in [str, int, float, bool] or isinstance(value, float) and not math.isfinite(value):
                raise LiveError('Parameter value must be a finite scalar or CDF string')
            if 'expect_value' in op and type(op['expect_value']) not in [str, int, float, bool]:
                raise LiveError('Invalid expected parameter value')
            wire.append([action, op['instance'], op['name'], value, op.get('expect_value')])
        elif action == 'inspect':
            wire.append([action, op['instance']])
        else:
            raise LiveError('Unsupported operation: {}'.format(action))
        if set(op) - allowed:
            raise LiveError('Unexpected operation fields')
    return wire


def run_job(state_dir, record, job, timeout=30):
    wire = validate_job(job)
    with session_lock(state_dir, record['id']):
        check_record(record)
        ws = open_workspace(record, timeout)
        try:
            identity = ws['cadexLiveIdentity']()
            expected = [record['id'], record['token'], record['host'], record['gui_pid']]
            if identity != expected:
                raise LiveError('GUI handshake mismatch; refusing to edit')
            result = ws['cadexLiveRun'](record['token'], job['library'], job['cell'], job['view'], wire, job.get('save', False))
            if (not isinstance(result, list) or len(result) != 7 or result[:3] != [job['library'], job['cell'], job['view']]
                    or result[3] not in ['a', 'w'] or not isinstance(result[5], list) or len(result[5]) != len(wire)
                    or any(not isinstance(change, list) or change[:2] != op[:2] for change, op in zip(result[5], wire))
                    or bool(result[6]) != job.get('save', False)):
                raise LiveError('Unexpected target/readback; inspect GUI before retrying')
            return {'session': record['id'], 'host': record['host'], 'gui_pid': record['gui_pid'],
                    'library': result[0], 'cell': result[1], 'view': result[2],
                    'mode': result[3], 'reused_window': bool(result[4]), 'changes': result[5],
                    'saved': bool(result[6]), 'visual_verification': 'pending user observation'}
        finally:
            ws.close()


def main(argv=None):
    config = load_config()
    parser = argparse.ArgumentParser(description='Opt-in live Virtuoso editing; never attaches automatically')
    parser.add_argument('--state-dir', default=config['state_dir'])
    parser.add_argument('--session', help='Explicit registered session, before or after the operation')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('status', help='Registry/process/socket metadata only; no GUI calls')
    sub.add_parser('attach-command', help='Print the one-time CIW action; do not execute it')
    new = sub.add_parser('new-job', help='Create a contained job scaffold outside the project')
    new.add_argument('--name', default='job')
    api = sub.add_parser('api', help='Read verified recipes/installed release documentation; no GUI access')
    api.add_argument('name', nargs='?')
    for command in ['skill', 'inspect']:
        action = sub.add_parser(command, help='Managed named-view SKILL job' if command == 'skill' else 'Read named view inventory, pins, CDF, wires')
        if command == 'skill':
            action.add_argument('job')
            action.add_argument('--save', action='store_true')
            action.add_argument('--allow-existing-edits', action='store_true')
        for key in ['library', 'cell', 'view']: action.add_argument('--' + key, required=True)
        action.add_argument('--session', default=argparse.SUPPRESS)
        action.add_argument('--timeout', type=float, default=60)
    run = sub.add_parser('run', help='Run a named-operation JSON job in an explicitly connected GUI')
    run.add_argument('job')
    run.add_argument('--session', default=argparse.SUPPRESS)
    run.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    attach = 'load({})'.format(json.dumps(config['bootstrap']))
    try:
        if args.command == 'attach-command':
            print(attach)
            return 0
        if args.command in ['new-job', 'api']:
            import managed
            value = managed.new_job(args.state_dir, args.name) if args.command == 'new-job' else managed.api_help(args.name)
            print(json.dumps(value, indent=2))
            return 0
        entries = records(args.state_dir)
        if args.command == 'status':
            clean = [{k: v for k, v in e.items() if k != '_record'} for e in entries]
            print(json.dumps({'sessions': clean, 'attach_command': attach, 'contacts_gui': False}, indent=2))
            return 0
        if args.command in ['skill', 'inspect']:
            import managed
            if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
                raise LiveError('Timeout must be between 0 and 300 seconds')
            record = select_record(entries, args.session)
            target = {key: getattr(args, key) for key in ['library', 'cell', 'view']}
            inspect_only = args.command == 'inspect'
            job = str(Path(__file__).parent / 'inspect.il') if inspect_only else args.job
            value = managed.execute(args.state_dir, record, job, target,
                                    save=False if inspect_only else args.save,
                                    allow_existing=False if inspect_only else args.allow_existing_edits,
                                    inspection=inspect_only, timeout=args.timeout)
            print(json.dumps(value, indent=2))
            return 0
        if args.command != 'run':
            parser.print_help()
            return 64
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
            raise LiveError('Timeout must be between 0 and 300 seconds')
        job_path = Path(args.job)
        if job_path.stat().st_size > 100000:
            raise LiveError('Job is too large')
        job = json.loads(job_path.read_text())
        validate_job(job)
        record = select_record(entries, args.session)
        result = run_job(args.state_dir, record, job, args.timeout)
        print(json.dumps(result, indent=2))
        return 0
    except (LiveError, OSError, ValueError, KeyError, ImportError, RuntimeError) as exc:
        error = {'error': str(exc)}
        if isinstance(exc, NoConnectionError):
            error['attach_command'] = attach
        if args.command in ['run', 'skill']:
            error['retry'] = 'Do not blindly retry a failed edit; inspect its outcome first.'
        print(json.dumps(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
