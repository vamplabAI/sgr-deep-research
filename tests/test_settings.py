"""Tests for settings module.

This module contains tests for application configuration using Pydantic
and EnvYAML.
"""

import pytest
from pydantic import ValidationError

from sgr_deep_research.settings import (
    AppConfig,
    ExecutionConfig,
    LoggingConfig,
    MCPConfig,
    OpenAIConfig,
    PromptsConfig,
    ScrapingConfig,
    SearchConfig,
    ServerConfig,
    TavilyConfig,
)


class TestOpenAIConfig:
    """Tests for OpenAIConfig model."""

    def test_openai_config_creation(self):
        """Test creating OpenAI config with valid data."""
        config = OpenAIConfig(
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            max_tokens=8000,
            temperature=0.4,
        )
        assert config.api_key == "sk-test123"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 8000
        assert config.temperature == 0.4

    def test_openai_config_defaults(self):
        """Test OpenAI config default values."""
        config = OpenAIConfig(api_key="sk-test123")
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 8000
        assert config.temperature == 0.4
        assert config.proxy == ""

    def test_openai_config_temperature_validation_low(self):
        """Test temperature validation - too low."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAIConfig(api_key="sk-test", temperature=-0.1)
        assert "greater than or equal to" in str(exc_info.value)

    def test_openai_config_temperature_validation_high(self):
        """Test temperature validation - too high."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAIConfig(api_key="sk-test", temperature=1.1)
        assert "less than or equal to" in str(exc_info.value)

    def test_openai_config_temperature_boundaries(self):
        """Test temperature at valid boundaries."""
        config_min = OpenAIConfig(api_key="sk-test", temperature=0.0)
        assert config_min.temperature == 0.0

        config_max = OpenAIConfig(api_key="sk-test", temperature=1.0)
        assert config_max.temperature == 1.0

    def test_openai_config_required_api_key(self):
        """Test that api_key is required."""
        with pytest.raises(ValidationError):
            OpenAIConfig()

    def test_openai_config_with_proxy(self):
        """Test OpenAI config with proxy."""
        config = OpenAIConfig(
            api_key="sk-test",
            proxy="socks5://127.0.0.1:1081",
        )
        assert config.proxy == "socks5://127.0.0.1:1081"


class TestTavilyConfig:
    """Tests for TavilyConfig model."""

    def test_tavily_config_creation(self):
        """Test creating Tavily config with valid data."""
        config = TavilyConfig(
            api_key="tvly-test123",
            api_base_url="https://api.tavily.com",
        )
        assert config.api_key == "tvly-test123"
        assert config.api_base_url == "https://api.tavily.com"

    def test_tavily_config_default_base_url(self):
        """Test Tavily config default base URL."""
        config = TavilyConfig(api_key="tvly-test123")
        assert config.api_base_url == "https://api.tavily.com"

    def test_tavily_config_required_api_key(self):
        """Test that api_key is required."""
        with pytest.raises(ValidationError):
            TavilyConfig()


class TestSearchConfig:
    """Tests for SearchConfig model."""

    def test_search_config_creation(self):
        """Test creating search config with valid data."""
        config = SearchConfig(max_results=10)
        assert config.max_results == 10

    def test_search_config_defaults(self):
        """Test search config default values."""
        config = SearchConfig()
        assert config.max_results == 10

    def test_search_config_validation_min(self):
        """Test max_results validation - minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(max_results=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_search_config_valid_boundary(self):
        """Test max_results at valid boundary."""
        config = SearchConfig(max_results=1)
        assert config.max_results == 1

    def test_search_config_large_value(self):
        """Test search config with large max_results."""
        config = SearchConfig(max_results=100)
        assert config.max_results == 100


class TestScrapingConfig:
    """Tests for ScrapingConfig model."""

    def test_scraping_config_creation(self):
        """Test creating scraping config with valid data."""
        config = ScrapingConfig(
            enabled=True,
            max_pages=5,
            content_limit=1500,
        )
        assert config.enabled is True
        assert config.max_pages == 5
        assert config.content_limit == 1500

    def test_scraping_config_defaults(self):
        """Test scraping config default values."""
        config = ScrapingConfig()
        assert config.enabled is False
        assert config.max_pages == 5
        assert config.content_limit == 1500

    def test_scraping_config_max_pages_validation(self):
        """Test max_pages validation - must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(max_pages=0)
        assert "greater than 0" in str(exc_info.value)

    def test_scraping_config_content_limit_validation(self):
        """Test content_limit validation - must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(content_limit=0)
        assert "greater than 0" in str(exc_info.value)

    def test_scraping_config_disabled(self):
        """Test scraping config when disabled."""
        config = ScrapingConfig(enabled=False)
        assert config.enabled is False


class TestPromptsConfig:
    """Tests for PromptsConfig model."""

    def test_prompts_config_creation(self):
        """Test creating prompts config with valid data."""
        config = PromptsConfig(
            prompts_dir="custom_prompts",
            system_prompt_file="custom_system.txt",
        )
        assert config.prompts_dir == "custom_prompts"
        assert config.system_prompt_file == "custom_system.txt"

    def test_prompts_config_defaults(self):
        """Test prompts config default values."""
        config = PromptsConfig()
        assert config.prompts_dir == "prompts"
        assert config.system_prompt_file == "system_prompt.txt"


class TestExecutionConfig:
    """Tests for ExecutionConfig model."""

    def test_execution_config_creation(self):
        """Test creating execution config with valid data."""
        config = ExecutionConfig(
            max_steps=10,
            reports_dir="custom_reports",
            logs_dir="custom_logs",
        )
        assert config.max_steps == 10
        assert config.reports_dir == "custom_reports"
        assert config.logs_dir == "custom_logs"

    def test_execution_config_defaults(self):
        """Test execution config default values."""
        config = ExecutionConfig()
        assert config.max_steps == 6
        assert config.reports_dir == "reports"
        assert config.logs_dir == "logs"

    def test_execution_config_max_steps_validation(self):
        """Test max_steps validation - must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionConfig(max_steps=0)
        assert "greater than 0" in str(exc_info.value)

    def test_execution_config_negative_max_steps(self):
        """Test max_steps validation - no negative values."""
        with pytest.raises(ValidationError):
            ExecutionConfig(max_steps=-1)


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_logging_config_creation(self):
        """Test creating logging config with valid data."""
        config = LoggingConfig(config_file="custom_logging.yaml")
        assert config.config_file == "custom_logging.yaml"

    def test_logging_config_defaults(self):
        """Test logging config default values."""
        config = LoggingConfig()
        assert config.config_file == "logging_config.yaml"


class TestMCPConfig:
    """Tests for MCPConfig model."""

    def test_mcp_config_creation(self):
        """Test creating MCP config with valid data."""
        transport = {"mcpServers": {"test_server": {"url": "https://test.com/mcp"}}}
        config = MCPConfig(
            context_limit=20000,
            transport_config=transport,
        )
        assert config.context_limit == 20000
        assert config.transport_config == transport

    def test_mcp_config_defaults(self):
        """Test MCP config default values."""
        config = MCPConfig()
        assert config.context_limit == 15000
        assert config.transport_config == {}

    def test_mcp_config_context_limit_validation(self):
        """Test context_limit validation - must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(context_limit=0)
        assert "greater than 0" in str(exc_info.value)

    def test_mcp_config_negative_context_limit(self):
        """Test context_limit validation - no negative values."""
        with pytest.raises(ValidationError):
            MCPConfig(context_limit=-1)

    def test_mcp_config_empty_transport(self):
        """Test MCP config with empty transport config."""
        config = MCPConfig(transport_config={})
        assert config.transport_config == {}


class TestServerConfig:
    """Tests for ServerConfig model."""

    def test_server_config_creation(self):
        """Test creating server config with valid data."""
        config = ServerConfig(host="127.0.0.1", port=8080)
        assert config.host == "127.0.0.1"
        assert config.port == 8080

    def test_server_config_defaults(self):
        """Test server config default values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8010

    def test_server_config_port_validation_low(self):
        """Test port validation - too low."""
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(port=0)
        assert "greater than 0" in str(exc_info.value)

    def test_server_config_port_validation_high(self):
        """Test port validation - too high."""
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(port=65536)
        assert "less than or equal to 65535" in str(exc_info.value)

    def test_server_config_port_boundaries(self):
        """Test port at valid boundaries."""
        config_min = ServerConfig(port=1)
        assert config_min.port == 1

        config_max = ServerConfig(port=65535)
        assert config_max.port == 65535

    def test_server_config_localhost(self):
        """Test server config with localhost."""
        config = ServerConfig(host="localhost", port=3000)
        assert config.host == "localhost"
        assert config.port == 3000


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_app_config_creation(self):
        """Test creating full app config."""
        config = AppConfig(
            openai=OpenAIConfig(api_key="sk-test"),
            tavily=TavilyConfig(api_key="tvly-test"),
            search=SearchConfig(),
            scraping=ScrapingConfig(),
            execution=ExecutionConfig(),
            prompts=PromptsConfig(),
            logging=LoggingConfig(),
            mcp=MCPConfig(),
        )
        assert config.openai.api_key == "sk-test"
        assert config.tavily.api_key == "tvly-test"
        assert isinstance(config.search, SearchConfig)
        assert isinstance(config.scraping, ScrapingConfig)
        assert isinstance(config.execution, ExecutionConfig)
        assert isinstance(config.prompts, PromptsConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.mcp, MCPConfig)

    def test_app_config_required_fields(self):
        """Test that openai and tavily are required."""
        with pytest.raises(ValidationError):
            AppConfig()

    def test_app_config_with_defaults(self):
        """Test app config with default sub-configs."""
        config = AppConfig(
            openai=OpenAIConfig(api_key="sk-test"),
            tavily=TavilyConfig(api_key="tvly-test"),
        )
        # Check that defaults are initialized
        assert config.search.max_results == 10
        assert config.scraping.enabled is False
        assert config.execution.max_steps == 6
        assert config.prompts.prompts_dir == "prompts"
        assert config.logging.config_file == "logging_config.yaml"
        assert config.mcp.context_limit == 15000

    def test_app_config_custom_values(self):
        """Test app config with custom values for all sub-configs."""
        config = AppConfig(
            openai=OpenAIConfig(api_key="sk-test", model="gpt-4", temperature=0.7),
            tavily=TavilyConfig(api_key="tvly-test"),
            search=SearchConfig(max_results=20),
            scraping=ScrapingConfig(enabled=True, max_pages=10),
            execution=ExecutionConfig(max_steps=15),
            prompts=PromptsConfig(prompts_dir="my_prompts"),
            logging=LoggingConfig(config_file="my_logging.yaml"),
            mcp=MCPConfig(context_limit=20000),
        )
        assert config.openai.model == "gpt-4"
        assert config.openai.temperature == 0.7
        assert config.search.max_results == 20
        assert config.scraping.enabled is True
        assert config.scraping.max_pages == 10
        assert config.execution.max_steps == 15
        assert config.prompts.prompts_dir == "my_prompts"
        assert config.logging.config_file == "my_logging.yaml"
        assert config.mcp.context_limit == 20000
