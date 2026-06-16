"""Tests for REPL :ask command integration with Helen assistant."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from helen.cli.repl import _handle_repl_command
from helen.interpreter.interpreter import Interpreter
from helen.semantic.analyzer import SemanticAnalyzer
from helen.core.errors import ErrorReporter


class TestREPLAskCommand:
    """Test REPL :ask command integration."""

    def test_ask_command_exists(self):
        """:ask command should be recognized by REPL."""
        errors = ErrorReporter()
        interp = Interpreter(errors=errors)
        analyzer = SemanticAnalyzer(errors)
        
        # Mock the assistant runner to avoid actual LLM call
        with patch('helen.cli.repl._run_helen_assistant') as mock_run:
            mock_run.return_value = "Mock response"
            
            with patch('builtins.print'):
                # :ask should be handled (return True) and not print "Unknown command"
                result = _handle_repl_command(":ask How do I define an agent?", interp, analyzer)
                assert result is True, ":ask command should be recognized"
                # Should call the assistant
                mock_run.assert_called_once()

    def test_ask_command_without_question_shows_usage(self):
        """:ask without question should show usage."""
        errors = ErrorReporter()
        interp = Interpreter(errors=errors)
        analyzer = SemanticAnalyzer(errors)
        
        with patch('builtins.print') as mock_print:
            result = _handle_repl_command(":ask", interp, analyzer)
            assert result is True
            # Should print usage message
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "usage" in call_args.lower() or "ask" in call_args.lower()

    def test_ask_command_invokes_helen_assistant(self):
        """:ask should invoke Helen assistant program."""
        errors = ErrorReporter()
        interp = Interpreter(errors=errors)
        analyzer = SemanticAnalyzer(errors)
        
        # Mock the Helen assistant execution
        with patch('helen.cli.repl._run_helen_assistant') as mock_run:
            mock_run.return_value = "Helen agents are defined with 'agent' keyword..."
            
            with patch('builtins.print') as mock_print:
                result = _handle_repl_command(":ask How to define agent?", interp, analyzer)
                assert result is True
                mock_run.assert_called_once_with("How to define agent?")
                # Should print the response
                mock_print.assert_called()

    def test_ask_command_prints_response(self):
        """:ask should print assistant response."""
        errors = ErrorReporter()
        interp = Interpreter(errors=errors)
        analyzer = SemanticAnalyzer(errors)
        
        with patch('helen.cli.repl._run_helen_assistant') as mock_run:
            mock_run.return_value = "Test response from Helen assistant"
            
            with patch('builtins.print') as mock_print:
                _handle_repl_command(":ask test question", interp, analyzer)
                
                # Should print the response
                printed = False
                for call in mock_print.call_args_list:
                    if "Test response" in str(call):
                        printed = True
                        break
                assert printed, "Should print assistant response"

    def test_help_command_includes_ask(self):
        """:help should mention :ask command."""
        errors = ErrorReporter()
        interp = Interpreter(errors=errors)
        analyzer = SemanticAnalyzer(errors)
        
        with patch('builtins.print') as mock_print:
            result = _handle_repl_command(":help", interp, analyzer)
            assert result is True
            
            # Should mention :ask in help
            help_text = ""
            for call in mock_print.call_args_list:
                help_text += str(call)
            
            assert ":ask" in help_text, "Help should mention :ask command"
