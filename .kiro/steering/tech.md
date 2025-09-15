# Technology Stack & Build System

## Core Technologies

### Language & Runtime
- **Python 3.8+** - Main programming language
- **Type Hints** - Extensive use of typing with Pydantic models
- **Async/Await** - Not used (synchronous architecture)

### Key Dependencies
- **OpenAI SDK** (`openai>=1.0.0`) - LLM integration with structured output support
- **Pydantic** (`pydantic>=2.0.0`) - Schema validation and structured data models
- **Rich** (`rich>=13.0.0`) - Terminal UI, progress bars, and formatting
- **Tavily** (`tavily-python>=0.3.0`) - Web search API integration
- **PyYAML** (`PyYAML>=6.0`) - Configuration file parsing
- **Trafilatura** (`trafilatura>=1.6.0`) - Web scraping and content extraction

### Streaming Version Additional Dependencies
- **annotated-types** (`>=0.6.0`) - Enhanced type annotations
- **LiteLLM** (`litellm>=1.35.0`) - Local model proxy (Ollama integration)
- **FastAPI** (`fastapi>=0.111.0`) - Airsroute gateway functionality
- **Uvicorn** - ASGI server for FastAPI components
- **OpenTelemetry** - Telemetry and monitoring for gateway

## Architecture Patterns

### Schema-First Design
- All LLM interactions use Pydantic models for structured output
- JSON schema validation enforces consistent reasoning patterns
- Type-safe data flow throughout the application
- **SINGLE SOURCE OF TRUTH**: All schemas defined in main `sgr_streaming.py` file only
- **NO DUPLICATE SCHEMAS**: Never create duplicate Pydantic models across files

### Pydantic Model Standards
```python
# ✅ CORRECT: Complete model with all required fields
class WebSearch(BaseModel):
    tool: Literal["web_search"]
    reasoning: str = Field(description="Why this search is needed")
    query: str = Field(description="Search query")
    max_results: int = Field(default=10, description="Maximum results")

# ❌ WRONG: Missing required fields or incomplete model
class WebSearch(BaseModel):
    tool: Literal["web_search"]
    query: str  # Missing other required fields!
```

### Testing Pydantic Models
```python
# ✅ CORRECT: Always create models with ALL required fields
def create_test_websearch():
    return WebSearch(
        tool="web_search",
        reasoning="test reasoning",
        query="test query",
        max_results=5
    )

# ❌ WRONG: Missing required fields causes ValidationError
def create_bad_websearch():
    return WebSearch(tool="web_search", query="test")  # Missing reasoning!
```

### Schema Import Pattern
```python
# ✅ CORRECT: Import from main module
from sgr_streaming import WebSearch, GeneratePlan, CreateReport

# ❌ WRONG: Never duplicate schema definitions
class WebSearch(BaseModel):  # Don't recreate existing schemas!
    pass
```

### Configuration Management
- YAML-based configuration with environment variable fallbacks
- Centralized config loading in `load_config()` function
- API keys support both config file and environment variables
- Local model support via `base_url` configuration (LiteLLM proxy)
- Airsroute integration for dynamic model selection (separate package)

## Common Commands

### Setup & Installation
```bash
# Clone and setup
git clone <repository>
cd sgr-deep-research

# Install classic version
cd sgr-classic
pip install -r requirements.txt

# Install streaming version  
cd sgr-streaming
pip install -r requirements.txt

# Create configuration
cp config.yaml.example config.yaml
# Edit config.yaml with your API keys
```

### Running the System
```bash
# Classic version
cd sgr-classic
python sgr-deep-research.py

# Streaming version
cd sgr-streaming
python sgr_streaming.py

# Streaming demos
python demo_enhanced_streaming.py
python compact_streaming_example.py

# Local model setup (GW -> LiteLLM -> Ollama)
# 1. Start Ollama
ollama serve

# 2. Start LiteLLM proxy
litellm --config proxy/litellm_config.yaml --host 0.0.0.0 --port 8000

# 3. Start airsroute gateway (optional)
python -m uvicorn proxy.airsroute_gateway.app:app --reload --port 8010
```

### Development Commands
```bash
# Code formatting (if using)
black *.py

# Type checking (if using)
mypy *.py

# Testing (if implemented)
pytest
```

## Code Style Conventions

### Import Organization
1. Standard library imports
2. Third-party imports (OpenAI, Pydantic, Rich, etc.)
3. Local module imports
4. Blank lines between groups

### Naming Conventions
- **Classes**: PascalCase (e.g., `SGRStep`, `ResearchPlan`)
- **Functions**: snake_case (e.g., `load_config`, `execute_search`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_TOKENS`)
- **Files**: snake_case (e.g., `sgr_streaming.py`)

### Documentation Style
- Docstrings for all public functions and classes
- Type hints for all function parameters and returns
- Rich console output with proper formatting and panels
## Local
 Model Integration

### Architecture Flow
```
SGR App -> Airsroute Gateway -> LiteLLM Proxy -> Ollama
```

### Known Issues & Troubleshooting

#### JSON Parsing Issues
- **Symptom**: "❌ Failed to parse LLM response" error
- **Root Causes**: 
  1. Model returns simplified schema instead of expected `NextStep` structure
  2. Model generates valid NextStep structure but with incomplete function objects
  3. Model uses complex objects in `remaining_steps` instead of simple strings
  4. Model omits required fields (e.g., missing `reasoning`, `research_goal` for `generate_plan`)
- **Common Patterns**:
  - Simplified: `{"clarification_questions": [...], "actions": []}`
  - Incomplete function: `{"function": {"tool": "generate_plan"}}` (missing required fields)
  - Complex remaining_steps: `[{"action_type": "web_search", "search_query": "..."}]`
- **Debug Steps**:
  1. Enable debug mode: `export SGR_DEBUG_JSON=1`
  2. Check raw logs: `logs/YYYYMMDD_HHMMSS_*_nextstep_simple_parse_raw.txt`
  3. Use validation tool: `python validate_specific_json.py`
  4. Compare expected vs actual JSON structure
- **Solutions**:
  - **Enhanced Coercion**: Handles incomplete NextStep structures and fills missing fields
  - **Multi-layer Fallback**: Structured output → Regular completion → Natural language extraction
  - **Temperature**: Lower to 0.1-0.3 for more consistent structured output
  - **Model Selection**: Use models that handle complex schemas (gemma2:27b, llama3.1:70b)
  - **Prompt Engineering**: System prompt now explicitly requires JSON format

#### Model Configuration
- **Ollama Models**: Use models that support structured output well
- **LiteLLM Mapping**: Update `proxy/litellm_config.yaml` model_list
- **Airsroute**: Separate package for dynamic model routing (optional)

#### Gateway Issues
- **Port Conflicts**: Default ports 8000 (LiteLLM), 8010 (Gateway), 11434 (Ollama)
- **API Keys**: Match `master_key` in LiteLLM config with `proxy_key` in gateway
- **Streaming**: Ensure all components support streaming passthrough
## De
bugging JSON Parsing Failures

### Enable Debug Mode
```bash
export SGR_DEBUG_JSON=1
cd sgr-streaming
python sgr_streaming.py
```

### Common Error Patterns

#### 1. Schema Mismatch
**Error**: `❌ Failed to parse LLM response`
**Cause**: Model returns simplified JSON instead of full NextStep schema
**Example Bad Output**:
```json
{
  "clarification_questions": ["What do you want to research?"],
  "actions": []
}
```
**Expected Output**:
```json
{
  "reasoning_steps": ["User request is unclear"],
  "current_situation": "Need clarification",
  "function": {"tool": "clarification", "questions": ["What do you want to research?"]}
}
```

#### 2. Incomplete JSON
**Cause**: Model stops generating before completing JSON structure
**Solution**: Increase `max_tokens` in config.yaml

#### 3. Invalid JSON Syntax
**Cause**: Model generates malformed JSON (missing quotes, brackets)
**Solution**: Lower temperature, use better model for structured output

### Model Recommendations for Structured Output
- **Best**: `gemma2:27b`, `llama3.1:70b` (high accuracy)
- **Good**: `gemma2:9b`, `llama3.1:8b` (moderate accuracy)
- **Avoid**: Models <7B parameters (poor structured output)

## Pydantic Schema Management

### Common ValidationError Causes & Solutions

#### 1. Missing Required Fields
**Error**: `Field required [type=missing, input_value={...}, input_type=dict]`
**Cause**: Not providing all required fields when creating model instance
**Solution**: Check model definition and provide ALL required fields
```python
# ❌ WRONG: Missing required fields
CreateReport(tool="create_report", title="test")

# ✅ CORRECT: All required fields provided
CreateReport(
    tool="create_report",
    reasoning="test reasoning",
    title="test title", 
    user_request_language_reference="test request",
    content="test content",
    confidence="high"
)
```

#### 2. Invalid Literal Values
**Error**: `Input should be 'high', 'medium' or 'low' [type=literal_error]`
**Cause**: Using wrong value for Literal field
**Solution**: Use exact values from Literal definition
```python
# ❌ WRONG: Invalid literal value
confidence=0.8  # Should be string, not float

# ✅ CORRECT: Valid literal value
confidence="high"  # Must be one of: "high", "medium", "low"
```

#### 3. List Length Validation
**Error**: `List should have at least 3 items after validation [type=too_short]`
**Cause**: List field has MinLen constraint
**Solution**: Provide minimum required items
```python
# ❌ WRONG: Too few items
planned_steps=[]  # MinLen(3) requires at least 3 items

# ✅ CORRECT: Sufficient items
planned_steps=["step1", "step2", "step3"]
```

### Schema Reference Quick Guide

#### All SGR Schemas (from sgr_streaming.py)
```python
# Import all schemas from main module
from sgr_streaming import (
    Clarification,      # Questions for ambiguous requests
    GeneratePlan,       # Research planning
    WebSearch,          # Web search execution
    AdaptPlan,          # Plan adaptation
    CreateReport,       # Report generation
    ReportCompletion,   # Task completion
    NextStep            # Main SGR decision schema
)

# Required fields for each schema:
Clarification(tool="clarification", reasoning="...", unclear_terms=[...], assumptions=[...], questions=[...])
GeneratePlan(tool="generate_plan", reasoning="...", research_goal="...", planned_steps=[...], search_strategies=[...])
WebSearch(tool="web_search", reasoning="...", query="...", max_results=10)
AdaptPlan(tool="adapt_plan", reasoning="...", original_goal="...", new_goal="...", plan_changes=[...], next_steps=[...])
CreateReport(tool="create_report", reasoning="...", title="...", user_request_language_reference="...", content="...", confidence="high|medium|low")
ReportCompletion(tool="report_completion", reasoning="...", completed_steps=[...], status="completed|failed")
```

### Testing Best Practices
1. **Always import schemas**: Never recreate Pydantic models in test files
2. **Use helper functions**: Create reusable model factory functions
3. **Validate early**: Test model creation before using in complex logic
4. **Check field requirements**: Use IDE/editor to see required vs optional fields