"""Tests for BaseAgent.

This module contains comprehensive tests for the BaseAgent class,
including initialization, logging, clarification handling, and execution
flow.
"""

import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext
from sgr_deep_research.core.tools import BaseTool, ReasoningTool
from tests.conftest import create_test_agent


class TestBaseAgentInitialization:
    """Tests for BaseAgent initialization and setup."""

    def test_initialization_basic(self):
        """Test basic initialization with required parameters."""
        from sgr_deep_research.core.agent_definition import ExecutionConfig

        agent = create_test_agent(
            BaseAgent,
            task="Test task",
            execution_config=ExecutionConfig(max_iterations=20, max_clarifications=3),
        )

        assert agent.task == "Test task"
        assert agent.name == "base_agent"
        assert agent.max_iterations == 20
        assert agent.max_clarifications == 3

    def test_initialization_with_custom_limits(self):
        """Test initialization with custom iteration and clarification
        limits."""
        from sgr_deep_research.core.agent_definition import ExecutionConfig

        agent = create_test_agent(
            BaseAgent,
            task="Test task",
            execution_config=ExecutionConfig(max_iterations=10, max_clarifications=5),
        )

        assert agent.max_iterations == 10
        assert agent.max_clarifications == 5

    def test_id_generation(self):
        """Test that unique ID is generated correctly."""
        agent = create_test_agent(BaseAgent, task="Test")

        assert agent.id.startswith("base_agent_")
        # Verify UUID format
        uuid_part = agent.id.replace("base_agent_", "")
        uuid.UUID(uuid_part)  # Should not raise

    def test_multiple_agents_have_unique_ids(self):
        """Test that multiple agents get unique IDs."""
        agent1 = create_test_agent(BaseAgent, task="Task 1")
        agent2 = create_test_agent(BaseAgent, task="Task 2")

        assert agent1.id != agent2.id

    def test_toolkit_initialization_default(self):
        """Test that toolkit is initialized as empty list by default."""
        agent = create_test_agent(BaseAgent, task="Test")

        assert agent.toolkit == []

    def test_toolkit_initialization_with_custom_tools(self):
        """Test adding custom tools to toolkit."""

        class CustomTool(BaseTool):
            pass

        agent = create_test_agent(BaseAgent, task="Test", toolkit=[CustomTool])

        assert CustomTool in agent.toolkit

    def test_context_initialization(self):
        """Test that ResearchContext is initialized."""
        agent = create_test_agent(BaseAgent, task="Test")

        assert isinstance(agent._context, ResearchContext)
        assert agent._context.iteration == 0
        assert agent._context.searches_used == 0
        assert agent._context.clarifications_used == 0

    def test_conversation_log_initialization(self):
        """Test that conversation and log are initialized as empty lists."""
        agent = create_test_agent(BaseAgent, task="Test")

        assert agent.conversation == []
        assert agent.log == []

    def test_creation_time_set(self):
        """Test that creation_time is set."""
        before = datetime.now()
        agent = create_test_agent(BaseAgent, task="Test")
        after = datetime.now()

        assert before <= agent.creation_time <= after

    def test_logger_initialization(self):
        """Test that logger is correctly initialized."""
        agent = create_test_agent(BaseAgent, task="Test")

        assert agent.logger is not None
        assert "sgr_deep_research.agents" in agent.logger.name
        assert agent.id in agent.logger.name


class TestBaseAgentClarificationHandling:
    """Tests for clarification handling functionality."""

    @pytest.mark.asyncio
    async def test_provide_clarification_basic(self):
        """Test basic clarification provision."""
        agent = create_test_agent(BaseAgent, task="Test")
        clarification = "This is a clarification"

        await agent.provide_clarification(clarification)

        assert len(agent.conversation) == 1
        assert agent.conversation[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_provide_clarification_increments_counter(self):
        """Test that providing clarification increments the counter."""
        agent = create_test_agent(BaseAgent, task="Test")

        await agent.provide_clarification("First clarification")
        assert agent._context.clarifications_used == 1

        await agent.provide_clarification("Second clarification")
        assert agent._context.clarifications_used == 2

    @pytest.mark.asyncio
    async def test_provide_clarification_sets_event(self):
        """Test that providing clarification sets the clarification_received
        event."""
        agent = create_test_agent(BaseAgent, task="Test")
        agent._context.clarification_received.clear()

        await agent.provide_clarification("Clarification")

        assert agent._context.clarification_received.is_set()

    @pytest.mark.asyncio
    async def test_provide_clarification_changes_state(self):
        """Test that providing clarification changes state to RESEARCHING."""
        agent = create_test_agent(BaseAgent, task="Test")
        agent._context.state = AgentStatesEnum.WAITING_FOR_CLARIFICATION

        await agent.provide_clarification("Clarification")

        assert agent._context.state == AgentStatesEnum.RESEARCHING


class TestBaseAgentLogging:
    """Tests for logging functionality."""

    def test_log_reasoning_adds_to_log(self):
        """Test that _log_reasoning adds entry to log."""
        agent = create_test_agent(BaseAgent, task="Test")
        agent._context.iteration = 1

        reasoning = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="In progress",
            enough_data=False,
            remaining_steps=["Next step"],
            task_completed=False,
        )

        agent._log_reasoning(reasoning)

        assert len(agent.log) == 1
        assert agent.log[0]["step_type"] == "reasoning"
        assert agent.log[0]["step_number"] == 1

    def test_log_reasoning_contains_reasoning_data(self):
        """Test that logged reasoning contains all reasoning data."""
        agent = create_test_agent(BaseAgent, task="Test")

        reasoning = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="Good",
            enough_data=True,
            remaining_steps=["Final"],
            task_completed=False,
        )

        agent._log_reasoning(reasoning)

        log_entry = agent.log[0]
        assert "agent_reasoning" in log_entry
        assert log_entry["agent_reasoning"]["enough_data"] is True

    def test_log_tool_execution_adds_to_log(self):
        """Test that _log_tool_execution adds entry to log."""
        agent = create_test_agent(BaseAgent, task="Test")
        agent._context.iteration = 1

        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="Good",
            enough_data=False,
            remaining_steps=["Next"],
            task_completed=False,
        )

        agent._log_tool_execution(tool, "Tool result")

        assert len(agent.log) == 1
        assert agent.log[0]["step_type"] == "tool_execution"
        assert agent.log[0]["tool_name"] == "reasoningtool"

    def test_log_tool_execution_contains_result(self):
        """Test that logged tool execution contains result."""
        agent = create_test_agent(BaseAgent, task="Test")

        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="Good",
            enough_data=False,
            remaining_steps=["Next"],
            task_completed=False,
        )

        result = "Test execution result"
        agent._log_tool_execution(tool, result)

        log_entry = agent.log[0]
        assert log_entry["agent_tool_execution_result"] == result


class TestBaseAgentAbstractMethods:
    """Tests for abstract methods that must be implemented by subclasses."""

    @pytest.mark.asyncio
    async def test_prepare_tools_raises_not_implemented(self):
        """Test that _prepare_tools raises NotImplementedError."""
        agent = create_test_agent(BaseAgent, task="Test")

        with pytest.raises(NotImplementedError):
            await agent._prepare_tools()

    @pytest.mark.asyncio
    async def test_reasoning_phase_raises_not_implemented(self):
        """Test that _reasoning_phase raises NotImplementedError."""
        agent = create_test_agent(BaseAgent, task="Test")

        with pytest.raises(NotImplementedError):
            await agent._reasoning_phase()

    @pytest.mark.asyncio
    async def test_select_action_phase_raises_not_implemented(self):
        """Test that _select_action_phase raises NotImplementedError."""
        agent = create_test_agent(BaseAgent, task="Test")
        reasoning = Mock()

        with pytest.raises(NotImplementedError):
            await agent._select_action_phase(reasoning)

    @pytest.mark.asyncio
    async def test_action_phase_raises_not_implemented(self):
        """Test that _action_phase raises NotImplementedError."""
        agent = create_test_agent(BaseAgent, task="Test")
        tool = Mock()

        with pytest.raises(NotImplementedError):
            await agent._action_phase(tool)


class TestBaseAgentPrepareContext:
    """Tests for context preparation."""

    @pytest.mark.asyncio
    async def test_prepare_context_basic(self):
        """Test basic context preparation."""
        agent = create_test_agent(BaseAgent, task="Test")
        agent.conversation = [{"role": "user", "content": "test"}]

        context = await agent._prepare_context()

        assert len(context) == 2  # system + user
        assert context[0]["role"] == "system"
        assert context[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_prepare_context_with_multiple_messages(self):
        """Test context preparation with multiple conversation messages."""
        agent = create_test_agent(BaseAgent, task="Test")
        agent.conversation = [
            {"role": "user", "content": "message 1"},
            {"role": "assistant", "content": "response 1"},
            {"role": "user", "content": "message 2"},
        ]

        context = await agent._prepare_context()

        assert len(context) == 4  # system + 3 messages
