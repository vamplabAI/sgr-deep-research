"""Tests for BaseAgent.

This module contains comprehensive tests for the BaseAgent class,
including initialization, logging, clarification handling, and execution flow.
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext
from sgr_deep_research.core.tools import BaseTool, ClarificationTool, ReasoningTool


class TestBaseAgentInitialization:
    """Tests for BaseAgent initialization and setup."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_initialization_basic(self, mock_openai, mock_get_config):
        """Test basic initialization with required parameters."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test task")
        
        assert agent.task == "Test task"
        assert agent.name == "base_agent"
        assert agent.max_iterations == 20
        assert agent.max_clarifications == 3

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_initialization_with_custom_limits(self, mock_openai, mock_get_config):
        """Test initialization with custom iteration and clarification limits."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(
            task="Test task",
            max_iterations=10,
            max_clarifications=5
        )
        
        assert agent.max_iterations == 10
        assert agent.max_clarifications == 5

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_id_generation(self, mock_openai, mock_get_config):
        """Test that unique ID is generated correctly."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        assert agent.id.startswith("base_agent_")
        # Verify UUID format
        uuid_part = agent.id.replace("base_agent_", "")
        uuid.UUID(uuid_part)  # Should not raise

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_multiple_agents_have_unique_ids(self, mock_openai, mock_get_config):
        """Test that multiple agents get unique IDs."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent1 = BaseAgent(task="Task 1")
        agent2 = BaseAgent(task="Task 2")
        
        assert agent1.id != agent2.id

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_toolkit_initialization_default(self, mock_openai, mock_get_config):
        """Test that toolkit includes system_agent_tools by default."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        # Configure mock to return a regular Mock instead of AsyncMock
        mock_openai.return_value = Mock()
        
        agent = BaseAgent(task="Test")
        
        # Should have system_agent_tools
        assert len(agent.toolkit) > 0
        # Check that ReasoningTool and ClarificationTool are present
        tool_names = [tool.tool_name for tool in agent.toolkit]
        assert "reasoningtool" in tool_names
        assert "clarificationtool" in tool_names

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_toolkit_initialization_with_custom_tools(self, mock_openai, mock_get_config):
        """Test adding custom tools to toolkit."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        class CustomTool(BaseTool):
            pass
        
        agent = BaseAgent(task="Test", toolkit=[CustomTool])
        
        # Should have both system tools and custom tool
        assert CustomTool in agent.toolkit

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_context_initialization(self, mock_openai, mock_get_config):
        """Test that ResearchContext is initialized."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        assert isinstance(agent._context, ResearchContext)
        assert agent._context.iteration == 0
        assert agent._context.searches_used == 0
        assert agent._context.clarifications_used == 0

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_conversation_log_initialization(self, mock_openai, mock_get_config):
        """Test that conversation and log are initialized as empty lists."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        assert agent.conversation == []
        assert agent.log == []

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_creation_time_set(self, mock_openai, mock_get_config):
        """Test that creation_time is set."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        before = datetime.now()
        agent = BaseAgent(task="Test")
        after = datetime.now()
        
        assert before <= agent.creation_time <= after

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_logger_initialization(self, mock_openai, mock_get_config):
        """Test that logger is correctly initialized."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        assert agent.logger is not None
        assert "sgr_deep_research.agents" in agent.logger.name
        assert agent.id in agent.logger.name

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @patch("sgr_deep_research.core.base_agent.OpenAIStreamingGenerator")
    def test_streaming_generator_initialization(self, mock_generator, mock_openai, mock_get_config):
        """Test that streaming generator is initialized with agent ID."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        mock_generator.assert_called_once_with(model=agent.id)


class TestBaseAgentClarificationHandling:
    """Tests for clarification handling functionality."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_provide_clarification_basic(self, mock_openai, mock_get_config):
        """Test basic clarification provision."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        clarification = "This is a clarification"
        
        await agent.provide_clarification(clarification)
        
        assert len(agent.conversation) == 1
        assert agent.conversation[0]["role"] == "user"

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_provide_clarification_increments_counter(self, mock_openai, mock_get_config):
        """Test that providing clarification increments the counter."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        await agent.provide_clarification("First clarification")
        assert agent._context.clarifications_used == 1
        
        await agent.provide_clarification("Second clarification")
        assert agent._context.clarifications_used == 2

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_provide_clarification_sets_event(self, mock_openai, mock_get_config):
        """Test that providing clarification sets the clarification_received event."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        agent._context.clarification_received.clear()
        
        await agent.provide_clarification("Clarification")
        
        assert agent._context.clarification_received.is_set()

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_provide_clarification_changes_state(self, mock_openai, mock_get_config):
        """Test that providing clarification changes state to RESEARCHING."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        agent._context.state = AgentStatesEnum.WAITING_FOR_CLARIFICATION
        
        await agent.provide_clarification("Clarification")
        
        assert agent._context.state == AgentStatesEnum.RESEARCHING

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_provide_clarification_with_long_text(self, mock_openai, mock_get_config):
        """Test clarification with very long text."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        long_clarification = "A" * 5000
        
        await agent.provide_clarification(long_clarification)
        
        assert len(agent.conversation) == 1

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_provide_clarification_with_unicode(self, mock_openai, mock_get_config):
        """Test clarification with Unicode characters."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        unicode_clarification = "Пояснение на русском 中文 日本語"
        
        await agent.provide_clarification(unicode_clarification)
        
        assert len(agent.conversation) == 1


class TestBaseAgentLogging:
    """Tests for logging functionality."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_log_reasoning_adds_to_log(self, mock_openai, mock_get_config):
        """Test that _log_reasoning adds entry to log."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        agent._context.iteration = 1
        
        reasoning = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="In progress",
            enough_data=False,
            remaining_steps=["Next step"],
            task_completed=False
        )
        
        agent._log_reasoning(reasoning)
        
        assert len(agent.log) == 1
        assert agent.log[0]["step_type"] == "reasoning"
        assert agent.log[0]["step_number"] == 1

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_log_reasoning_contains_reasoning_data(self, mock_openai, mock_get_config):
        """Test that logged reasoning contains all reasoning data."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        reasoning = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="Good",
            enough_data=True,
            remaining_steps=["Final"],
            task_completed=False
        )
        
        agent._log_reasoning(reasoning)
        
        log_entry = agent.log[0]
        assert "agent_reasoning" in log_entry
        assert log_entry["agent_reasoning"]["enough_data"] is True

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_log_tool_execution_adds_to_log(self, mock_openai, mock_get_config):
        """Test that _log_tool_execution adds entry to log."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        agent._context.iteration = 1
        
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="Good",
            enough_data=False,
            remaining_steps=["Next"],
            task_completed=False
        )
        
        agent._log_tool_execution(tool, "Tool result")
        
        assert len(agent.log) == 1
        assert agent.log[0]["step_type"] == "tool_execution"
        assert agent.log[0]["tool_name"] == "reasoningtool"

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_log_tool_execution_contains_result(self, mock_openai, mock_get_config):
        """Test that logged tool execution contains result."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Testing",
            plan_status="Good",
            enough_data=False,
            remaining_steps=["Next"],
            task_completed=False
        )
        
        result = "Test execution result"
        agent._log_tool_execution(tool, result)
        
        log_entry = agent.log[0]
        assert log_entry["agent_tool_execution_result"] == result



class TestBaseAgentAbstractMethods:
    """Tests for abstract methods that must be implemented by subclasses."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_tools_raises_not_implemented(self, mock_openai, mock_get_config):
        """Test that _prepare_tools raises NotImplementedError."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        with pytest.raises(NotImplementedError):
            await agent._prepare_tools()

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_reasoning_phase_raises_not_implemented(self, mock_openai, mock_get_config):
        """Test that _reasoning_phase raises NotImplementedError."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        
        with pytest.raises(NotImplementedError):
            await agent._reasoning_phase()

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_select_action_phase_raises_not_implemented(self, mock_openai, mock_get_config):
        """Test that _select_action_phase raises NotImplementedError."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        reasoning = Mock()
        
        with pytest.raises(NotImplementedError):
            await agent._select_action_phase(reasoning)

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_action_phase_raises_not_implemented(self, mock_openai, mock_get_config):
        """Test that _action_phase raises NotImplementedError."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        tool = Mock()
        
        with pytest.raises(NotImplementedError):
            await agent._action_phase(tool)


class TestBaseAgentPrepareContext:
    """Tests for context preparation."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_context_basic(self, mock_openai, mock_get_config):
        """Test basic context preparation."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        agent.conversation = [{"role": "user", "content": "test"}]
        
        context = await agent._prepare_context()
        
        assert len(context) == 2  # system + user
        assert context[0]["role"] == "system"
        assert context[1]["role"] == "user"

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_context_with_multiple_messages(self, mock_openai, mock_get_config):
        """Test context preparation with multiple conversation messages."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config
        
        agent = BaseAgent(task="Test")
        agent.conversation = [
            {"role": "user", "content": "message 1"},
            {"role": "assistant", "content": "response 1"},
            {"role": "user", "content": "message 2"}
        ]
        
        context = await agent._prepare_context()
        
        assert len(context) == 4  # system + 3 messages

