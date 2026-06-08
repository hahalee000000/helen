from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.errors import ErrorReporter
from hellen.core.ast import ProgramNode, AgentDeclNode

def _parse(s):
    sc = Scanner(s, file='<t>')
    tok = sc.scan_all()
    er = ErrorReporter()
    pa = Parser(tok, er)
    return pa.parse(), er

p, e = _parse('agent Test { prompt "hello"; }')
assert not e.has_errors
print('agent:', p.statements[0].name)
print('OK')
