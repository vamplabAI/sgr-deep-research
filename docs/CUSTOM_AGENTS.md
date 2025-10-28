# Custom Agents Configuration Guide

## Overview

SGR Deep Research supports dynamic agent creation through YAML configuration files. This allows you to define custom agents with specific tools, prompts, and execution parameters without modifying code.

## Quick Start

### 1. Create Agent Configuration

Create a file `agents_config.yaml` or add agents inline in `config.yaml`:

```yaml
agents:
  - name: "my_research_agent"
    display_name: "My Research Agent"
    description: "Custom agent for specific research tasks"
    base_class: "SGRResearchAgent"
    tools:
      - "WebSearchTool"
      - "CreateReportTool"
      - "FinalAnswerTool"
```

### 2. Reference in Main Config

In `config.yaml`, add:

```yaml
agents:
  config_file: "agents_config.yaml"  # Load from separate file
  # OR define inline:
  # agents:
  #   - name: "inline_agent"
  #     ...
```

### 3. Use via API

```bash
curl -X POST http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "my_research_agent",
    "messages": [{"role": "user", "content": "Research topic X"}],
    "stream": true
  }'
```

## Configuration Reference

### Agent Definition

```yaml
name: string                    # Required: Unique agent identifier
display_name: string           # Optional: Human-readable name
description: string            # Optional: Agent description
base_class: string             # Required: Base agent class name
openai: object                 # Optional: OpenAI configuration override
prompts: object                # Optional: Custom prompts configuration
context: object                # Optional: Execution context settings
tools: list[string]            # Required: List of tool names
```

### Base Classes

Available base classes:

- `BaseAgent` - Minimal base class (requires custom implementation)
- `SGRResearchAgent` - Full SGR research agent with planning
- `SGRToolCallingResearchAgent` - SGR with native function calling
- `SGRAutoToolCallingResearchAgent` - Auto tool selection variant
- `ToolCallingResearchAgent` - Pure function calling agent
- `SGRSOToolCallingResearchAgent` - Streaming-optimized variant

### OpenAI Configuration Override

```yaml
openai:
  api_key: "custom-api-key"           # Optional
  base_url: "https://api.custom.com"  # Optional
  model: "gpt-4o"                     # Optional
  max_tokens: 8000                    # Optional
  temperature: 0.3                    # Optional
  proxy: "http://proxy:8080"          # Optional
```

All fields are optional and will inherit from global config if not specified.

### Custom Prompts

```yaml
prompts:
  system_prompt_file: "prompts/custom_system.txt"
  initial_user_request_file: "prompts/custom_initial.txt"
  clarification_response_file: "prompts/custom_clarification.txt"
```

Prompt files are relative to the working directory.

### Execution Context

```yaml
context:
  max_iterations: 15        # Maximum execution iterations
  max_clarifications: 5     # Maximum clarification requests
  max_searches: 6           # Maximum search operations
```

### Available Tools

Standard tools that can be included:

- `WebSearchTool` - Web search via Tavily
- `ExtractPageContentTool` - Extract content from URLs
- `CreateReportTool` - Generate research reports
- `ClarificationTool` - Request user clarification
- `GeneratePlanTool` - Generate research plan
- `AdaptPlanTool` - Adapt existing plan
- `FinalAnswerTool` - Provide final answer
- `ReasoningTool` - Structured reasoning

Plus any MCP tools loaded from MCP servers.

## Examples

### Example 1: Fast Research Agent

```yaml
- name: "fast_researcher"
  display_name: "Fast Research Agent"
  description: "Quick research with minimal iterations"
  base_class: "SGRToolCallingResearchAgent"

  openai:
    model: "gpt-4o-mini"
    temperature: 0.1

  context:
    max_iterations: 8
    max_clarifications: 2
    max_searches: 3

  tools:
    - "WebSearchTool"
    - "CreateReportTool"
    - "FinalAnswerTool"
```

### Example 2: Deep Analysis Agent

```yaml
- name: "deep_analyst"
  display_name: "Deep Analysis Agent"
  description: "Thorough research with extended capabilities"
  base_class: "SGRResearchAgent"

  prompts:
    system_prompt_file: "prompts/deep_analysis_system.txt"

  context:
    max_iterations: 20
    max_clarifications: 5
    max_searches: 10

  tools:
    - "WebSearchTool"
    - "ExtractPageContentTool"
    - "CreateReportTool"
    - "ClarificationTool"
    - "GeneratePlanTool"
    - "AdaptPlanTool"
    - "FinalAnswerTool"
```

### Example 3: Specialized Domain Agent

```yaml
- name: "technical_analyst"
  display_name: "Technical Documentation Analyst"
  description: "Specialized in technical documentation analysis"
  base_class: "SGRResearchAgent"

  openai:
    model: "gpt-4o"
    temperature: 0.2

  prompts:
    system_prompt_file: "prompts/technical_analyst.txt"

  context:
    max_iterations: 15
    max_clarifications: 3
    max_searches: 8

  tools:
    - "WebSearchTool"
    - "ExtractPageContentTool"
    - "CreateReportTool"
    - "ClarificationTool"
    - "FinalAnswerTool"
```

## API Integration

### List Available Agents

```bash
curl http://localhost:8010/v1/models
```

Returns both built-in and custom agents.

### Create Chat with Custom Agent

```bash
curl -X POST http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_custom_agent_name",
    "messages": [
      {"role": "user", "content": "Your research query"}
    ],
    "stream": true
  }'
```

### Check Agent State

```bash
curl http://localhost:8010/agents/{agent_id}/state
```

## Tool Registry

The tool registry is integrated into `BaseTool` and automatically registers all tool subclasses when they are defined via `__init_subclass__`. This means:

- All standard tools are registered when imported
- MCP tools are registered when dynamically created
- Custom tools are registered when defined

No manual registration is needed!

### Checking Available Tools

Tools are registered automatically when their classes are defined. You can check registered tools in the startup logs:

```
INFO - Application initialized successfully
INFO - Registered tools: 15
INFO - Registered custom agents: 2
```

## Best Practices

1. **Start Simple**: Begin with a basic agent configuration and add complexity as needed
2. **Tool Selection**: Only include tools your agent actually needs
3. **Iteration Limits**: Set appropriate limits based on task complexity
4. **Custom Prompts**: Use custom prompts for specialized domains
5. **Testing**: Test agents with simple queries before production use
6. **Naming**: Use descriptive, unique names for agents
7. **Documentation**: Document custom agents and their intended use cases

## Troubleshooting

### Agent Not Found

- Check agent name is correct and unique
- Verify agents config file is loaded (check logs)
- Ensure config file path is correct in main config

### Tool Not Found

- Verify tool name matches registered tools exactly
- Check tool is imported and registered at startup
- Review startup logs for tool registration

### Configuration Errors

- Validate YAML syntax
- Check all required fields are present
- Review logs for specific error messages

### Custom Prompts Not Loading

- Verify file paths are correct (relative to working directory)
- Check file permissions
- Ensure files exist and are readable

## Advanced Usage

### Dynamic Tool Loading

Tools from MCP servers are automatically registered and available to custom agents:

```yaml
tools:
  - "WebSearchTool"
  - "mcp_custom_tool"  # MCP tool name
```

### Multiple Configurations

You can maintain multiple agent configuration files:

```yaml
# config.yaml
agents:
  config_file: "agents_production.yaml"

# agents_production.yaml
agents:
  - name: "prod_agent_1"
    ...
  - name: "prod_agent_2"
    ...
```

### Environment-Specific Agents

Use different config files per environment:

- `agents_development.yaml`
- `agents_staging.yaml`
- `agents_production.yaml`

## Migration from Hardcoded Agents

To migrate existing hardcoded agents to configuration:

1. Identify agent parameters (tools, iterations, etc.)
2. Create agent definition in YAML
3. Test with same queries
4. Gradually transition to config-based approach

## See Also

- [Main Configuration Guide](../README.md)
- [API Documentation](../docs/API.md)
- [Tool Development Guide](../docs/TOOLS.md)
- [Example Configurations](../agents_config.yaml.example)
