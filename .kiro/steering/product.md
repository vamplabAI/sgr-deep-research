# SGR Deep Research System

## Product Overview

SGR (Schema-Guided Reasoning) Deep Research is an automated research system that uses structured reasoning to conduct comprehensive web research and generate detailed reports. The system forces language models to think through research tasks systematically rather than relying on unpredictable function calling.

## Core Concept

The system addresses the limitation that local models <32B parameters have poor function calling accuracy (2% on BFCL benchmark) by using structured output to force reasoning, then executing deterministically. This approach achieves 100% reliability on simple tasks compared to <35% accuracy with traditional function calling.

## Two Versions Available

- **SGR Classic**: Simple, stable version with basic text output
- **SGR Streaming**: Enhanced version with real-time animations, visual schema trees, and detailed metrics

## Key Capabilities

- Automated research with clarification questions
- Web search integration via Tavily API
- Optional web scraping for full content extraction
- Structured report generation with citations
- Multi-language support with automatic detection
- Schema-guided reasoning pipeline (6 steps: clarification, planning, search, adaptation, reporting, completion)

## Target Use Cases

- Market research and competitive analysis
- Technical research and trend analysis
- Academic research with proper citations
- Product research and pricing analysis