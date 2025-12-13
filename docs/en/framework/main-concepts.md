# Main Concepts

This document describes the key entities of the SGR Deep Research Framework.

![SGR Agent Core Concept](../../assets/images/sgr_concept.png)

## Agent

**BaseAgent** — base class for all agents. Defines a three-phase execution cycle: Reasoning Phase → Select Action Phase → Action Phase. Manages state through `ResearchContext`, provides response streaming and clarification handling.

## Tool

**BaseTool** — base class for all tools. Defines a unified interface through the `__call__()` method. All tools are automatically registered through `ToolRegistryMixin` and return results as strings or JSON.

## Config

**AgentConfig** — centralized agent configuration that combines settings:

- **LLMConfig** — language model parameters (API key, model, temperature, tokens)
- **SearchConfig** — search settings (Tavily API, search and result limits)
- **ExecutionConfig** — execution parameters (maximum iterations, clarifications, directories)
- **PromptsConfig** — prompt settings (system prompt, request templates)
- **MCPConfig** — MCP server integration settings

## Definition

**AgentDefinition** — agent definition as a template for creating instances. Includes agent name, base class, toolset, and all settings from `AgentConfig`. Supports loading from YAML files and automatic inheritance of settings from `GlobalConfig`.

## Registry

**Registry** — centralized registries (`AgentRegistry`, `ToolRegistry`) for automatic registration and class lookup. Provides dynamic name-based lookup and type safety through generics.

## Stream

**Streaming** — response streaming for real-time data transmission. Implements an asynchronous queue and is compatible with the OpenAI streaming API format.
