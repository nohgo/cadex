"""Project discovery and non-destructive scaffolding. No EDA processes."""
import hashlib
import json
import os
from pathlib import Path


class Error(RuntimeError):
    pass


def inside(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    return path == root or root in path.parents


def relative_path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise Error('Project paths must be nonempty relative paths')
    path = (root / value).resolve()
    if not inside(root, path):
        raise Error('Project path escapes the project: ' + value)
    return path


def discover(start=None):
    start = Path(start or Path.cwd()).expanduser().resolve()
    if not start.is_dir():
        raise Error('Project directory does not exist: ' + str(start))
    for root in [start] + list(start.parents):
        file = root / 'cadex.json'
        if file.is_file():
            config = json.loads(file.read_text())
            if not isinstance(config, dict) or config.get('schema') != 1 or config.get('mode') not in ['full', 'small']:
                raise Error('Unsupported cadex.json schema/mode')
            if not isinstance(config.get('paths'), dict) or not all(k in config['paths'] for k in ['cadence', 'results', 'agent']):
                raise Error('cadex.json requires cadence/results/agent path definitions')
            if not isinstance(config.get('libraries', {}), dict):
                raise Error('libraries must map names to project-relative paths')
            paths = {k: relative_path(root, config['paths'][k]) for k in ['cadence', 'results', 'agent']}
            # Outputs must never overlap native source or each other.
            for a, b in [('cadence', 'results'), ('cadence', 'agent'), ('results', 'agent')]:
                if paths[a] == paths[b] or ((config['mode'] == 'full' or a == 'results') and (inside(paths[a], paths[b]) or inside(paths[b], paths[a]))):
                    raise Error('Project source/output directories overlap')
            return dict(root=root, config=config, legacy=False, **paths)
    if (start / 'cds.lib').is_file():
        key = hashlib.sha256(str(start).encode()).hexdigest()[:16]
        state = Path.home() / '.local/state/cadex/projects' / key
        return dict(root=start, cadence=start, results=state / 'results', agent=state / 'agent',
                    config={'schema': 1, 'name': start.name, 'profile': None}, legacy=True)
    raise Error('No cadex.json or local cds.lib; initialize a project explicitly')


def show(project):
    return dict({k: str(project[k]) for k in ['root', 'cadence', 'results', 'agent']},
                legacy=project['legacy'], profile=project['config'].get('profile'))


def initialize(path, mode='full', profile=None):
    if mode not in ['full', 'small']:
        raise Error('Unknown project mode')
    root = Path(path).expanduser().absolute()
    adopting = root.is_dir() and any(root.iterdir())
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    if (root / 'cadex.json').exists():
        raise Error('Project already configured; edit cadex.json deliberately, without moving source files')
    cadence = 'cadence' if mode == 'full' else '.'
    config = {'schema': 1, 'name': root.name, 'mode': mode, 'profile': profile,
              'paths': {'cadence': cadence, 'results': 'results', 'agent': 'agent'}, 'libraries': {}}
    for value in [cadence, 'results', 'agent/work', 'agent/designs', 'agent/notes', '.agents/skills']:
        p = relative_path(root, value)
        if p.exists() and not p.is_dir():
            raise Error('Expected a directory; existing file preserved: ' + str(p))
    # All generated files are create-only; adopting a layout never overwrites Cadence setup.
    files = {
        'cadex.json': json.dumps(config, indent=2) + '\n',
        'AGENTS.md': '# Project workflow\n\nRead cadex.json for project paths; run `~/.codex/scripts/cadex project show`.\n'
                     'Use cadence/ as the EDA working directory in full projects, or the configured\n'
                     'launch directory otherwise. Read agent/README.md when creating work or results.\n'
                     'Reuse installed Cadex skills; put only project-specific skills in .agents/skills.\n'
                     'A project or GUI process is not permission to attach; retain per-command review.\n',
        'agent/README.md': '# Agent workspace\n\n'
                           'work/ holds temporary jobs, probes, caches and scratch files (ignored).\n'
                           'designs/<design>/ holds durable intent, requirements and evidence indexes.\n'
                           'notes/ holds project decisions and verified run procedures worth tracking.\n'
                           'Native Cadence source stays in the configured launch directory.\n'
                           'Labeled tool runs go in results/ with manifests, inputs, logs and artifacts.\n'
                           'Run `cadex status` to check completion and source freshness.\n'
                           'Completed tool execution is separate from meeting engineering requirements.\n'
                           'Keep raw results/scratch out of Git; publish selected reports deliberately.\n'
                           'Place reusable project skills in ../.agents/skills for native discovery,\n'
                           'rather than burying SKILL.md files in scratch or duplicating global skills.\n',
    }
    prefix = '/cadence/' if mode == 'full' else '/'
    files['.gitignore'] = '/agent/work/\n/results/\n' + ''.join(prefix + p + '\n' for p in
        ['.cadence/', '.pcdb/', 'xcelium.d/', 'CDS.log*', '*.cdslck', '*.cdslck.*'])
    lib = '# Project library mappings; Cadex initialization never sources /apps/settings here.\n'
    if profile == 'uf-gpdk180':
        lib += ('INCLUDE /apps/cds/IC618/share/cdssetup/cds.lib\n'
                'DEFINE gpdk180 /apps/cds/IC618/local/GPDK180/libs.oa22/gpdk180\n'
                'DEFINE substrateLib /apps/cds/IC618/local/GPDK180/libs.oa22/substrateLib\n')
    files[str(Path(cadence) / 'cds.lib')] = lib
    for value in [cadence, 'results', 'agent/work', 'agent/designs', 'agent/notes', '.agents/skills']:
        relative_path(root, value).mkdir(parents=True, exist_ok=True)
    if mode == 'full' and not adopting:
        for value in ['rtl', 'tb']:
            relative_path(root, value).mkdir(exist_ok=True)
    preserved = []
    for name, text in files.items():
        p = relative_path(root, name)
        if p.exists():
            preserved.append(name)
            continue
        with p.open('x') as f:
            f.write(text)
    return dict(show(discover(root)), preserved=preserved)


def view_file(project, lib, cell, view):
    for value in [lib, cell, view]:
        if not isinstance(value, str) or not value or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in value):
            raise Error('This native recipe requires simple library/cell/view identifiers')
    configured = project['config'].get('libraries', {}).get(lib)
    base = relative_path(project['root'], configured) if configured else project['cadence'] / lib
    filename = {'schematic': 'sch.oa', 'layout': 'layout.oa'}.get(view)
    if not filename:
        raise Error('Supported saved views are schematic and layout')
    p = base / cell / view / filename
    if not p.is_file() or not inside(project['root'], p):
        raise Error('Cannot identify project-owned saved view; configure libraries in cadex.json: ' + str(p))
    return p.resolve()
