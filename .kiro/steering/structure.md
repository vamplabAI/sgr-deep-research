# Project Structure & Organization

## Root Directory Layout

```
sgr-deep-research/
├── sgr-classic/          # Classic SGR implementation
├── sgr-streaming/        # Enhanced streaming version
├── .tmp/                 # Temporary files and tests
├── reports/              # Generated research reports (created at runtime)
├── config.yaml.example  # Configuration template
├── config.yaml          # User configuration (gitignored)
├── requirements.txt      # Root-level dependencies
└── README.md            # Main project documentation
```

## Version-Specific Structure

### SGR Classic (`sgr-classic/`)
```
sgr-classic/
├── sgr-deep-research.py  # Main entry point
├── scraping.py          # Web scraping utilities
├── config.yaml.example # Version-specific config template
├── config.yaml         # Version-specific config
├── requirements.txt     # Classic version dependencies
└── README.md           # Classic version documentation
```

### SGR Streaming (`sgr-streaming/`)
```
sgr-streaming/
├── sgr_streaming.py              # Main streaming entry point
├── enhanced_streaming.py         # JSON streaming parser
├── sgr_visualizer.py            # SGR process visualizer
├── sgr_step_tracker.py          # Execution step tracker
├── demo_enhanced_streaming.py   # Feature demonstrations
├── compact_streaming_example.py # Compact display examples
├── scraping.py                  # Web scraping utilities
├── proxy/                       # LiteLLM proxy configuration
├── logs/                        # Runtime logs
├── reports/                     # Generated reports
├── config.yaml.example         # Streaming config template
├── config.yaml                 # Streaming config
├── requirements.txt             # Streaming dependencies
└── README.md                   # Streaming documentation
```

## File Naming Conventions

### Python Files
- **Main entry points**: `sgr_*.py` (e.g., `sgr_streaming.py`)
- **Utility modules**: descriptive names (e.g., `scraping.py`, `enhanced_streaming.py`)
- **Demo files**: `demo_*.py` or `*_example.py`
- **Component modules**: `sgr_<component>.py` (e.g., `sgr_visualizer.py`)

### Configuration Files
- **Templates**: `*.example` suffix (e.g., `config.yaml.example`)
- **Active configs**: Base name without suffix (e.g., `config.yaml`)
- **Version-specific**: Each version maintains its own `config.yaml`

### Generated Files
- **Reports**: `YYYYMMDD_HHMMSS_Task_Name.md` format in `reports/` directory
- **Conversation Logs**: `YYYYMMDD_HHMMSS_*_conversation.json` in `logs/` directory
- **Raw Parse Logs**: `YYYYMMDD_HHMMSS_*_nextstep_simple_parse_raw.txt` for debugging JSON parsing
- **Gateway Logs**: Runtime telemetry and request logs (airsroute gateway)

## Module Organization Patterns

### Core SGR Components
Each version implements these core components:
- **Configuration loading** (`load_config()` function)
- **SGR step definitions** (Pydantic models)
- **Search integration** (Tavily API wrapper)
- **Report generation** (Markdown output)
- **Main execution loop** (SGR pipeline)

### Streaming-Specific Components
- **Enhanced streaming parser** (`enhanced_streaming.py`)
- **Visual components** (`sgr_visualizer.py`, `sgr_step_tracker.py`)
- **Demo and example files** (multiple demonstration scripts)
- **Proxy infrastructure** (`proxy/` directory with LiteLLM and airsroute gateway)
- **Runtime logs** (`logs/` directory with conversation and raw parsing logs)

## Configuration Management

### Hierarchy
1. **Root level**: `config.yaml.example` (shared template)
2. **Version level**: Each version has its own `config.yaml.example`
3. **User level**: Each version creates its own `config.yaml`

### Environment Variables
All configuration supports environment variable overrides:
- `OPENAI_API_KEY`, `TAVILY_API_KEY`
- `OPENAI_MODEL`, `MAX_TOKENS`, `TEMPERATURE`
- `MAX_SEARCH_RESULTS`, `MAX_EXECUTION_STEPS`
- `REPORTS_DIRECTORY`

### Reporting Quality Controls (Streaming)
- `execution.reports_dir` — directory for saved reports.
- `execution.force_final_report` — may trigger a forced final report if early termination is detected.
- Optional knobs (defaults are applied if keys are absent):
  - `execution.strict_report_quality` (bool) — if true, short/missing-citation reports are not saved.
  - `execution.min_report_words` (int) — min words to save normal reports (default 300).
  - `execution.min_report_words_forced` (int) — min words to save forced reports (default 150).

## Development Workflow

### Adding New Features
1. Choose appropriate version (`sgr-classic/` or `sgr-streaming/`)
2. Follow existing naming conventions
3. Update version-specific `requirements.txt` if needed
4. Add documentation to version-specific `README.md`

### Cross-Version Compatibility
- Both versions share the same configuration schema
- Core SGR logic should remain consistent
- Utility modules like `scraping.py` are duplicated but should stay synchronized

### Testing and Demos
- Place test files in `.tmp/` directory
- Demo files go in the respective version directory
- Use descriptive names with `demo_` or `test_` prefixes
- **CRITICAL**: Always import Pydantic models from main module, never recreate them
- **SCHEMA TESTING**: Use helper functions to create valid model instances

### Schema Management Rules
- **Single Source**: All Pydantic schemas live in `sgr_streaming.py` only
- **No Duplication**: Never recreate existing schemas in test files
- **Import Pattern**: `from sgr_streaming import ModelName`
- **Validation**: Always provide ALL required fields when creating model instances#
# Proxy Infrastructure (`sgr-streaming/proxy/`)

### LiteLLM Configuration
```
proxy/
├── litellm_config.yaml      # LiteLLM -> Ollama mapping
└── README.md               # Setup instructions
```

### Airsroute Gateway (Optional)
```
proxy/airsroute_gateway/
├── app.py                  # FastAPI gateway application
├── config.yaml            # Gateway configuration
├── otel.py                # OpenTelemetry setup
├── static/                # Dashboard assets
└── templates/             # Dashboard HTML templates
```

## Debugging Workflow

### JSON Parsing Issues
1. **Enable debug mode**: `export SGR_DEBUG_JSON=1`
2. **Check raw parse logs**: `logs/*_nextstep_simple_parse_raw.txt`
3. **Verify model output**: Compare against expected `NextStep` schema
4. **Test configuration**: Lower temperature (0.1-0.3), increase max_tokens
5. **Model compatibility**: Ensure model supports complex structured output
6. **Schema coercion**: Check if `_coerce_model_json_to_nextstep()` handles the format

### Local Model Flow
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Test LiteLLM proxy: `curl http://localhost:8000/v1/models`
3. Check gateway routing: Dashboard at `http://localhost:8010/`
4. Monitor SGR app logs for base_url configuration
