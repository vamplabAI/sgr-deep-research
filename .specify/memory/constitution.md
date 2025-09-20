<!--
Sync Impact Report:
- Version change: [CONSTITUTION_VERSION] → 1.0.0
- New constitution creation for SGR Deep Research system
- Added principles: I. Schema-Guided Reasoning, II. Agent Architecture, III. Production-Ready API, IV. Open Source Community, V. Research Quality
- Added sections: Quality Standards, Development Workflow
- Templates requiring updates: ✅ all existing templates compatible
- Follow-up TODOs: None - all placeholders filled
-->

# SGR Deep Research Constitution

## Core Principles

### I. Schema-Guided Reasoning First
Every research agent MUST use structured schemas to guide reasoning decisions; Structured Output enforces decision-making patterns regardless of model size; SGR schemas MUST be deterministic and enable transparent reasoning traces; Function Calling may supplement SGR but cannot replace core reasoning structure.

**Rationale**: SGR enables smaller models to perform complex reasoning by forcing structured decision-making, unlike pure Function Calling which fails on models <32B parameters.

### II. Multi-Agent Architecture
System MUST support multiple agent types (sgr, sgr-tools, sgr-auto-tools, sgr-so-tools, tools-agent); Each agent type MUST implement base agent interface with consistent state management; Agent interruption and clarification flows MUST be supported across all agent types; No single agent implementation may dominate - flexibility is required.

**Rationale**: Different models and use cases require different reasoning approaches. A single architecture cannot optimally serve both small local models and large commercial models.

### III. OpenAI-Compatible API (NON-NEGOTIABLE)
API MUST implement OpenAI chat completions standard with streaming support; Agent state MUST persist through agent_id in model field; Clarification requests MUST use standard tool_calls format; All endpoints MUST maintain backward compatibility with OpenAI client libraries.

**Rationale**: Standard API ensures broad compatibility and easy integration with existing tools and workflows.

### IV. Open Source Community Standards
All development MUST be open source with MIT license; Community contributions MUST be welcomed and properly attributed; Documentation MUST be comprehensive and accessible to all skill levels; No proprietary dependencies may be required for core functionality.

**Rationale**: Open source development ensures transparency, community ownership, and prevents vendor lock-in for critical research infrastructure.

### V. Research Quality and Reproducibility
All research outputs MUST include complete source citations and timestamps; Research methods MUST be transparent and reproducible; Deep research modes MUST scale deterministically with clear performance expectations; Batch processing MUST maintain research quality across parallel executions.

**Rationale**: Research integrity requires transparent methods and reproducible results for scientific and professional credibility.

## Quality Standards

Research reports MUST include executive summary, technical analysis, key findings, and complete source references; All agents MUST support both streaming and non-streaming response modes; Configuration MUST support multiple LLM providers (OpenAI, Azure OpenAI) with seamless switching; Error handling MUST provide actionable feedback without exposing internal implementation details.

## Development Workflow

All changes MUST include comprehensive tests using pytest framework; Code formatting MUST use Ruff with 120-character line limits and consistent import ordering; CLI functionality MUST be tested in both interactive and batch modes; Documentation updates MUST accompany any API or CLI changes; Docker deployment MUST remain functional with all configuration changes.

## Governance

Constitution supersedes all other development practices and coding guidelines; All feature development MUST verify compliance with these principles before implementation; Complexity that violates these principles MUST be justified with specific business requirements; Community feedback on constitutional amendments MUST be solicited through GitHub issues; AGENTS.md provides runtime development guidance and MUST remain aligned with constitutional principles.

**Version**: 1.0.0 | **Ratified**: 2025-01-21 | **Last Amended**: 2025-01-21