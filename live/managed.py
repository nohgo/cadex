"""Contained jobs and release-specific help for the installed live entrypoint."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
import html


def allocate(state_dir, kind, name='job'):
    from client import private_directory
    parent = private_directory(Path(state_dir) / kind)
    name = re.sub(r'[^A-Za-z0-9_-]+', '-', name).strip('-')[:48] or 'job'
    return Path(tempfile.mkdtemp(prefix=datetime.utcnow().strftime('%Y%m%dT%H%M%SZ_') + name + '_', dir=str(parent)))


def new_job(state_dir, name):
    directory = allocate(state_dir, 'jobs', name)
    path = directory / 'job.il'
    path.write_text('; Managed context: cadexCV, cadexWindow, cadexRunDir.\n'
                    '; Reuse recipes; report task-specific output with cadexReport(...).\n'
                    '; No bridge/Python/target-selection/exit/save glue belongs here.\n'
                    'error("Replace this scaffold with the requested job")\n')
    path.chmod(0o600)
    return {'job': str(path), 'directory': str(directory)}


def validate_script(path):
    from client import LiveError
    path = Path(path)
    if path.stat().st_size > 1000000:
        raise LiveError('SKILL job is too large')
    text = path.read_text()
    code = re.sub(r'"(?:\\.|[^"\\])*"|;[^\n]*', '', text)
    names = r'exit|quit|hiCloseWindow|deCloseWindow|hiSetCurrentWindow|dbClose|dbPurge|dbReopen|pyKillServer|ipcKillProcess|dbSave|schHiCheckAndSave|deOpenCellView|load|evalstring'
    if re.search(r'\b(?:' + names + r')\s*\(|\(\s*(?:' + names + r')(?:\s|\))', code):
        raise LiveError('Job contains lifecycle/target/save or nested-evaluation calls; use managed context, recipes and --save')
    # This catches accidental dangerous glue, not arbitrary trusted-SKILL behavior.
    return text


def api_help(name, runtime=None, docroot='/apps/cds/IC618/doc'):
    from client import LiveError
    runtime = Path(runtime or Path(__file__).parent)
    index = json.loads((runtime / 'api-index.json').read_text())
    if not name:
        return {'apis': sorted(index), 'recipes': ['cadexDescribe', 'cadexInst', 'cadexPin', 'cadexPinEscape', 'cadexStub', 'cadexCreate', 'cadexParam', 'cadexWire', 'cadexDeleteWire', 'cadexExpectConnection', 'cadexExpectNet']}
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', name):
        raise LiveError('API name must be an identifier')
    result = dict(index.get(name, {}), name=name)
    candidates = []
    if result.get('doc'):
        candidates.append(Path(docroot) / result['doc'])
    for folder in ['skdfref', 'skcompref', 'skuiref', 'sklangref', 'cdfuser']:
        candidates.extend((Path(docroot) / folder).glob('*' + name + '*.html'))
    for path in candidates:
        if path.is_file():
            text = html.unescape(re.sub('<[^>]+>', ' ', path.read_text(errors='replace')))
            text = re.sub(r'\s+', ' ', text)
            match = re.search(r'\b' + re.escape(name) + r'\s*\(', text)
            if match:
                result['installed_document'] = str(path)
                result['excerpt'] = text[max(0, match.start()-50):match.start()+3500]
                break
    if len(result) == 1:
        raise LiveError('No verified recipe or installed reference found; do not guess the API')
    return result


def execute(state_dir, record, job, target, save=False, allow_existing=False,
            inspection=False, timeout=60, runtime=None):
    from client import LiveError, session_lock, check_record, open_workspace
    runtime = Path(runtime or Path(__file__).parent)
    for key in ['library', 'cell', 'view']:
        if not isinstance(target.get(key), str) or not target[key] or len(target[key]) > 255:
            raise LiveError('Invalid target ' + key)
    if target['view'] not in ['schematic', 'layout']:
        raise LiveError('Unsupported target view')
    if save and inspection:
        raise LiveError('Inspect-only jobs cannot save')
    if allow_existing and not save:
        raise LiveError('--allow-existing-edits is meaningful only with --save')
    text = validate_script(job)
    directory = allocate(state_dir, 'runs', Path(job).stem)
    copied = directory / 'job.il'
    copied.write_text(text)
    copied.chmod(0o600)
    request = dict(target, session=record['id'], save=save, allow_existing_edits=allow_existing,
                   inspection=inspection, source=str(Path(job).absolute()), sha256=hashlib.sha256(text.encode()).hexdigest())
    (directory / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    try:
        with session_lock(state_dir, record['id']):
            check_record(record)
            ws = open_workspace(record, timeout)
            try:
                expected = [record['id'], record['token'], record['host'], record['gui_pid']]
                if ws['cadexLiveIdentity']() != expected:
                    raise LiveError('GUI handshake mismatch; no job sent')
                ws['load'](str(runtime / 'job.il'))
                ws['load'](str(runtime / 'recipes.il'))
                result = ws['cadexJobRun'](record['token'], target['library'], target['cell'], target['view'],
                                             str(copied), str(directory), save, allow_existing, inspection)
                if (not isinstance(result, list) or len(result) != 9
                        or result[:3] != [target['library'], target['cell'], target['view']]
                        or bool(result[6]) != save):
                    raise LiveError('Managed result/target/save mismatch; inspect outcome before retrying')
                output = dict(target, session=record['id'], gui_pid=record['gui_pid'], host=record['host'],
                              run=str(directory), preexisting_unsaved=bool(result[3]), baseline_check=result[4],
                              final_check=result[5], saved=bool(result[6]), result=result[7], readback=result[8], visual_verification='pending user observation')
                (directory / 'result.json').write_text(json.dumps(output, indent=2) + '\n')
                (directory / 'status').write_text('0\n')
                (directory / 'completion.ok').write_text('cadex-managed-complete\n')
                return output
            finally:
                ws.close()
    except Exception as exc:
        (directory / 'failure.json').write_text(json.dumps({'error': str(exc), 'outcome': 'possibly partial; inspect before retrying'}, indent=2) + '\n')
        (directory / 'status').write_text('2\n')
        raise LiveError('{}; RUN={}'.format(exc, directory))
