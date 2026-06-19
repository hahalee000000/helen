"""Async interpreter contract for true concurrent execution (Phase 1b).

This module defines the interface for async-capable interpretation,
enabling true concurrent LLM calls without blocking threads.

Contract:
- AsyncInterpreter can execute Helen code asynchronously
- LLM calls use act_async() / route_async() (non-blocking)
- Multiple async tasks run concurrently in a single thread
- Environment isolation between concurrent tasks
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from helen.core.ast import (
    LlmActExprNode,
    LlmIfStmtNode,
    LiteralNode,
    StatementNode,
)
from helen.interpreter.interpreter import Interpreter


class AsyncInterpreterContract:
    """Contract for async-capable interpreter.

    This defines the interface that async interpreter implementations
    must satisfy. Used for type checking and documentation.
    """

    @abstractmethod
    async def execute_stmt_async(self, stmt: StatementNode) -> Any:
        """Execute a statement asynchronously.

        Args:
            stmt: The statement to execute.

        Returns:
            The result of execution (may be a coroutine).
        """
        ...

    @abstractmethod
    async def execute_stmts_async(self, stmts: list[StatementNode]) -> Any:
        """Execute a list of statements asynchronously.

        Args:
            stmts: Statements to execute in order.

        Returns:
            The result of the last statement.
        """
        ...

    @abstractmethod
    async def visit_llm_act_expr_async(self, node: LlmActExprNode) -> str | None:
        """Execute llm act expression asynchronously.

        Must call self.llm_runtime.act_async() (non-blocking).

        Args:
            node: The llm act expression node.

        Returns:
            The LLM response text, or None on failure.
        """
        ...

    @abstractmethod
    async def visit_llm_if_stmt_async(self, node: LlmIfStmtNode) -> Any:
        """Execute llm if statement asynchronously.

        Must call self.llm_runtime.route_async() (non-blocking).

        Args:
            node: The llm if statement node.

        Returns:
            The result of executing the matched branch.
        """
        ...


class AsyncLLMInterpreter(Interpreter, AsyncInterpreterContract):
    """Async-capable interpreter for concurrent LLM execution.

    Extends Interpreter with async methods for LLM operations.
    Non-LLM code executes synchronously; only LLM calls are async.

    Key features:
    - LLM calls use act_async() / route_async() (non-blocking)
    - Multiple async tasks can run concurrently
    - Environment isolation between tasks
    - Backward compatible with sync Interpreter
    """

    async def execute_stmt_async(self, stmt: StatementNode) -> Any:
        """Execute a statement asynchronously.

        For LLM statements, uses async execution.
        For other statements, delegates to sync execution.
        """
        from helen.core.ast import LlmActExprNode, LlmIfStmtNode

        if isinstance(stmt, LlmActExprNode):
            return await self.visit_llm_act_expr_async(stmt)
        elif isinstance(stmt, LlmIfStmtNode):
            return await self.visit_llm_if_stmt_async(stmt)
        else:
            # Non-LLM statements execute synchronously
            return stmt.accept(self)

    async def execute_stmts_async(self, stmts: list[StatementNode]) -> Any:
        """Execute a list of statements asynchronously.

        Executes each statement in order, using async for LLM statements.
        """
        from helen.interpreter.exceptions import (
            BreakSentinel,
            ContinueSentinel,
            ReturnSentinel,
        )

        result = None
        for stmt in stmts:
            step = await self.execute_stmt_async(stmt)
            if isinstance(step, ReturnSentinel):
                return step
            if isinstance(step, (BreakSentinel, ContinueSentinel)):
                return step
            result = step
        return result

    async def visit_llm_act_expr_async(self, node: LlmActExprNode) -> str | None:
        """Execute llm act expression asynchronously.

        Uses act_async() for non-blocking LLM call.
        """
        from helen.interpreter.exceptions import HelenRuntimeError

        # Evaluate prompt expression (sync - no LLM call yet)
        prompt_obj = node.prompt.accept(self) if node.prompt else None
        prompt = str(prompt_obj) if prompt_obj is not None else None

        # Get agent settings
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))
        max_turns = int(self._get_agent_setting("max-turns", 1))

        # Build tools list
        tools = self._build_tools_list()
        if tools and max_turns < 3:
            max_turns = 3

        # Get rendered agent prompt as system_prompt
        system_prompt = self._get_rendered_agent_prompt()

        # Record user message to history
        if prompt:
            self._add_to_history("user", prompt)

        try:
            # KEY: Call act_async() for non-blocking execution
            response = await self.llm_runtime.act_async(
                prompt or "", tools=tools, model=model,
                temperature=temperature, max_turns=max_turns,
                system_prompt=system_prompt,
            )
            # Record assistant response to history
            if response and response.text:
                self._add_to_history("assistant", response.text)
            return response.text if response else None
        except HelenRuntimeError:
            return None

    async def visit_llm_if_stmt_async(self, node: LlmIfStmtNode) -> Any:
        """Execute llm if statement asynchronously.

        Uses route_async() for non-blocking LLM routing.
        """
        from helen.interpreter.exceptions import HelenRuntimeError

        # Build branch names
        branches = []
        for b in node.branches:
            if b.condition is not None:
                if isinstance(b.condition, LiteralNode):
                    branches.append(str(b.condition.value))
                else:
                    branches.append(str(b.condition))
            else:
                branches.append("default")

        # Evaluate description expression to string
        if isinstance(node.description, str):
            desc_str = node.description
        else:
            desc_val = node.description.accept(self)
            desc_str = str(desc_val) if desc_val is not None else ""

        # Get context from environment (conversation summary)
        context = self._get_context()

        # Record user message to history
        self._add_to_history("user", f"[route] {desc_str}")

        try:
            # KEY: Call route_async() for non-blocking execution
            matched = await self.llm_runtime.route_async(
                desc_str, branches, context=context
            )
        except (HelenRuntimeError, ValueError, TypeError):
            matched = None

        # Record assistant response to history
        if matched is not None:
            self._add_to_history("assistant", f"[routed to: {matched}]")

        # Validate against pre-defined enum
        if matched is not None and matched not in branches:
            matched = None

        # Find and execute matched branch
        for b in node.branches:
            if b.condition is not None:
                if isinstance(b.condition, LiteralNode):
                    branch_name = str(b.condition.value)
                else:
                    branch_name = str(b.condition)
            else:
                branch_name = "default"

            if matched == branch_name:
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    result = self._execute_stmts(b.body)
                    return result
                finally:
                    self.environment = old_env

        # No match or parsing failed -> execute default branch
        for b in node.branches:
            if b.condition is None:  # default branch
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    result = self._execute_stmts(b.body)
                    return result
                finally:
                    self.environment = old_env

        return None
