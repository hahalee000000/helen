"""Tests for helen VS Code extension — TextMate grammar & manifest (HLD M13).

Covers:
- TextMate grammar is valid JSON
- All Helen keywords are covered by the grammar
- package.json is valid VS Code extension manifest
- language-configuration.json is valid
- Grammar scopes are correctly defined
- Keyword regex patterns compile without error
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Project root relative to this file
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXT_DIR = PROJECT_ROOT / "extensions" / "vscode"


class TestTextMateGrammar:
    """Test helen.tmLanguage.json validity and completeness."""

    def setup_method(self):
        with open(EXT_DIR / "syntaxes" / "helen.tmLanguage.json") as f:
            self.grammar = json.load(f)

    def test_valid_json(self):
        """Grammar file is valid JSON."""
        assert self.grammar is not None

    def test_has_scope_name(self):
        """Grammar defines source.helen scope."""
        assert self.grammar["scopeName"] == "source.helen"

    def test_has_file_types(self):
        """Grammar associates with .helen files."""
        assert ".helen" in self.grammar["fileTypes"]

    def test_has_repository(self):
        """Grammar defines a repository of patterns."""
        assert "repository" in self.grammar

    def test_has_comments_pattern(self):
        """Grammar includes comment patterns."""
        repo = self.grammar["repository"]
        assert "comments" in repo

    def test_has_strings_pattern(self):
        """Grammar includes string patterns."""
        repo = self.grammar["repository"]
        assert "strings" in repo

    def test_has_keywords_pattern(self):
        """Grammar includes keyword patterns."""
        repo = self.grammar["repository"]
        assert "keywords" in repo

    def test_has_literals_pattern(self):
        """Grammar includes literal patterns."""
        repo = self.grammar["repository"]
        # Grammar uses 'constants' instead of 'literals'
        assert "constants" in repo

    def test_all_regex_patterns_compile(self):
        """All regex patterns in the grammar compile without error."""
        repo = self.grammar.get("repository", {})
        for section_name, section in repo.items():
            patterns = section.get("patterns", [])
            for pattern in patterns:
                regex = pattern.get("match")
                if regex:
                    try:
                        re.compile(regex)
                    except re.error as e:
                        raise AssertionError(
                            f"Invalid regex in {section_name}: {regex!r} — {e}"
                        )


class TestKeywordCoverage:
    """Test that all Helen keywords are covered by the TextMate grammar."""

    # All keywords from helen.core.tokens._KEYWORD_MAP (v1.14: removed 'stream', merged into llm act)
    HELLEN_KEYWORDS = {
        "agent", "description", "model", "tools",
        "temperature", "max-turns", "prompt", "llm", "import",
        "let", "const", "shared", "if", "else", "for", "while", "break", "continue",
        "return", "await", "async", "match", "case", "branch",
        "default", "act", "try", "catch", "finally",
        "throw", "assert",
        "fn", "as", "in", "functions", "main", "alias",
        "protocol", "impl", "is",
        "streaming",
        "true", "false", "null",
    }

    def setup_method(self):
        with open(EXT_DIR / "syntaxes" / "helen.tmLanguage.json") as f:
            self.grammar = json.load(f)

    def _extract_all_keyword_patterns(self) -> list[str]:
        """Extract all keyword regex patterns from the grammar."""
        patterns = []
        keywords_section = self.grammar["repository"]["keywords"]
        for p in keywords_section.get("patterns", []):
            if "match" in p:
                patterns.append(p["match"])
        # Also check literals for true/false/null
        literals_section = self.grammar["repository"]["constants"]
        for p in literals_section.get("patterns", []):
            if "match" in p:
                patterns.append(p["match"])
        return patterns

    def _keyword_matches_pattern(self, keyword: str, pattern: str) -> bool:
        """Check if a keyword is matched by a regex pattern."""
        try:
            regex = re.compile(pattern)
            # Test the exact keyword with word boundaries
            test_str = keyword
            return regex.search(test_str) is not None
        except re.error:
            return False

    def test_all_keywords_covered(self):
        """Every Helen keyword is matched by at least one grammar pattern."""
        patterns = self._extract_all_keyword_patterns()
        uncovered = []
        for kw in self.HELLEN_KEYWORDS:
            covered = any(self._keyword_matches_pattern(kw, p) for p in patterns)
            if not covered:
                uncovered.append(kw)
        assert not uncovered, f"Keywords not covered by grammar: {uncovered}"


class TestPackageJson:
    """Test package.json validity."""

    def setup_method(self):
        with open(EXT_DIR / "package.json") as f:
            self.pkg = json.load(f)

    def test_valid_json(self):
        """package.json is valid JSON."""
        assert self.pkg is not None

    def test_has_required_fields(self):
        """Has name, displayName, version, engines."""
        assert "name" in self.pkg
        assert "displayName" in self.pkg
        assert "version" in self.pkg
        assert "engines" in self.pkg

    def test_contributes_languages(self):
        """Contributes helen language."""
        contributes = self.pkg["contributes"]
        assert "languages" in contributes
        langs = contributes["languages"]
        helen_lang = [lang for lang in langs if lang.get("id") == "helen"]
        assert len(helen_lang) == 1
        lang = helen_lang[0]
        assert ".helen" in lang.get("extensions", [])

    def test_contributes_grammar(self):
        """Contributes TextMate grammar."""
        contributes = self.pkg["contributes"]
        assert "grammars" in contributes
        grammars = contributes["grammars"]
        assert len(grammars) >= 1
        grammar = grammars[0]
        assert grammar["language"] == "helen"
        assert grammar["scopeName"] == "source.helen"
        assert grammar["path"] == "./syntaxes/helen.tmLanguage.json"

    def test_vscode_engine_version(self):
        """Specifies VS Code engine version."""
        assert "vscode" in self.pkg["engines"]


class TestLanguageConfiguration:
    """Test language-configuration.json validity."""

    def setup_method(self):
        with open(EXT_DIR / "language-configuration.json") as f:
            self.config = json.load(f)

    def test_valid_json(self):
        """language-configuration.json is valid JSON."""
        assert self.config is not None

    def test_has_comments(self):
        """Defines comment styles."""
        assert "comments" in self.config
        assert "lineComment" in self.config["comments"]
        assert "blockComment" in self.config["comments"]

    def test_has_brackets(self):
        """Defines bracket pairs."""
        assert "brackets" in self.config
        brackets = self.config["brackets"]
        assert ["{", "}"] in brackets
        assert ["[", "]"] in brackets
        assert ["(", ")"] in brackets

    def test_has_auto_closing_pairs(self):
        """Defines auto-closing pairs."""
        assert "autoClosingPairs" in self.config
        opens = [p["open"] for p in self.config["autoClosingPairs"]]
        assert '"' in opens
        assert "{" in opens

    def test_has_word_pattern(self):
        """Defines word pattern for selection."""
        assert "wordPattern" in self.config
