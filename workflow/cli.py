#!/usr/bin/env python3
"""Installed entrypoint. Tool execution remains subject to per-command review."""
import argparse
import csv
import json
import math
import re
from pathlib import Path
import subprocess
import sys

from project import Error, discover, initialize, show
from runs import status
import native
from formats import read_psf
from skill import check


def condition(values):
    result = {}
    for text in values:
        if '=' not in text:
            raise Error('Conditions use NAME=VALUE, including units in names where relevant')
        key, value = text.split('=', 1)
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_]*', key) or key in result:
            raise Error('Empty/duplicate condition name')
        try:
            value = json.loads(value)
        except ValueError:
            pass
        try:
            json.dumps(value, allow_nan=False)
        except ValueError:
            raise Error('Declared conditions must be finite JSON values')
        result[key] = value
    return result


def clean(value):
    if isinstance(value, complex):
        return {'real': clean(value.real), 'imag': clean(value.imag)}
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(x) for x in value]
    return value


def psf_summary(args):
    rows = read_psf(args.file, args.axis)
    signals = args.signals or sorted(rows[0])
    if any(s not in row for row in rows for s in signals):
        raise Error('Requested PSF signals are missing from one or more records')
    nonfinite = sorted({s for row in rows for s in signals if isinstance(row[s], (float, complex))
                       and not (math.isfinite(row[s].real) and math.isfinite(row[s].imag))})
    if args.csv:
        with Path(args.csv).open('x', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(signals)
            writer.writerows([[row[s] for s in signals] for row in rows])
    return {'records': len(rows), 'signals': signals, 'nonfinite_signals': nonfinite,
            'first': {s: rows[0][s] for s in signals}, 'last': {s: rows[-1][s] for s in signals},
            'csv': args.csv, 'scope': 'data inspection/export; no engineering pass inferred'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Cadex projects and reviewed native EDA recipes')
    parser.add_argument('--project', help='Project root or configured Cadence launch directory; otherwise discover from cwd')
    parser.add_argument('--profile', dest='profile_override', choices=['uf-gpdk180'], help='Invocation-only profile override, useful for unconfigured small experiments')
    sub = parser.add_subparsers(dest='command')
    p = sub.add_parser('project', help='Discover or initialize a full/small project without changing existing setup')
    actions = p.add_subparsers(dest='action')
    actions.add_parser('show')
    init = actions.add_parser('init')
    init.add_argument('path')
    init.add_argument('--mode', choices=['full', 'small'], default='full')
    init.add_argument('--profile', choices=['uf-gpdk180'])
    sub.add_parser('status', help='Summarize labeled runs and detect changed source inputs')
    doctor = sub.add_parser('doctor', help='Inspect known tool paths; optional read-only license query, no checkout')
    doctor.add_argument('--licenses', action='store_true')
    preflight = sub.add_parser('skill-check', help='Lexical balance/lifecycle check; not a SKILL compiler')
    preflight.add_argument('file')
    psf = sub.add_parser('psf', help='Inspect/export PSF ASCII real, complex, unit-bearing OP and margin data')
    psf.add_argument('file')
    psf.add_argument('--axis')
    psf.add_argument('--signals', nargs='+')
    psf.add_argument('--csv', help='Create-only CSV export path')
    job = sub.add_parser('skill', help='Preflight and execute a batch job; driver owns lifecycle')
    job.add_argument('file')
    sim = sub.add_parser('spectre', help='Run a deck with isolated site setup; native completion is not design acceptance')
    sim.add_argument('file')
    sim.add_argument('--source', action='append', default=[], help='Additional source/model/DUT file to fingerprint')
    sim.add_argument('--condition', action='append', default=[], help='Declared condition, e.g. corner=NN or temp_C=27')
    net = sub.add_parser('netlist', help='Generate a fresh saved-schematic netlist with contained OCEAN projectDir')
    net.add_argument('library')
    net.add_argument('cell')
    net.add_argument('--corner', default='NN')
    for name in ['drc', 'lvs']:
        tool = sub.add_parser(name, help='Verified uf-gpdk180 Assura recipe and native-result validation')
        tool.add_argument('library')
        tool.add_argument('cell')
        if name == 'lvs':
            tool.add_argument('--netlist-run', required=True)
    ext = sub.add_parser('pex', help='Quantus extraction from a fresh matched LVS working copy')
    ext.add_argument('--lvs-run', required=True)
    ext.add_argument('--ground', help='Actual extraction reference net; otherwise use explicit project ground_net')
    for p in [job, sim, net, sub.choices['drc'], sub.choices['lvs'], ext]:
        p.add_argument('--label', required=True, help='Meaningful design/purpose label; each attempt gets a unique run')
    args = parser.parse_args(argv)
    if not args.command or (args.command == 'project' and not args.action):
        (sub.choices['project'] if args.command == 'project' else parser).print_help()
        return 0
    try:
        if args.command == 'project' and args.action == 'init':
            value = initialize(args.path, args.mode, args.profile)
        elif args.command == 'skill-check':
            value = check(Path(args.file).read_text())
        elif args.command == 'psf':
            value = psf_summary(args)
        else:
            project = discover(args.project)
            if args.profile_override:
                project['config'] = dict(project['config'], profile=args.profile_override)
            if args.command == 'project' and args.action == 'show':
                value = show(project)
            elif args.command == 'status':
                value = {'runs': status(project)}
            elif args.command == 'doctor':
                pr = native.profile(project)
                value = {'profile': pr, 'paths': {key: {'path': pr[key], 'exists': Path(pr[key]).exists()}
                         for key in ['assura', 'quantus', 'lmutil']},
                         'spectre': 'resolved after isolated /apps/settings setup',
                         'license_query_is_not_tool_availability': True}
                if args.licenses:
                    proc = subprocess.run([pr['lmutil'], 'lmstat', '-c', '5280@ece-itop-licsvr.ece.ufl.edu', '-f', '111'],
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=20)
                    value['license_query'] = {'status': proc.returncode,
                        'feature_lines': [s for s in proc.stdout.splitlines() if s.startswith('Users of ')],
                        'scope': 'read-only query; no license checkout, reservation or guarantee'}
            elif args.command == 'skill':
                value = native.run_skill(project, args.file, args.label)
            elif args.command == 'spectre':
                value = native.spectre(project, args.file, args.label, args.source, condition(args.condition))
            elif args.command == 'netlist':
                value = native.netlist(project, args.library, args.cell, args.label, args.corner)
            elif args.command in ['drc', 'lvs']:
                value = native.physical(project, args.library, args.cell, args.label, args.command, getattr(args, 'netlist_run', None))
            elif args.command == 'pex':
                value = native.pex(project, args.lvs_run, args.label, args.ground)
            else:
                parser.print_help()
                return 64
        print(json.dumps(clean(value), indent=2, allow_nan=False))
        if not isinstance(value, dict) or value.get('state', 'complete') == 'complete':
            return 0
        code = value.get('native_exit')
        return code if isinstance(code, int) and 0 < code < 256 else 65
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'error': str(exc), 'automatic_retry': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
