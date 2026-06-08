from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.errors import ErrorReporter
from hellen.core.ast import ProgramNode, VarDeclNode, LiteralNode, BinaryOpNode

def _parse(s):
    sc = Scanner(s, file='<t>')
    tok = sc.scan_all()
    er = ErrorReporter()
    pa = Parser(tok, er)
    return pa.parse(), er

# Empty
p, e = _parse('')
assert isinstance(p, ProgramNode) and p.statements == []
print('PASS: empty')

# Let
p, e = _parse('let x = 42;')
assert not e.has_errors and p.statements[0].name == 'x' and p.statements[0].mutable
print('PASS: let')

# Const
p, e = _parse('const M = 100;')
assert not e.has_errors and not p.statements[0].mutable
print('PASS: const')

# Precedence
p, e = _parse('let x = 1 + 2 * 3;')
assert not e.has_errors
d = p.statements[0].initializer
assert d.operator.lexeme == '+' and d.right.operator.lexeme == '*'
print('PASS: precedence')

# Grouping
p, e = _parse('let x = (1+2)*3;')
assert not e.has_errors
from hellen.core.ast import GroupingNode
assert isinstance(p.statements[0].initializer.left, GroupingNode)
print('PASS: grouping')

# Unary
p, e = _parse('let x = !true;')
assert not e.has_errors
from hellen.core.ast import UnaryOpNode
assert isinstance(p.statements[0].initializer, UnaryOpNode)
print('PASS: unary')

# Comparison chain
p, e = _parse('let x = a < b && b > c;')
assert not e.has_errors
e2 = p.statements[0].initializer
assert e2.operator.lexeme == '&&'
print('PASS: comparison_chain')

# Function call
p, e = _parse('print("hi");')
assert not e.has_errors
from hellen.core.ast import CallNode, VariableNode
c = p.statements[0]
assert isinstance(c, CallNode) and c.callee.name == 'print'
print('PASS: call')

print('\nALL 8 PASSED')
