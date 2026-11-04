"""Conservative lexical preflight, not a licensed SKILL compiler."""
import re
from project import Error


def check(text):
    depth = 0
    in_string = escaped = comment = False
    clean = []
    index = 0
    while index < len(text):
        c = text[index]
        if not in_string and not comment and text[index:index+2] == '/*':
            end = text.find('*/', index+2)
            if end < 0:
                raise Error('SKILL preflight: unterminated block comment')
            clean.append(' ')
            index = end+2
            continue
        index += 1
        if comment:
            if c == '\n':
                comment = False
                clean.append(' ')
            continue
        if in_string:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                in_string = False
                clean.append(' ')
            continue
        if c == ';':
            comment = True
        elif c == '"':
            in_string = True
        else:
            clean.append(c)
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth < 0:
                    raise Error('SKILL preflight: unexpected closing parenthesis')
    if depth or in_string:
        raise Error('SKILL preflight: unbalanced parentheses or unterminated string')
    if re.search(r'\b(?:exit|quit)\s*\(|\(\s*(?:exit|quit)(?:\s|\))', ''.join(clean)):
        raise Error('Batch job must return normally; the managed driver owns exit()')
    return {'balanced': True, 'lifecycle': 'returns to driver', 'licensed_compilation': False}
