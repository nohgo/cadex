"""Strict adapters for the demonstrated gpdk180 flat-MOS flow and PSF ASCII."""
import json
import math
from pathlib import Path
import re

from project import Error


def flat_lines(text):
    text = re.sub(r'\\\r?\n\s*', ' ', text)
    return re.sub(r'\n\+\s*', ' ', text).splitlines()


def pex_to_spectre(text, mapping):
    lines = ['// Audited syntax translation of native extracted MOS/R/C cards.', 'simulator lang=spectre']
    counts = dict(M=0, R=0, C=0)
    omitted, nodes, ports, names = [], {}, [], set()
    started = ended = False

    def node(value):
        if not re.fullmatch(r'[A-Za-z0-9_#]+', value):
            raise Error('Unsupported PEX node syntax; use a project-specific adapter: ' + value)
        translated = value.replace('#', '_p')
        if translated in nodes.values() and nodes.get(value) != translated:
            raise Error('PEX node escaping would merge distinct nodes')
        nodes[value] = translated
        return translated

    for line in flat_lines(text):
        words = line.split()
        if not words or words[0].startswith('*'):
            continue
        tag = words[0].upper()
        if tag == '.SUBCKT':
            if started or len(words) < 3:
                raise Error('Only one flat extracted subcircuit is supported')
            started = True
            ports = words[2:]
            # Preserve declared interface order and names exactly.
            if any(node(p) != p for p in ports):
                raise Error('Escaped external PEX ports require an explicit interface adapter')
            lines.append('subckt ' + ' '.join(words[1:]))
            cell = words[1]
            continue
        if tag == '.ENDS':
            if not started or ended or len(words) != 2 or words[1] != cell:
                raise Error('Invalid extracted subcircuit terminator')
            ended = True
            lines.append('ends ' + cell)
            continue
        if not started or ended or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', words[0]):
            raise Error('Unsupported extracted statement: ' + line[:160])
        if words[0] in names:
            raise Error('Duplicate extracted instance name')
        names.add(words[0])
        kind = tag[0]
        if kind == 'M':
            if len(words) < 8 or words[5] not in mapping:
                raise Error('Unsupported extracted MOS model or card')
            params = {}
            for word in words[6:]:
                if word.count('=') != 1:
                    raise Error('Unsupported MOS parameter expression')
                k, v = word.split('=')
                k = k.lower()
                if k in params or not math.isfinite(float(v)):
                    raise Error('Invalid or duplicate MOS parameter')
                params[k] = v
            if not {'l', 'w'}.issubset(params):
                raise Error('Extracted MOS is missing W/L')
            kept = []
            for key, value in params.items():
                if key in ['fw', 'simw']:
                    if float(value) != float(params['w']):
                        raise Error('Non-redundant finger/width metadata requires a project-specific model adapter')
                    omitted.append(dict(instance=words[0], property=key, value=value))
                else:
                    kept.append(key + '=' + value)
            lines.append('{} ({}) {} {}'.format(words[0], ' '.join(node(n) for n in words[1:5]), mapping[words[5]], ' '.join(kept)))
        elif kind in ['R', 'C']:
            if len(words) != 4 or not math.isfinite(float(words[3])) or float(words[3]) < 0:
                raise Error('Unsupported extracted R/C card or value')
            lines.append('{} ({}) {} {}={}'.format(words[0], ' '.join(node(n) for n in words[1:3]),
                         'resistor' if kind == 'R' else 'capacitor', kind.lower(), words[3]))
        else:
            raise Error('Unsupported extracted device; no cards were silently dropped: ' + words[0])
        counts[kind] += 1
    if not ended or not counts['M']:
        raise Error('No complete MOS/R/C extracted subcircuit')
    return '\n'.join(lines) + '\n', dict(counts=counts, ports=ports, model_mapping=mapping,
        node_mapping=nodes, omitted_redundant_metadata=omitted)


def schematic_cdl(text, cell, ports, mapping):
    """Convert only known flat native MOS cards; reject unknown circuit statements."""
    if not ports or len(set(ports)) != len(ports):
        raise Error('Saved schematic port metadata is missing or ambiguous')
    output = ['* Flat MOS CDL derived from the native saved-schematic Spectre netlist.',
              '.SUBCKT ' + cell + ' ' + ' '.join(ports)]
    count = 0
    started = False
    for line in flat_lines(text):
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('simulator ') or line.startswith('global ') or line.startswith('include '):
            continue
        if line.startswith('simulatorOptions'):
            break
        m = re.fullmatch(r'(M[A-Za-z0-9_]*)\s+\(([^)]+)\)\s+(\w+)\s+(.+)', line)
        if not m:
            raise Error('This CDL adapter supports only flat native MOS cards; use a verified native CDL flow for this design: ' + line[:120])
        name, terminals, model, params = m.groups()
        if len(terminals.split()) != 4 or model not in mapping:
            raise Error('Unsupported schematic model/terminal count')
        if not re.fullmatch(r'[A-Za-z0-9_\s.=+*()eE-]+', params):
            raise Error('Unsupported schematic parameter expression')
        params = re.sub(r'\(([^()]+)\)', r'\1', params)
        def multiplier(match):
            value = 1.0
            for part in match.group(1).split('*'):
                value *= float(part)
            if not math.isfinite(value) or value <= 0:
                raise Error('Invalid MOS multiplicity')
            return 'm=' + format(value, '.15g')
        params = re.sub(r'(?i)\bm=([0-9.eE+*-]+)', multiplier, params)
        params = ' '.join(params.split())
        output.append('{} {} {} {}'.format(name, terminals, mapping[model], params))
        count += 1
        started = True
    if not started:
        raise Error('Native schematic netlist has no supported MOS cards')
    output.append('.ENDS ' + cell)
    return '\n'.join(output) + '\n', count


def read_psf(path, axis=None):
    """Read VALUE records, including quoted OP units and complex AC samples."""
    path = Path(path)
    if path.stat().st_size > 128 * 1024 * 1024:
        raise Error('PSF ASCII reader limit is 128 MiB; export selected signals with OCEAN')
    text = path.read_text()
    if '\nVALUE\n' not in text:
        raise Error('Not supported PSF ASCII; export ASCII/selected signals through the project flow')
    rows, record = [], {}
    for line in text.split('\nVALUE\n', 1)[1].splitlines():
        m = re.match(r'^"((?:\\.|[^"\\])*)"\s+(.*)', line)
        if not m:
            continue
        key, value = m.groups()
        key = json.loads('"' + key + '"')
        if axis and key == axis and record:
            rows.append(record)
            record = {}
        # OP and margin records can carry a quoted unit before the value.
        if value.startswith('"'):
            unit = re.match(r'^"(?:\\.|[^"\\])*"\s+(.*)', value)
            if unit:
                value = unit.group(1)
        try:
            if value.startswith('('):
                pair = value.split(')', 1)[0][1:].split()
                if len(pair) != 2:
                    raise Error('Invalid complex PSF sample')
                parsed = complex(float(pair[0]), float(pair[1]))
            elif value.startswith('"'):
                parsed = json.JSONDecoder().raw_decode(value)[0]
            else:
                parsed = float(value.split()[0])
        except (ValueError, IndexError):
            raise Error('Unrecognized PSF value for ' + key)
        record[key] = parsed
    if record:
        rows.append(record)
    if not rows or (axis and any(axis not in r for r in rows)):
        raise Error('Missing PSF records/axis')
    return rows
