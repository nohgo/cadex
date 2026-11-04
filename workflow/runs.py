"""Unique runs, provenance and explicit source freshness; no automatic replay."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from project import Error, inside


def digest(path):
    with Path(path).open('rb') as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise Error('Input file is missing: ' + str(path))
    return {'path': str(path), 'sha256': digest(path)}


def fresh(manifest):
    changed = []
    for item in manifest.get('post_inputs', manifest.get('inputs', [])):
        p = Path(item['path'])
        if not p.is_file() or digest(p) != item['sha256']:
            changed.append(str(p))
    return changed


def load_run(path, expected=None):
    p = Path(path).expanduser().resolve()
    data = json.loads((p / 'manifest.json').read_text())
    if data.get('schema') != 1 or data.get('state') != 'complete':
        raise Error('Dependency is not a completed managed run: ' + str(p))
    marker = p / 'completion.ok'
    if not marker.is_file() or marker.read_text() != 'cadex-complete\n':
        raise Error('Dependency completion marker is missing or invalid: ' + str(p))
    if expected and data.get('stage') != expected:
        raise Error('Wrong run stage; expected ' + expected)
    if fresh(data):
        raise Error('Dependency source changed; regenerate it before reuse: ' + str(p))
    for name, item in data.get('artifacts', {}).items():
        artifact = p / item['path']
        if not inside(p, artifact) or not artifact.is_file() or digest(artifact) != item['sha256']:
            raise Error('Dependency artifact changed or missing: ' + name)
    return p, data


@contextmanager
def serialized(project):
    import fcntl
    directory = project['agent'] / 'work'
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(directory / 'licensed-run.lock'), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Error('Another managed licensed run is active in this project')
        yield
    finally:
        os.close(fd)


class Run:
    def __init__(self, project, stage, label, inputs=(), conditions=None):
        slug = re.sub(r'[^A-Za-z0-9_-]+', '-', label).strip('-')[:64]
        if not slug:
            raise Error('Provide a descriptive run label')
        if not (project['cadence'] / 'cds.lib').is_file():
            raise Error('No cds.lib in configured Cadence launch directory; setup was not run')
        parent = project['results'] / stage / slug
        parent.mkdir(parents=True, exist_ok=True)
        self.path = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_'), dir=str(parent)))
        for name in ['setup', 'native', 'inputs', 'tmp', 'cache']:
            (self.path / name).mkdir(mode=0o700)
        self.data = {'schema': 1, 'stage': stage, 'label': label, 'state': 'running',
                     'project': str(project['root']), 'cadence': str(project['cadence']),
                     'created_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                     'inputs': [identity(p) for p in list(inputs) + [project['cadence'] / 'cds.lib'] + ([project['root'] / 'cadex.json'] if not project['legacy'] else [])], 'declared_conditions': conditions or {},
                     'artifacts': {}, 'engineering_acceptance': 'not_assessed'}
        self.write()

    def write(self):
        p = self.path / 'manifest.json'
        temporary = p.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, indent=2, allow_nan=False) + '\n')
        temporary.replace(p)

    def artifact(self, name, path):
        path = Path(path).resolve()
        if not inside(self.path, path):
            raise Error('Artifact escaped managed run: ' + str(path))
        self.data['artifacts'][name] = {'path': str(path.relative_to(self.path)), 'sha256': digest(path)}

    def finish(self, native, evidence):
        self.data.update(native_exit=native, evidence=evidence)
        changed = fresh(self.data)
        self.data['changed_inputs'] = changed
        self.data['state'] = 'complete' if native == 0 and not changed else 'failed' if native else 'inconclusive'
        self.data['finished_utc'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.write()
        if self.data['state'] == 'complete':
            (self.path / 'completion.ok').write_text('cadex-complete\n')

    def fail(self, message, native=None):
        self.data.update(state='failed', error=str(message), native_exit=native,
                         finished_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
        self.write()


def status(project):
    rows = []
    for file in sorted(project['results'].glob('*/*/*/manifest.json')):
        try:
            data = json.loads(file.read_text())
            changed = fresh(data)
            state = data['state']
            if state == 'complete':
                marker = file.parent / 'completion.ok'
                if not marker.is_file() or marker.read_text() != 'cadex-complete\n':
                    state = 'incomplete'
            rows.append({'run': str(file.parent), 'stage': data['stage'], 'label': data['label'],
                         'state': 'stale' if changed else state, 'changed_inputs': changed,
                         'engineering_acceptance': data.get('engineering_acceptance', 'not_assessed')})
        except (ValueError, OSError, KeyError) as exc:
            rows.append({'run': str(file.parent), 'state': 'invalid', 'error': str(exc)})
    return rows
