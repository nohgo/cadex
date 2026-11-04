"""Native execution and release-specific recipes, with bounded JSON results."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess

from project import Error, inside, view_file
from runs import Run, digest, fresh, identity, load_run, serialized
from formats import schematic_cdl, pex_to_spectre
from skill import check

SETUP = '''set +e +u
set +o pipefail
setup=$1; cwd=$2; shift 2
cd "$setup" || exit 66
source /apps/settings > setup.stdout.log 2> setup.stderr.log
setup_status=$?
printf '%s\\n' "$setup_status" > setup.status
if [ "$setup_status" != 0 ]; then exit "$setup_status"; fi
export PATH=/apps/cds/xcelium2309/tools.lnx86/bin:/apps/cds/xcelium2309/tools/bin:$PATH
cd "$cwd" || exit 66
exec "$@"
'''


def profile(project):
    name = project['config'].get('profile')
    profiles = json.loads((Path(__file__).parent / 'profile.json').read_text())
    if name not in profiles:
        raise Error('Choose a supported technology profile explicitly in cadex.json: ' + ', '.join(profiles))
    return profiles[name]


def execute(run, project, argv, cwd=None, timeout=300, env=None):
    environment = os.environ.copy()
    environment.update(TMPDIR=str(run.path / 'tmp'), MPLCONFIGDIR=str(run.path / 'cache'),
                       PYTHONPYCACHEPREFIX=str(run.path / 'cache/python'))
    environment.update(env or {})
    run.data.update(argv=[str(x) for x in argv], cwd=str(cwd or project['cadence']))
    run.write()
    with (run.path / 'stdout.log').open('w') as out, (run.path / 'stderr.log').open('w') as err:
        try:
            proc = subprocess.Popen(['bash', '-c', SETUP, 'cadex-env', str(run.path / 'setup'),
                                   str(cwd or project['cadence'])] + [str(x) for x in argv],
                                  stdout=out, stderr=err, env=environment, start_new_session=True)
            code = proc.wait(timeout=timeout)
            banner = (run.path / 'stdout.log').read_text(errors='replace')[:2400]
            run.data['tool_reported_banner'] = [line for line in banner.splitlines() if line.strip()][:12]
            return code
        except subprocess.TimeoutExpired:
            # Only the process group created for this invocation is signaled.
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            return 124



def bounded_summary(run):
    return dict(run=str(run.path), stage=run.data['stage'], state=run.data['state'],
                native_exit=run.data.get('native_exit'), evidence=run.data.get('evidence'),
                error=run.data.get('error'), engineering_acceptance=run.data['engineering_acceptance'])


def guarded(project, stage, label, inputs, operation, conditions=None):
    with serialized(project):
        run = Run(project, stage, label, inputs, conditions)
        try:
            operation(run)
        except (Error, OSError, ValueError, KeyError) as exc:
            run.fail(exc, run.data.get('native_exit'))
        return bounded_summary(run)


def skill_job(run, project, text, timeout=180):
    check(text)
    job = run.path / 'inputs/job.il'
    job.write_text(text)
    run.artifact('submitted_job', job)
    launcher = Path.home() / '.codex/scripts/virtuoso-batch.sh'
    code = execute(run, project, ['bash', launcher, job], timeout=timeout+30,
                   env={'CODEX_VIRTUOSO_RUN_ROOT': str(run.path / 'native'), 'VIRTUOSO_TIMEOUT_SECONDS': str(timeout)})
    run.data['native_exit'] = code
    output = (run.path / 'stdout.log').read_text(errors='replace')
    matches = re.findall(r'^RUN=(.+)$', output, re.M)
    if len(matches) != 1 or not inside(run.path / 'native', Path(matches[0])):
        raise Error('Missing/invalid owned batch output directory; inspect logs')
    batch = Path(matches[0])
    if code != 0 or not (batch / 'completion.ok').is_file():
        raise Error('Batch job failed/incomplete; inspect its CDS.log before any retry: ' + str(batch))
    return batch


def run_skill(project, path, label):
    path = Path(path).expanduser().resolve()
    text = path.read_text()
    check(text)  # Before allocating a run or loading site setup.
    def operation(run):
        batch = skill_job(run, project, text)
        run.artifact('batch_completion', batch / 'completion.ok')
        # Library creation legitimately changes this owned mapping; retain both identities.
        mapping = str((project['cadence'] / 'cds.lib').resolve())
        run.data['post_inputs'] = [identity(item['path']) if item['path'] == mapping else item for item in run.data['inputs']]
        run.data['intentional_mutation'] = 'batch job may update project library mappings; before/after identities retained'
        run.finish(0, {'batch': str(batch), 'completion_marker': True, 'scope': 'job completion only'})
    return guarded(project, 'skill', label, [path], operation)


def netlist(project, lib, cell, label, corner='NN'):
    pr = profile(project)
    source = view_file(project, lib, cell, 'schematic')
    if not re.fullmatch('[A-Za-z0-9_]+', corner):
        raise Error('Invalid model section')
    models = Path(pr['pdk']) / 'models/spectre/gpdk.scs'
    def operation(run):
        ade = run.path / 'native/ade'
        text = '''envSetVal("asimenv.startup" "projectDir" 'string ADE)
simulator('spectre)
unless(ddGetObj(LIB CELL "schematic") error("Existing schematic is missing"))
design(LIB CELL "schematic")
resultsDir(RESULTS)
modelFile(list(MODELS CORNER))
let((path out cv)
 path=createNetlist(?recreateAll t ?display nil)
 unless(path error("Native netlisting failed"))
 out=outfile(strcat(getShellEnvVar("CODEX_VIRTUOSO_RUN") "/netlist_path.txt"))
 fprintf(out "%L\\n" path)
 close(out)
 cv=dbOpenCellViewByType(LIB CELL "schematic" "" "r")
 out=outfile(strcat(getShellEnvVar("CODEX_VIRTUOSO_RUN") "/ports.txt"))
 foreach(term cv~>terminals fprintf(out "%L\\n" term~>name))
 close(out)
)
'''
        values = dict(ADE=str(ade), LIB=lib, CELL=cell, RESULTS=str(run.path/'native/psf'), MODELS=str(models), CORNER=corner)
        text = re.sub(r'\b(?:'+'|'.join(values)+r')\b', lambda m: json.dumps(values[m.group()]), text)
        batch = skill_job(run, project, text)
        path = Path(json.loads((batch / 'netlist_path.txt').read_text().strip())).resolve()
        if not inside(ade, path) or not path.is_file():
            raise Error('OCEAN output escaped its configured projectDir; no outside output was moved/deleted')
        ports = [json.loads(x) for x in (batch / 'ports.txt').read_text().splitlines()]
        if not ports or any(not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', p) for p in ports):
            raise Error('Unsupported or missing native port names')
        run.data.update(target={'library': lib, 'cell': cell, 'view': 'schematic'}, ports=ports, profile=pr)
        run.artifact('netlist', path)
        run.artifact('ports', batch / 'ports.txt')
        run.finish(0, {'native_netlist': str(path), 'ports': ports, 'corner': corner, 'contained': True})
    return guarded(project, 'netlist', label, [source, models], operation, {'corner': corner})


def spectre(project, input_file, label, sources=(), conditions=None):
    path = Path(input_file).expanduser().resolve()
    def operation(run):
        shutil.copyfile(str(path), str(run.path / 'inputs' / path.name))
        run.artifact('submitted_deck', run.path / 'inputs' / path.name)
        code = execute(run, project, ['spectre', path, '-raw', run.path/'native/psf', '-format', 'psfascii',
                                     '+log', run.path/'native/spectre.log'])
        run.data['native_exit'] = code
        log = run.path / 'native/spectre.log'
        text = log.read_text(errors='replace') if log.exists() else ''
        summary = re.findall(r'spectre completes with (\d+) errors?, (\d+) warnings?', text)
        if code or not summary or int(summary[-1][0]) != 0:
            suffix = ' SPECTRE-209 in an ordinary sandbox can require per-command reviewed execution; it does not establish license exhaustion.' if 'SPECTRE-209' in text else ''
            raise Error('Spectre did not complete successfully; see native log.' + suffix)
        run.artifact('simulator_log', log)
        for data in (run.path/'native/psf').rglob('*'):
            if data.is_file():
                run.artifact('psf/'+str(data.relative_to(run.path/'native/psf')), data)
        run.finish(0, {'errors': int(summary[-1][0]), 'warnings': int(summary[-1][1]),
                       'psf': str(run.path/'native/psf'), 'scope': 'simulation completion; verify analyses and task metrics separately'})
    return guarded(project, 'simulation', label, [path] + list(sources), operation, conditions)


def physical(project, lib, cell, label, stage, netlist_run=None):
    pr = profile(project)
    source = view_file(project, lib, cell, 'layout')
    pdk = Path(pr['pdk'])
    inputs = [source, pdk/'pv/assura'/('drc.rul' if stage == 'drc' else 'extract.rul')]
    if stage == 'lvs':
        np, nm = load_run(netlist_run, 'netlist')
        if nm['target'] != {'library': lib, 'cell': cell, 'view': 'schematic'}:
            raise Error('Netlist target differs from requested LVS target')
        native = np / nm['artifacts']['netlist']['path']
        cdl, count = schematic_cdl(native.read_text(), cell, nm['ports'], {v:k for k,v in pr['model_mapping'].items()})
        inputs += [native, np/'manifest.json', pdk/'pv/assura/compare.rul'] + [Path(i['path']) for i in nm['inputs']]
    def operation(run):
        common = ('avParameters(\n ?inputLayout ("df2" LIB)\n ?cellName CELL\n ?viewName "layout"\n'
                  ' ?rulesFile RULES\n ?runName CELL\n ?workingDirectory WORK\n ?avrpt t\n')
        if stage == 'drc':
            common += ' ?flagNon45 t\n ?flagOffGrid .005\n ?userUnits "micron"\n ?joinPins top\n ?modifyHierarchy nil\n)\n'
        else:
            file = run.path/'inputs/schematic.cdl';file.write_text(cdl);run.artifact('source_cdl', file)
            common += ' ?technology "gpdk180"\n ?techLib TECH\n)\nload(COMPARE)\navCompareRules(schematic(netlist(cdl CDL)))\navLVS()\n'
        values = dict(LIB=lib, CELL=cell, RULES=str(pdk/'pv/assura'/('drc.rul' if stage=='drc' else 'extract.rul')),
                      WORK=str(run.path/'native'), TECH=str(pdk/'assura_tech.lib'), COMPARE=str(pdk/'pv/assura/compare.rul'),
                      CDL=str(run.path/'inputs/schematic.cdl'))
        text = re.sub(r'\b(?:'+'|'.join(values)+r')\b', lambda m: json.dumps(values[m.group()]), common)
        rsf = run.path/'inputs/run.rsf';rsf.write_text(text);run.artifact('rules_setup', rsf)
        code = execute(run, project, [pr['assura'], rsf])
        run.data['native_exit'] = code
        log = (run.path/'stdout.log').read_text(errors='replace')
        if code or 'Assura terminated normally' not in log:
            raise Error('Assura did not terminate normally; inspect native logs, not license-query guesses')
        if stage == 'drc':
            totals = re.findall(r'Total\s+errors:\s+(\d+)\s+(\d+)', log)
            if not totals or any(int(x) for x in totals[-1]):
                raise Error('DRC has violations or no authoritative error total')
            evidence = {'errors': [int(x) for x in totals[-1]], 'deck': str(pdk/'pv/assura/drc.rul'), 'scope': 'default deck; density/antenna not included'}
            run.artifact('report', run.path/'stdout.log')
        else:
            report = run.path/'native'/(cell+'.csm')
            text = report.read_text() if report.exists() else ''
            if not re.search(r'^Schematic and Layout Match\s*$', text, re.M) or re.search('pin errs|Mismatch', text, re.I):
                raise Error('LVS mismatch or pin errors; process exit 0 is not a match')
            evidence = {'matched': True, 'ports': nm['ports'], 'source_mos_count': count}
            run.artifact('report', report)
        run.data.update(target={'library':lib, 'cell':cell, 'view':'layout'}, profile=pr)
        # Native files are the exact immutable dependency for a later extraction working copy.
        for f in (run.path/'native').rglob('*'):
            if f.is_file():
                run.artifact('native/'+str(f.relative_to(run.path/'native')), f)
        run.finish(0, evidence)
    return guarded(project, stage, label, inputs, operation)


def pex(project, lvs_run, label, ground=None):
    ground = ground or project['config'].get('ground_net')
    if not ground:
        raise Error('Specify the actual extraction reference net with --ground or project ground_net')
    source, lvs = load_run(lvs_run, 'lvs')
    pr = profile(project)
    if lvs.get('profile') != pr or lvs.get('project') != str(project['root']):
        raise Error('LVS project/profile differs; extraction was not started')
    cell, lib = lvs['target']['cell'], lvs['target']['library']
    tech = Path(pr['pdk'])/'pv/assura/rcx'
    inputs = [source/'manifest.json', tech/'qrcTechFile'] + [Path(i['path']) for i in lvs['inputs']]
    for value in lvs['artifacts'].values():inputs.append(source/value['path'])
    def operation(run):
        shutil.copytree(str(source/'native'), str(run.path/'native/lvs'))
        native = run.path/'native/lvs'
        commands = [
            'process_technology -technology_directory TECH -temperature 27',
            'input_db -type assura -directory_name NATIVE -run_name CELL -format DFII -design_cell_name CELL layout LIB -library_definitions_file LIBFILE',
            'output_setup -directory_name NATIVE -temporary_directory_name qrc_tmp -file_name PEXNAME -net_name_space schematic',
            'extraction_setup -net_name_space layout -max_fracture_length infinite -max_fracture_length_unit microns',
            'output_db -type spice -include_cap_model false -include_res_model false -include_parasitic_cap_model false -include_parasitic_res_model false',
            'extract -selection all -type rc_coupled', 'capacitance -ground_net GROUND', 'filter_res -min_res 0.001',
            'log_file -file_name LOGFILE -dump_options true']
        # Quantus Tcl-style options are not shell arguments; reject paths requiring unverified quoting.
        values = dict(TECH=str(tech), NATIVE=str(native), CELL=cell, LIB=lib, LIBFILE=str(project['cadence']/'cds.lib'),
                      PEXNAME=cell+'_pex.sp', GROUND=ground, LOGFILE=str(run.path/'native/qrc.log'))
        if any(not re.fullmatch(r'[A-Za-z0-9_./:-]+', v) for v in values.values()):
            raise Error('Quantus recipe does not support whitespace/special-character paths; use a verified project-specific flow')
        command = re.sub(r'\b(?:'+'|'.join(values)+r')\b', lambda m: values[m.group()], '\n'.join(commands)+'\n')
        file = run.path/'inputs/qrc.cmd';file.write_text(command);run.artifact('commands', file)
        code = execute(run, project, [pr['quantus'], '-cmd', file], cwd=native)
        run.data['native_exit'] = code
        log = run.path/'native/qrc.log'
        text = log.read_text(errors='replace') if log.exists() else ''
        if code or 'Quantus terminated normally' not in text:
            raise Error('Quantus extraction incomplete; inspect qrc.log and retained failed run')
        raw = native/(cell+'_pex.sp')
        translated, conversion = pex_to_spectre(raw.read_text(), pr['model_mapping'])
        output = run.path/'native/dut.scs';output.write_text(translated)
        proof = run.path/'native/conversion.json';proof.write_text(json.dumps(conversion, indent=2)+'\n')
        for name, f in [('raw_pex',raw),('spectre',output),('conversion',proof),('extractor_log',log)]:run.artifact(name,f)
        run.data.update(target=lvs['target'], profile=pr)
        run.finish(0, dict(conversion['counts'], ports=conversion['ports'],
                           floating_nets=[int(n) for n in re.findall(r'Total floating nets\s*=\s*(\d+)',text)],
                           warnings=[x for x in text.splitlines() if 'WARNING (' in x][:20],
                           scope='native coupled RC; inspect warnings and verify electrical performance separately'))
    return guarded(project, 'pex', label, inputs, operation)
