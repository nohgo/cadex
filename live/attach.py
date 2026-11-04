"""Executed ONLY by the explicitly loaded CIW bootstrap via direct IPC."""
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import struct
import sys
import time
import uuid

from client import LiveError, load_config, private_directory, process_stamp, socket_path


def gui_ancestor():
    pid = os.getppid()
    for _ in range(8):
        comm = Path('/proc/{}/comm'.format(pid)).read_text().strip()
        if comm == 'virtuoso':
            return pid
        fields = Path('/proc/{}/status'.format(pid)).read_text().splitlines()
        pid = int(next(line.split()[1] for line in fields if line.startswith('PPid:')))
        if pid <= 1:
            break
    raise LiveError('Attach must be invoked by the CIW bootstrap, not an ordinary shell')


def main():
    # Guard BEFORE Workspace.open(direct=True): stdin alone is not authorization.
    gui_pid = gui_ancestor()
    from skillbridge import Workspace
    config = load_config()
    root = private_directory(config['state_dir'])
    directory = private_directory(root / 'sessions')
    ws = Workspace.open(direct=True)
    session_id = 'cadex_' + uuid.uuid4().hex
    token = secrets.token_hex(32)
    started = False
    try:
        ws['cadexLiveInit'](session_id, token, socket.gethostname(), gui_pid)
        started = bool(ws['pyStartServer'](id=session_id, python=sys.executable, singleMode=True, timeout=30))
        if not started:
            raise LiveError('Existing SkillBridge server was not replaced')
        path = socket_path(session_id)
        deadline = time.monotonic() + 10
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        info = path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise LiveError('Bridge socket did not start privately')
        # Kernel peer identity only; sends no GUI command through this socket.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(2)
            peer.connect(str(path))
            server_pid, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.getuid():
            raise LiveError('Bridge peer account mismatch')
        record = {'schema': 1, 'opted_in': True, 'id': session_id, 'token': token,
                  'host': socket.gethostname(), 'uid': uid, 'gui_pid': gui_pid,
                  'gui_start': process_stamp(gui_pid), 'server_pid': server_pid,
                  'server_start': process_stamp(server_pid)}
        temporary = directory / ('.' + session_id + '.tmp')
        fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(record, out)
            out.write('\n')
        temporary.replace(directory / (session_id + '.json'))
        print('Cadex live session enabled: {} on {} (GUI PID {}).'.format(session_id, record['host'], gui_pid), file=sys.stderr)
    except Exception:
        ws['cadexLiveRevoke'](token)
        if started:
            ws['pyKillServer']()  # Only the server this attach attempt just started.
        raise
    finally:
        ws.close()


if __name__ == '__main__':
    main()
