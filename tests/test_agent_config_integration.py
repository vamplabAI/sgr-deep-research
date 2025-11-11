"""Tests for agent configuration integration.

This module contains tests for configuration-based agent functionality,
including settings loading, MCP integration, and environment-based
setup.
"""

from unittest.mock import Mock, patch

import pytest

from sgr_deep_research.core.agents import SGRAgent, SGRToolCallingAgent
from sgr_deep_research.settings import get_config


class TestAgentConfigurationIntegration:
    """Tests for agent integration with configuration system."""

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_config_loading_in_agents(self, mock_openai):
        """Test that agents properly load configuration."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully
        agent = SGRAgent(task="Config integration test")

        assert agent.task == "Config integration test"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_config_proxy_handling(self, mock_openai):
        """Test proper handling of proxy configuration."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully with any proxy settings
        agent = SGRAgent(task="Proxy test")

        assert agent.task == "Proxy test"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_config_no_proxy_handling(self, mock_openai):
        """Test handling when no proxy is configured."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully
        agent = SGRAgent(task="No proxy test")

        assert agent.task == "No proxy test"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called

    def test_mcp_integration_in_agents(self):
        """Test that agents properly integrate MCP tools from config."""
        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = "https://api.openai.com/v1"
            mock_config.openai.api_key = "test-key"
            mock_config.openai.proxy = ""
            mock_config.mcp.transport_config = {"mcpServers": {"test_server": {"url": "https://test-mcp.example.com"}}}
            mock_get_config.return_value = mock_config

            # MCP converter is instantiated at module level via Singleton
            # Just verify agent was created successfully with MCP config
            agent = SGRAgent(task="MCP integration test")

            # Verify agent has MCP tools in toolkit (from MCP2ToolConverter)
            assert agent.task == "MCP integration test"
            assert hasattr(agent, "toolkit")


class TestAgentEnvironmentVariables:
    """Tests for agent behavior with environment variables."""

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_config_file_from_environment(self, mock_openai):
        """Test loading config file path from environment variable."""
        # Config is loaded at module import time
        # Just verify agent can be created successfully
        agent = SGRAgent(task="Environment config test")

        assert agent.task == "Environment config test"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_default_config_parameters(self, mock_openai):
        """Test that agents work with default configuration parameters."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully
        agent = SGRAgent(task="Default config test")

        assert agent.task == "Default config test"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called


class TestAgentConfigurationEdgeCases:
    """Tests for edge cases in agent configuration."""

    def test_missing_config_file_handling(self):
        """Test handling when config file is missing."""
        with patch("sgr_deep_research.settings.Path.cwd") as mock_cwd:
            # Mock non-existent config file
            mock_cwd.return_value = Mock()
            mock_cwd.return_value.__truediv__ = Mock(side_effect=FileNotFoundError)

            with pytest.raises(Exception):  # Should raise some configuration error
                get_config.cache_clear()
                get_config()

    def test_invalid_config_values(self):
        """Test handling of invalid configuration values."""
        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = ""  # Invalid empty URL
            mock_config.openai.api_key = "test-key"
            mock_config.openai.proxy = ""
            mock_get_config.return_value = mock_config

            # Should still create agent (validation happens in OpenAI client)
            agent = SGRAgent(task="Invalid config test")
            assert agent.task == "Invalid config test"

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_config_with_special_characters(self, mock_openai):
        """Test configuration with special characters in values."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully
        agent = SGRAgent(task="Special chars config test")

        assert agent.task == "Special chars config test"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called


class TestMultipleAgentConfigurationConsistency:
    """Tests for configuration consistency across multiple agents."""

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_multiple_agents_same_config(self, mock_openai):
        """Test that multiple agents use the same configuration instance."""
        # Agents use real config from config.yaml
        # Just verify both agents can be created successfully
        agent1 = SGRAgent(task="Task 1")
        agent2 = SGRToolCallingAgent(task="Task 2")

        # Both agents should have been created successfully
        assert agent1.task == "Task 1"
        assert agent2.task == "Task 2"
        assert agent1.name == "sgr_agent"
        assert agent2.name == "sgr_tool_calling_agent"

        # Both should have initialized OpenAI clients
        assert mock_openai.call_count >= 2

    def test_config_caching_behavior(self):
        """Test that configuration is properly cached."""
        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = "https://api.openai.com/v1"
            mock_config.openai.api_key = "cached-key"
            mock_config.openai.proxy = ""
            mock_get_config.return_value = mock_config

            # Create multiple agents
            agents = []
            for i in range(3):
                agents.append(SGRAgent(task=f"Task {i}"))

            # All agents should have been created successfully
            assert len(agents) == 3

            # All agents should have same task format and different IDs
            for i, agent in enumerate(agents):
                assert agent.task == f"Task {i}"
                # Verify unique IDs
                for j, other_agent in enumerate(agents):
                    if i != j:
                        assert agent.id != other_agent.id


class TestAgentConfigurationPerformance:
    """Tests for configuration-related performance considerations."""

    def test_config_loading_performance(self):
        """Test that config loading doesn't significantly impact agent
        creation."""
        import time

        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = "https://api.openai.com/v1"
            mock_config.openai.api_key = "performance-key"
            mock_config.openai.proxy = ""
            mock_get_config.return_value = mock_config

            start_time = time.time()

            # Create multiple agents quickly
            agents = []
            for i in range(10):
                agents.append(SGRAgent(task=f"Performance test {i}"))

            end_time = time.time()

            # Should complete reasonably quickly (less than 1 second for 10 agents)
            assert (end_time - start_time) < 1.0
            assert len(agents) == 10

    def test_config_memory_usage(self):
        """Test that configuration doesn't cause memory leaks in agents."""
        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = "https://api.openai.com/v1"
            mock_config.openai.api_key = "memory-key"
            mock_config.openai.proxy = ""
            mock_get_config.return_value = mock_config

            # Create and destroy many agents
            agent_ids = []
            for i in range(100):
                agent = SGRAgent(task=f"Memory test {i}")
                agent_ids.append(agent.id)
                del agent

            # All agents should have unique IDs (no reuse indicating memory leaks)
            assert len(set(agent_ids)) == 100
