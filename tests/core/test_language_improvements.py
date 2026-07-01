"""Tests for Helen language improvements.

This module tests:
1. skills is no longer a reserved word
2. Agent functions block can have variable definitions (let/const)
3. List objects have common methods (append, pop, insert, etc.)
4. Match statement supports range patterns and guard conditions
"""
import pytest
from typing import Tuple, List

from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter


def run_helen(source: str) -> Tuple[List[str], List[str]]:
    """Run Helen source code and return (stdout_lines, errors)."""
    import io
    import sys
    
    errors = ErrorReporter()
    scanner = Scanner(source=source, file='<test>')
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors)
    program = parser.parse()
    
    if errors.has_errors:
        return [], [str(e) for e in errors._errors]
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        interp = Interpreter(errors=errors)
        interp.interpret(program)
        output = sys.stdout.getvalue().strip().split('\n') if sys.stdout.getvalue().strip() else []
    finally:
        sys.stdout = old_stdout
    
    return output, []


class TestSkillsNotReserved:
    """Test that 'skills' is no longer a reserved word."""
    
    def test_skills_as_variable(self):
        """skills can be used as a variable name."""
        source = '''
        main {
            let skills = ["coding", "testing"]
            print(skills)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert "['coding', 'testing']" in output[0]
    
    def test_skills_reassignment(self):
        """skills variable can be reassigned."""
        source = '''
        main {
            let skills = "initial"
            skills = "updated"
            print(skills)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "updated"


class TestAgentFunctionsBlockVariables:
    """Test that agent functions block can have variable definitions."""
    
    def test_let_in_functions_block(self):
        """let declarations work in functions block."""
        source = '''
        agent MyAgent() {
            functions {
                let config = "default"
                fn get_config(): str {
                    return config
                }
            }
            main {
                print(get_config())
            }
        }
        main {
            MyAgent()
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "default"
    
    def test_const_in_functions_block(self):
        """const declarations work in functions block."""
        source = '''
        agent MyAgent() {
            functions {
                const MAX = 100
                fn get_max(): int {
                    return MAX
                }
            }
            main {
                print(get_max())
            }
        }
        main {
            MyAgent()
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "100"
    
    def test_multiple_vars_in_functions_block(self):
        """Multiple variable declarations work in functions block."""
        source = '''
        agent MyAgent() {
            functions {
                let a = 1
                let b = 2
                const c = 3
                fn sum(): int {
                    return a + b + c
                }
            }
            main {
                print(sum())
            }
        }
        main {
            MyAgent()
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "6"


class TestListMethods:
    """Test that list objects have common methods."""
    
    def test_append(self):
        """list.append() works."""
        source = '''
        main {
            let list = [1, 2, 3]
            list.append(4)
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[1, 2, 3, 4]"
    
    def test_pop(self):
        """list.pop() works."""
        source = '''
        main {
            let list = [1, 2, 3]
            let popped = list.pop()
            print(popped)
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "3"
        assert output[1] == "[1, 2]"
    
    def test_insert(self):
        """list.insert() works."""
        source = '''
        main {
            let list = [1, 2, 3]
            list.insert(0, 0)
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[0, 1, 2, 3]"
    
    def test_remove(self):
        """list.remove() works."""
        source = '''
        main {
            let list = [1, 2, 3, 2]
            list.remove(2)
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[1, 3, 2]"
    
    def test_reverse(self):
        """list.reverse() works."""
        source = '''
        main {
            let list = [1, 2, 3]
            list.reverse()
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[3, 2, 1]"
    
    def test_sort(self):
        """list.sort() works."""
        source = '''
        main {
            let list = [3, 1, 2]
            list.sort()
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[1, 2, 3]"
    
    def test_extend(self):
        """list.extend() works."""
        source = '''
        main {
            let list = [1, 2]
            list.extend([3, 4])
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[1, 2, 3, 4]"
    
    def test_index(self):
        """list.index() works."""
        source = '''
        main {
            let list = [10, 20, 30]
            let idx = list.index(20)
            print(idx)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "1"
    
    def test_count(self):
        """list.count() works."""
        source = '''
        main {
            let list = [1, 2, 2, 3, 2]
            let cnt = list.count(2)
            print(cnt)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "3"
    
    def test_clear(self):
        """list.clear() works."""
        source = '''
        main {
            let list = [1, 2, 3]
            list.clear()
            print(list)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[]"
    
    def test_copy(self):
        """list.copy() works."""
        source = '''
        main {
            let list = [1, 2, 3]
            let copy = list.copy()
            copy.append(4)
            print(list)
            print(copy)
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "[1, 2, 3]"
        assert output[1] == "[1, 2, 3, 4]"


class TestMatchRangePattern:
    """Test that match statement supports range patterns."""
    
    def test_range_match(self):
        """Range pattern matching works."""
        source = '''
        main {
            let x = 5
            match x {
                case 1..3 {
                    print("small")
                }
                case 4..7 {
                    print("medium")
                }
                case 8..10 {
                    print("large")
                }
                default {
                    print("other")
                }
            }
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "medium"
    
    def test_range_boundary_inclusive(self):
        """Range boundaries are inclusive."""
        source = '''
        main {
            let x = 3
            match x {
                case 1..3 {
                    print("matched")
                }
                default {
                    print("not matched")
                }
            }
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "matched"
    
    def test_range_no_match(self):
        """Range pattern falls through to default when no match."""
        source = '''
        main {
            let x = 15
            match x {
                case 1..10 {
                    print("small")
                }
                default {
                    print("other")
                }
            }
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "other"


class TestMatchGuardCondition:
    """Test that match statement supports guard conditions."""
    
    def test_guard_with_range(self):
        """Guard condition works with range pattern."""
        source = '''
        main {
            let x = 25
            match x {
                case 21..30 if x == 25 {
                    print("exactly 25")
                }
                case 21..30 {
                    print("other in range")
                }
                default {
                    print("out of range")
                }
            }
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "exactly 25"
    
    def test_guard_fallback(self):
        """Guard condition falls through when false."""
        source = '''
        main {
            let x = 26
            match x {
                case 21..30 if x == 25 {
                    print("exactly 25")
                }
                case 21..30 {
                    print("other in range")
                }
                default {
                    print("out of range")
                }
            }
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "other in range"
    
    def test_guard_with_complex_condition(self):
        """Guard condition supports complex expressions."""
        source = '''
        main {
            let x = 15
            match x {
                case 10..20 if x > 12 && x < 18 {
                    print("in sweet spot")
                }
                default {
                    print("outside")
                }
            }
        }
        '''
        output, errors = run_helen(source)
        assert not errors
        assert output[0] == "in sweet spot"


class TestDotDotLexer:
    """Test that .. is correctly lexed as DOTDOT token."""
    
    def test_dotdot_token(self):
        """.. is lexed as DOTDOT, not two DOTs."""
        from helen.core.tokens import TokenType
        
        source = "1..10"
        scanner = Scanner(source=source, file='<test>')
        tokens = scanner.scan_all()
        
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 1
        assert tokens[1].type == TokenType.DOTDOT
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].literal == 10
    
    def test_float_still_works(self):
        """Floating point numbers still work after adding .. operator."""
        from helen.core.tokens import TokenType
        
        source = "3.14"
        scanner = Scanner(source=source, file='<test>')
        tokens = scanner.scan_all()
        
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].literal == 3.14
    
    def test_member_access_still_works(self):
        """Member access with . still works."""
        from helen.core.tokens import TokenType
        
        source = "obj.prop"
        scanner = Scanner(source=source, file='<test>')
        tokens = scanner.scan_all()
        
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[1].type == TokenType.DOT
        assert tokens[2].type == TokenType.IDENTIFIER
