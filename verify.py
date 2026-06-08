from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.errors import ErrorReporter
from hellen.core.ast import *

def _parse(s):
    sc = Scanner(s, file='<t>')
    tok = sc.scan_all()
    er = ErrorReporter()
    pa = Parser(tok, er)
    return pa.parse(), er

p, e = _parse('')
assert isinstance(p, ProgramNode) and p.statements == []
print('PASS: empty')

p, e = _parse('let x = 42;')
assert not e.has_errors and p.statements[0].name == 'x' and p.statements[0].mutable
print('PASS: let')

p, e = _parse('const M = 100;')
assert not e.has_errors and not p.statements[0].mutable
print('PASS: const')

p, e = _parse('agent T { prompt "hi"; }')
assert not e.has_errors
a = p.statements[0]
assert isinstance(a, AgentDeclNode) and a.name == 'T'
assert isinstance(a.prompt, PromptDefNode) and a.prompt.content == 'hi'
print('PASS: agent')

p, e = _parse('agent A { prompt "p"; main { let x = 1; } }')
assert not e.has_errors
print('PASS: agent+main')

p, e = _parse('let x = 1 + 2 * 3;')
assert not e.has_errors
d = p.statements[0].initializer
assert d.operator.lexeme == '+' and d.right.operator.lexeme == '*'
print('PASS: precedence')

p, e = _parse('if true { } else { }')
assert not e.has_errors and isinstance(p.statements[0], IfStmtNode)
print('PASS: if/else')

p, e = _parse('for x in items { }')
assert not e.has_errors and p.statements[0].variable == 'x'
print('PASS: for')

p, e = _parse('while true { }')
assert not e.has_errors and isinstance(p.statements[0], WhileStmtNode)
print('PASS: while')

p, e = _parse('break;')
assert not e.has_errors and isinstance(p.statements[0], BreakStmtNode)
print('PASS: break')

p, e = _parse('continue;')
assert not e.has_errors and isinstance(p.statements[0], ContinueStmtNode)
print('PASS: continue')

p, e = _parse('return 42;')
assert not e.has_errors and p.statements[0].value.value == 42
print('PASS: return')

p, e = _parse('fn add(a, b) -> int { }')
assert not e.has_errors
f = p.statements[0]
assert f.name == 'add' and len(f.parameters) == 2 and f.return_type.name == 'int'
print('PASS: fn')

p, e = _parse('import "u" as x;')
assert not e.has_errors and p.statements[0].module_path == 'u'
print('PASS: import')

p, e = _parse('let x = (1+2)*3;')
assert not e.has_errors and isinstance(p.statements[0].initializer.left, GroupingNode)
print('PASS: grouping')

p, e = _parse('let x = !true;')
assert not e.has_errors and isinstance(p.statements[0].initializer, UnaryOpNode)
print('PASS: unary')

p, e = _parse('print("hi");')
assert not e.has_errors and isinstance(p.statements[0], CallNode)
print('PASS: call')

p, e = _parse('let x = a < b && b > c;')
assert not e.has_errors
e = p.statements[0].initializer
assert e.operator.lexeme == '&&'
print('PASS: comparison_chain')

p, e = _parse('agent B { prompt "hi" let x =')
assert e.has_errors
print('PASS: error_recovery')

p, e = _parse('!!!;')
assert e.has_errors
print('PASS: unexpected')

print('\nALL 20 TESTS PASSED')
