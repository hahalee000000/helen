"""Test Chinese keyword support in the Helen lexer and parser.

Chinese keywords map to the same TokenType as their English equivalents,
so the parser and interpreter require zero changes.
"""

import pytest
from helen.core.lexer import Scanner
from helen.core.tokens import TokenType, keywords


class TestChineseKeywordsLexer:
    """Verify the lexer recognizes Chinese keywords as correct token types."""

    def test_let(self):
        source = "让 x = 42"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.LET
        assert tokens[0].lexeme == "让"

    def test_const(self):
        source = "常量 PI = 3.14"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.CONST
        assert tokens[0].lexeme == "常量"

    def test_fn(self):
        source = "函数 add(a, b) { 返回 a + b }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.FN
        assert tokens[0].lexeme == "函数"

    def test_return(self):
        source = "返回 42"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.RETURN
        assert tokens[0].lexeme == "返回"

    def test_if_else(self):
        source = "如果 x { } 否则 { }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.IF
        assert tokens[0].lexeme == "如果"
        # Find ELSE token
        else_token = next(t for t in tokens if t.type == TokenType.ELSE)
        assert else_token.lexeme == "否则"

    def test_for_in(self):
        source = "对于 x 属于 列表 { }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.FOR
        assert tokens[0].lexeme == "对于"
        in_token = next(t for t in tokens if t.type == TokenType.IN)
        assert in_token.lexeme == "属于"

    def test_while(self):
        source = "当 真 { }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.WHILE
        assert tokens[0].lexeme == "当"

    def test_break_continue(self):
        source = "中断 继续"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.BREAK
        assert tokens[0].lexeme == "中断"
        assert tokens[1].type == TokenType.CONTINUE
        assert tokens[1].lexeme == "继续"

    def test_match_case_default(self):
        source = "匹配 x { 情况 1 { } 默认 { } }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.MATCH
        assert tokens[0].lexeme == "匹配"
        case_token = next(t for t in tokens if t.type == TokenType.CASE)
        assert case_token.lexeme == "情况"
        default_token = next(t for t in tokens if t.type == TokenType.DEFAULT)
        assert default_token.lexeme == "默认"

    def test_try_catch_finally(self):
        source = "尝试 { } 捕获 RuntimeError e { } 最终 { }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.TRY
        assert tokens[0].lexeme == "尝试"
        catch_token = next(t for t in tokens if t.type == TokenType.CATCH)
        assert catch_token.lexeme == "捕获"
        finally_token = next(t for t in tokens if t.type == TokenType.FINALLY)
        assert finally_token.lexeme == "最终"

    def test_throw(self):
        source = "抛出 Error(\"msg\")"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.THROW
        assert tokens[0].lexeme == "抛出"

    def test_assert(self):
        source = "断言 x > 0"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.ASSERT
        assert tokens[0].lexeme == "断言"

    def test_literals(self):
        source = "真 假 空"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.TRUE
        assert tokens[0].lexeme == "真"
        assert tokens[1].type == TokenType.FALSE
        assert tokens[1].lexeme == "假"
        assert tokens[2].type == TokenType.NULL_KW
        assert tokens[2].lexeme == "空"

    def test_is(self):
        source = "x 是 int"
        tokens = self._scan(source)
        is_token = next(t for t in tokens if t.type == TokenType.IS)
        assert is_token.lexeme == "是"

    def test_agent_keywords(self):
        source = "智能体 大模型 执行 流式执行 异步 等待"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.AGENT
        assert tokens[0].lexeme == "智能体"
        assert tokens[1].type == TokenType.LLM
        assert tokens[1].lexeme == "大模型"
        assert tokens[2].type == TokenType.ACT
        assert tokens[2].lexeme == "执行"
        assert tokens[3].type == TokenType.STREAM
        assert tokens[3].lexeme == "流式执行"
        assert tokens[4].type == TokenType.ASYNC
        assert tokens[4].lexeme == "异步"
        assert tokens[5].type == TokenType.AWAIT
        assert tokens[5].lexeme == "等待"

    def test_agent_decl_keywords(self):
        source = "提示 描述 模型 工具 流式输出 温度 最大轮次 函数区 主"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.PROMPT
        assert tokens[0].lexeme == "提示"
        assert tokens[1].type == TokenType.DESCRIPTION
        assert tokens[1].lexeme == "描述"
        assert tokens[2].type == TokenType.MODEL
        assert tokens[2].lexeme == "模型"
        assert tokens[3].type == TokenType.TOOLS
        assert tokens[3].lexeme == "工具"
        assert tokens[4].type == TokenType.STREAMING
        assert tokens[4].lexeme == "流式输出"
        assert tokens[5].type == TokenType.TEMPERATURE
        assert tokens[5].lexeme == "温度"
        assert tokens[6].type == TokenType.MAX_TURNS
        assert tokens[6].lexeme == "最大轮次"
        assert tokens[7].type == TokenType.FUNCTIONS
        assert tokens[7].lexeme == "函数区"
        assert tokens[8].type == TokenType.MAIN
        assert tokens[8].lexeme == "主"

    def test_other_keywords(self):
        source = "导入 作为 协议 实现 调用 分支"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.IMPORT
        assert tokens[0].lexeme == "导入"
        assert tokens[1].type == TokenType.AS
        assert tokens[1].lexeme == "作为"
        assert tokens[2].type == TokenType.PROTOCOL
        assert tokens[2].lexeme == "协议"
        assert tokens[3].type == TokenType.IMPL
        assert tokens[3].lexeme == "实现"
        assert tokens[4].type == TokenType.CALL
        assert tokens[4].lexeme == "调用"
        assert tokens[5].type == TokenType.BRANCH
        assert tokens[5].lexeme == "分支"

    def test_chinese_identifiers(self):
        """Chinese characters not in keyword map should be IDENTIFIER."""
        source = "让 姓名 = \"张三\""
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.LET
        name_token = tokens[1]
        assert name_token.type == TokenType.IDENTIFIER
        assert name_token.lexeme == "姓名"

    def test_mixed_chinese_english(self):
        """Chinese and English keywords can be mixed freely."""
        source = "让 x = 42\nconst y = 100\n如果 x > 0 { 返回 x }"
        tokens = self._scan(source)
        assert tokens[0].type == TokenType.LET
        assert tokens[0].lexeme == "让"
        # const should still work
        const_token = next(t for t in tokens if t.type == TokenType.CONST)
        assert const_token.lexeme == "const"
        # 如果 should be IF
        if_token = next(t for t in tokens if t.type == TokenType.IF)
        assert if_token.lexeme == "如果"
        # 返回 should be RETURN
        return_token = next(t for t in tokens if t.type == TokenType.RETURN)
        assert return_token.lexeme == "返回"

    def test_all_44_chinese_keywords_registered(self):
        """Verify exactly 45 Chinese keywords are in the keyword map (v1.10 added 共享)."""
        kw = keywords()
        chinese = {k: v for k, v in kw.items()
                   if any('\u4e00' <= c <= '\u9fff' for c in k)}
        assert len(chinese) == 45, f"Expected 45, got {len(chinese)}: {sorted(chinese.keys())}"

    def test_no_lexer_errors(self):
        """Full Chinese program should produce zero lexer errors."""
        source = """
让 x = 10
常量 Y = 20
函数 加(甲: int, 乙: int): int {
    返回 甲 + 乙
}
如果 x > 0 {
    让 结果 = 加(x, Y)
} 否则 {
    让 结果 = 0
}
"""
        scanner = Scanner(source=source, file="<test>")
        scanner.scan_all()
        assert not scanner.has_errors, f"Unexpected errors: {scanner.errors}"

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _scan(source: str):
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        # Remove EOF
        return [t for t in tokens if t.type != TokenType.EOF]


class TestChineseKeywordsParser:
    """Verify the parser accepts Chinese keywords in full programs."""

    def test_parse_simple_let(self):
        source = "让 x = 42"
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import VarDeclNode
        stmt = program.statements[0]
        assert isinstance(stmt, VarDeclNode)
        assert stmt.name == "x"

    def test_parse_fn_with_chinese_body(self):
        source = """
函数 加(甲: int, 乙: int): int {
    返回 甲 + 乙
}
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import FunctionDeclNode
        fn = program.statements[0]
        assert isinstance(fn, FunctionDeclNode)
        assert fn.name == "加"

    def test_parse_if_else_chinese(self):
        source = """
如果 真 {
    让 x = 1
} 否则 {
    让 x = 2
}
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import IfStmtNode
        assert isinstance(program.statements[0], IfStmtNode)

    def test_parse_for_loop_chinese(self):
        source = """
对于 i 属于 [1, 2, 3] {
    print(i)
}
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import ForStmtNode
        assert isinstance(program.statements[0], ForStmtNode)

    def test_parse_match_chinese(self):
        source = """
匹配 x {
    情况 1 { print("one") }
    默认 { print("other") }
}
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import MatchStmtNode
        assert isinstance(program.statements[0], MatchStmtNode)

    def test_parse_try_catch_chinese(self):
        source = """
尝试 {
    让 x = 1
} 捕获 RuntimeError e {
    print(e)
}
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import TryStmtNode
        assert isinstance(program.statements[0], TryStmtNode)

    def test_parse_agent_chinese(self):
        source = """
智能体 翻译器 {
    描述 "翻译文本"
    提示 "你是专业翻译"
    模型 "gpt-4"
    温度 0.3
    主 {
        返回 "done"
    }
}
"""
        program = self._parse(source)
        assert len(program.statements) == 1
        from helen.core.ast import AgentDeclNode
        assert isinstance(program.statements[0], AgentDeclNode)

    def test_parse_mixed_chinese_english(self):
        """Chinese and English keywords can be freely mixed."""
        source = """
让 x = 42
const y = 100
如果 x > 0 {
    返回 x + y
}
"""
        program = self._parse(source)
        assert len(program.statements) == 3

    def test_parse_chinese_identifiers(self):
        """Chinese variable and function names should work."""
        source = """
让 姓名 = "张三"
让 年龄 = 30
函数 打招呼(名字: str) {
    print("你好, " + 名字)
}
"""
        program = self._parse(source)
        assert len(program.statements) == 3

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse(source: str):
        from helen.core.errors import ErrorReporter
        from helen.core.parser import Parser
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        if errors.has_errors:
            err_msgs = "; ".join(str(e) for e in errors.errors)
            pytest.fail(f"Parse errors: {err_msgs}")
        return program
