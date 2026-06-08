from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.errors import ErrorReporter
from hellen.core.ast import *

def _parse(source):
    scanner = Scanner(source, file='<test>')
    tokens = scanner.scan_all()
    errors = ErrorReporter()
    parser = Parser(tokens, errors)
    return parser.parse(), errors

# agent
p, e = _parse('agent Test { prompt "hello"; }')
assert not e.has_errors
a = p.statements[0]
assert isinstance(a, AgentDeclNode) and a.name == 'Test'
assert isinstance(a.prompt, PromptDefNode) and a.prompt.content == 'hello'
print('PASS: agent')

# agent with main
p, e = _parse('agent A { prompt "p"; main { let x = 1; } }')
assert not e.has_errors
print('PASS: agent+main')

# precedence
p, e = _parse('let x = 1 + 2 * 3;')
assert not e.has_errors
d = p.statements[0]
assert d.initializer.operator.lexeme == '+'
assert d.initializer.right.operator.lexeme == '*'
print('PASS: precedence')

# if/else
p, e = _parse('if true { } else { }')
assert not e.has_errors
assert isinstance(p.statements[0], IfStmtNode)
print('PASS: if/else')

# for
p, e = _parse('for x in items { }')
assert not e.has_errors
assert isinstance(p.statements[0], ForStmtNode)
print('PASS: for')

# while
p, e = _parse('while true { }')
assert not e.has_errors
print('PASS: while')

# break/continue
p, e = _parse('break;')
assert not e.has_errors
assert isinstance(p.statements[0], BreakStmtNode)
p, e = _parse('continue;')
assert isinstance(p.statements[0], ContinueStmtNode)
print('PASS: break/continue')

# return
p, e = _parse('return 42;')
assert not e.has_errors
assert isinstance(p.statements[0], ReturnStmtNode)
print('PASS: return')

# fn
p, e = _parse('fn add(a, b) -> int { }')
assert not e.has_errors
f = p.statements[0]
assert f.name == 'add' and len(f.parameters) == 2
assert f.return_type.name == 'int'
print('PASS: fn')

# import
p, e = _parse('import "utils" as u;')
assert not e.has_errors
assert p.statements[0].module_path == 'utils'
print('PASS: import')

# grouping
p, e = _parse('let x = (1 + 2) * 3;')
assert not e.has_errors
assert isinstance(p.statements[0].initializer.left, GroupingNode)
print('PASS: grouping')

# unary
p, e = _parse('let x = !true;')
assert not e.has_errors
assert isinstance(p.statements[0].initializer, UnaryOpNode)
print('PASS: unary')

# call
p, e = _parse('print("hi");')
assert not e.has_errors
assert isinstance(p.statements[0], CallNode)
print('PASS: call')

# error recovery
p, e = _parse('agent B { prompt "hi" let x =')
assert e.has_errors
print('PASS: error_recovery')

# unexpected
p, e = _parse('!!!;')
assert e.has_errors
print('PASS: unexpected')

# const
p, e = _parse('const MAX = 100;')
assert not e.has_errors
assert p.statements[0].mutable is False
print('PASS: const')

print('\nALL 18 TESTS PASSED')
