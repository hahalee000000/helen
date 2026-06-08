from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.errors import ErrorReporter
from hellen.core.ast import ProgramNode

def _parse(source):
    scanner = Scanner(source, file='<test>')
    tokens = scanner.scan_all()
    errors = ErrorReporter()
    parser = Parser(tokens, errors)
    return parser.parse(), errors

p, e = _parse('')
assert isinstance(p, ProgramNode) and p.statements == []
print('PASS: empty')

p, e = _parse('let x = 42;')
assert not e.has_errors
print('PASS: let')

p, e = _parse('break;')
assert not e.has_errors
print('PASS: break')

print('ALL OK')
