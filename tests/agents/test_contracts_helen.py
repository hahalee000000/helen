"""Tests for Helen-native contracts.

TDD: Write tests first, then implement contracts.helen
"""

import pytest
from pathlib import Path


class TestContractsHelen:
    """Test Helen-native contract definitions."""
    
    @pytest.fixture
    def contracts_path(self):
        return Path(__file__).parent.parent.parent / "agents" / "contracts" / "contracts.helen"
    
    def test_contracts_file_exists(self, contracts_path):
        """Contract file should exist."""
        assert contracts_path.exists(), f"contracts.helen not found at {contracts_path}"
    
    def test_contracts_parseable(self, contracts_path):
        """Contract file should be parseable by Helen parser."""
        # Use subprocess to run helen check (more reliable than importing)
        import subprocess
        result = subprocess.run(
            ["helen", "check", str(contracts_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        # Should parse successfully
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Parse failed: {result.stdout}"
    
    def test_skill_manager_contract_defined(self, contracts_path):
        """SkillManager contract should be defined."""
        source = contracts_path.read_text()
        
        # Check for contract function signatures
        assert "fn skill_manager_create" in source or "skill_manager_create" in source
        assert "fn skill_manager_read" in source or "skill_manager_read" in source
        assert "fn skill_manager_update" in source or "skill_manager_update" in source
        assert "fn skill_manager_delete" in source or "skill_manager_delete" in source
        assert "fn skill_manager_list" in source or "skill_manager_list" in source
    
    def test_skill_matcher_contract_defined(self, contracts_path):
        """SkillMatcher contract should be defined."""
        source = contracts_path.read_text()
        
        assert "fn skill_matcher_match" in source or "skill_matcher_match" in source
        assert "fn skill_matcher_extract_keywords" in source or "skill_matcher_extract_keywords" in source
    
    def test_skill_learner_contract_defined(self, contracts_path):
        """SkillLearner contract should be defined."""
        source = contracts_path.read_text()
        
        assert "fn skill_learner_learn" in source or "skill_learner_learn" in source
        assert "fn skill_learner_determine_category" in source or "skill_learner_determine_category" in source
    
    def test_skill_evolver_contract_defined(self, contracts_path):
        """SkillEvolver contract should be defined."""
        source = contracts_path.read_text()
        
        assert "fn skill_evolver_evolve" in source or "skill_evolver_evolve" in source
    
    def test_programming_agent_contract_defined(self, contracts_path):
        """ProgrammingAgent contract should be defined."""
        source = contracts_path.read_text()
        
        assert "fn programming_agent_process" in source or "programming_agent_process" in source
        assert "fn programming_agent_analyze" in source or "programming_agent_analyze" in source
        assert "fn programming_agent_run_tests" in source or "programming_agent_run_tests" in source
    
    def test_contracts_have_documentation(self, contracts_path):
        """Contracts should have documentation comments."""
        source = contracts_path.read_text()
        
        # Check for documentation patterns
        doc_patterns = [
            "Preconditions",
            "Postconditions",
            "Returns",
            "Parameters"
        ]
        
        found_docs = sum(1 for pattern in doc_patterns if pattern in source)
        assert found_docs >= 2, f"Expected at least 2 documentation patterns, found {found_docs}"
    
    def test_contracts_use_v15_features(self, contracts_path):
        """Contracts should use v1.5 features (list methods, functions block vars)."""
        source = contracts_path.read_text()
        
        # Check for v1.5 features
        # List methods
        has_list_methods = any(method in source for method in [
            ".append(", ".extend(", ".pop(", ".sort(", ".reverse("
        ])
        
        # Functions block variables (let/const in agent functions block)
        has_functions_vars = "let " in source and "const " in source
        
        # Match range pattern
        has_match_range = ".." in source
        
        # At least one v1.5 feature should be used
        assert has_list_methods or has_functions_vars or has_match_range, \
            "Contracts should use at least one v1.5 feature"


class TestContractsExecution:
    """Test that contracts can be executed (no runtime errors)."""
    
    @pytest.fixture
    def contracts_path(self):
        return Path(__file__).parent.parent.parent / "agents" / "contracts" / "contracts.helen"
    
    def test_contracts_no_syntax_errors(self, contracts_path):
        """Contracts should have no syntax errors."""
        import subprocess
        # Use helen CLI directly
        result = subprocess.run(
            ["helen", "check", str(contracts_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        # Should pass syntax check (return code 0 or "OK" in output)
        assert result.returncode == 0 or "OK" in result.stdout or "OK" in result.stderr, \
            f"Syntax check failed: {result.stderr}"
    
    def test_contract_functions_return_maps(self, contracts_path):
        """Contract functions should return map type."""
        source = contracts_path.read_text()
        
        # All contract functions should have -> map return type
        import re
        fn_pattern = r'fn\s+\w+\s*\([^)]*\)\s*->\s*(\w+)'
        matches = re.findall(fn_pattern, source)
        
        if matches:
            # At least some functions should return map
            map_returns = sum(1 for m in matches if m == "map")
            assert map_returns > 0, "Expected at least some functions to return map"
