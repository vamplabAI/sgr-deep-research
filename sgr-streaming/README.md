# 🚀 SGR Streaming - Enhanced Schema-Guided Reasoning

Enhanced SGR version with streaming output, animations and extended visualization.

## 📁 Files

### Core Components
- **`sgr_streaming.py`** - main file with streaming support
- **`enhanced_streaming.py`** - enhanced JSON schema streaming module
- **`sgr_visualizer.py`** - SGR process visualizer
- **`sgr_step_tracker.py`** - execution step tracker

### Utilities and Demos
- **`demo_enhanced_streaming.py`** - full feature demonstration
- **`compact_streaming_example.py`** - compact streaming example
- **`scraping.py`** - web scraping utilities

### Configuration
- **`config.yaml`** - configuration file

## 🚀 Usage

```bash
# Navigate to directory
cd sgr-streaming

# Quick setup for local models (recommended)
python configure_for_local_models.py

# Test JSON parsing capabilities
python test_json_parsing.py

# Main streaming system
python sgr_streaming.py

# Feature demonstration
python demo_enhanced_streaming.py

# Compact streaming example
python compact_streaming_example.py
```

## ✨ Features

### 🎨 Visual Enhancements
- ⚡ **Real-time JSON streaming** with animated progress bars
- 🌳 **Interactive schema trees** with field details
- 🎬 **Smooth animations** and color coding
- 📊 **Live performance metrics**

### 📊 Extended Analytics
- 🔍 **Real-time schema detection**
- ⏱️ **Timing metrics** for each step
- 📈 **Parsing statistics** and success rates
- 🎯 **Step grouping** (multiple searches)

### 🔄 SGR Process Monitor
- 📋 **Pipeline visualization** of all SGR steps
- 📚 **Execution history** with results
- 🔄 **Step transitions** with animations
- 📊 **Contextual task information**

### 🛠️ Fixes
- ✅ **Compact panels** - no large gaps after streaming
- ✅ **Proper step grouping** - no planning duplication
- ✅ **Clarification questions display** - correct post-streaming display

## 📋 Configuration

Copy `config.yaml.example` to `config.yaml` and configure:

```yaml
openai:
  api_key: "your-api-key"
  model: "gpt-4o-mini"
  base_url: ""  # Optional for custom endpoints (e.g., LiteLLM proxy http://localhost:8000/v1)
  
tavily:
  api_key: "your-tavily-key"
  
execution:
  max_steps: 6
  reports_dir: "reports"
  # Optional quality knobs
  strict_report_quality: false         # if true, require citations and min words
  min_report_words: 300                # min words to save normal reports
  min_report_words_forced: 150         # min words to save forced final reports
```

## 🧩 LiteLLM + Ollama (optional)

- You can place a LiteLLM proxy in front of your local Ollama to expose an OpenAI-compatible `/v1` API.
- A ready-to-use config is provided at `proxy/litellm_config.yaml`.

Steps:
- Install deps: `pip install -r requirements.txt`
- Run Ollama: `ollama serve` (default: http://localhost:11434)
- Start proxy: `litellm --config proxy/litellm_config.yaml --host 0.0.0.0 --port 8000`
- Set in `config.yaml`:
  - `openai.base_url: http://localhost:8000/v1`
  - `openai.model: research-ollama` (mapped in the proxy config)
  - `openai.api_key: dev-key` (or your master_key)

airsroute integration: see `proxy/README.md` for a callback hook skeleton to let your private `airsroute` package dynamically select the target model per request.

### Airsroute Gateway + Dashboard (optional)

- A thin FastAPI gateway is available at `proxy/airsroute_gateway`.
- It accepts OpenAI-compatible requests, does per-request routing via your `airsroute` package (if installed), forwards to the LiteLLM proxy, and provides a basic telemetry/config UI.

Run gateway:
- `python -m uvicorn proxy.airsroute_gateway.app:app --reload --port 8010`
- Visit http://localhost:8010/ for telemetry and config editing.

Point app at gateway:
- In `config.yaml`, set `openai.base_url: http://localhost:8010/v1`
- `openai.model` can be left as-is; the gateway may override it based on `airsroute` if `force_routing` is enabled.

## 🔧 Requirements

```bash
pip install openai tavily-python pydantic rich annotated-types
```

## 🎯 Demonstrations

### Main Demos
```bash
# Full feature demonstration
python demo_enhanced_streaming.py

# Choose demo:
# 1. JSON Streaming Parser - real-time parsing
# 2. Schema-Specific Displays - specialized displays
# 3. Full SGR Process Monitor - complete SGR monitoring
# 4. All Demos - run all demonstrations
```

### Compact Streaming
```bash
# Compact display solutions demonstration
python compact_streaming_example.py
```

## 🔍 Differences from Classic

| Feature | Classic | Streaming |
|---------|---------|-----------|
| JSON Parsing | Static | Streaming with animation |
| Metrics | Basic | Detailed + timing |
| Visualization | Simple | Interactive |
| SGR Steps | Text output | Visual pipeline |
| Display | Large blocks | Compact panels |
| Animations | None | Spinners, progress bars |
| History | Simple log | Grouping + statistics |

## 🐛 Resolved Issues

1. **Large gaps after streaming** ✅
   - Added `expand=False` and fixed panel widths
   
2. **Planning step duplication** ✅
   - Created `SGRStepTracker` for proper tracking
   
3. **Clarification questions not displayed** ✅
   - Added special handling and question display

4. **Schema overlapping Completed block** ✅
   - Added proper spacing and formatting

## 🎨 Visual Examples

When running, you'll see:
- 🌳 **Schema trees** with real-time field progress
- 📊 **Live performance metrics**
- 🎬 **Animated progress bars** for each JSON field
- 🔄 **SGR pipeline** with color-coded steps
- ❓ **Beautiful question panels** for clarification
- 📈 **Compact summaries** without large gaps

---

✨ **Enjoy beautiful and informative SGR streaming!** ✨

## 🛠️ Local Model Setup & Troubleshooting

### Quick Setup
```bash
# 1. Configure for local models
python configure_for_local_models.py

# 2. Test your model's JSON capabilities  
python test_json_parsing.py

# 3. Validate schema requirements
python validate_nextstep_schema.py

# 4. Enable debug mode and run
SGR_DEBUG_JSON=1 python sgr_streaming.py
```

### JSON Parsing Issues

If you see "❌ Failed to parse LLM response":

1. **Enable debug mode**: `export SGR_DEBUG_JSON=1`
2. **Check logs**: Look at `logs/*_nextstep_simple_parse_raw.txt` files
3. **Lower temperature**: Set to 0.1-0.3 in config.yaml
4. **Use better model**: gemma2:27b or llama3.1:70b recommended
5. **Test parsing**: Run `python test_json_parsing.py`

### Model Recommendations

| Model | Quality | Temperature | Max Tokens | Notes |
|-------|---------|-------------|------------|-------|
| gemma2:27b | Best | 0.1 | 16000 | Excellent structured output |
| llama3.1:70b | Best | 0.1 | 16000 | Very capable, slower |
| gemma2:9b | Good | 0.2 | 12000 | Good balance |
| llama3.1:8b | Good | 0.2 | 12000 | Faster, decent quality |

### Debug Files

When `SGR_DEBUG_JSON=1` is set, debug files are saved to `logs/`:
- `*_nextstep_simple_parse_raw.txt` - Raw model output with analysis
- `*_conversation.json` - Full conversation history
- Enhanced error messages with recommendations

### Validation Tools
```bash
# Test schema validation with examples
python validate_nextstep_schema.py

# Validate a specific debug file
python validate_nextstep_schema.py logs/20241212_120000_test_nextstep_simple_parse_raw.txt

# Test model JSON capabilities
python test_json_parsing.py

# Test clarification behavior (should be less aggressive)
python test_clarification_behavior.py
```
## 🎯 Clarification Behavior

The system has been optimized to be less aggressive with clarification requests:

### When Clarification is Used
- **Truly ambiguous requests**: "test", "help", single words
- **Impossible to research**: Completely unclear topics

### When Research Proceeds Directly
- **Clear topics**: "jazz history", "BMW prices", "AI trends 2024"
- **Reasonable requests**: Most research topics with identifiable subjects
- **After one clarification**: Anti-cycling prevents repeated clarification

### Testing Clarification Behavior
```bash
python test_clarification_behavior.py
```

This will test various request types and show whether the system chooses `generate_plan` (good) or `clarification` (potentially too aggressive).### Enh
anced Fallback Mechanisms

The system now includes multiple fallback layers when structured output fails:

1. **Structured Output**: Primary method using `response_format=NextStep`
2. **Regular Completion**: Falls back to regular API with explicit JSON instructions  
3. **Natural Language Extraction**: Extracts questions from natural language responses
4. **Schema Coercion**: Converts simplified formats to valid NextStep objects
5. **Default Generation**: Creates reasonable defaults when all else fails

### Additional Testing Tools
```bash
# Test fallback mechanisms for natural language responses
python test_json_fallback.py

# Test clarification behavior (less aggressive)  
python test_clarification_behavior.py
```

These improvements should resolve the "❌ Failed to parse LLM response" errors by providing robust fallback mechanisms when local models generate natural language instead of structured JSON.
## 🛡️ C
omprehensive Schema Enforcement

### Schema-Guided Reasoning Protection

SGR now includes a **Schema Enforcement Engine** that proactively prevents ALL schema validation failures:

#### Critical Issues Automatically Fixed:
- ✅ **Generated plan with no steps** - Fills empty `planned_steps` with meaningful defaults
- ✅ **Empty required lists** - Pads lists to minimum lengths (reasoning_steps: 2+, questions: 3+, etc.)
- ✅ **Complex objects in simple fields** - Converts `remaining_steps` objects to strings
- ✅ **Missing function fields** - Completes incomplete function objects with all required fields
- ✅ **Wrong data types** - Converts string numbers/booleans to proper types
- ✅ **Empty strings** - Fills required fields with contextually appropriate defaults
- ✅ **Wrong tool names** - Corrects "plan" → "generate_plan", "search" → "web_search"

#### Schema Enforcement Layers:
1. **Data Type Correction** - Fix int/bool/string type mismatches
2. **Structure Validation** - Ensure all NextStep fields exist
3. **Function Completion** - Fill missing function object fields
4. **List Validation** - Pad lists to meet minimum length requirements
5. **String Validation** - Replace empty required strings
6. **Business Logic** - Prevent critical failures like empty plans

### Testing Schema Enforcement
```bash
# Test your specific JSON case
python test_your_specific_case.py

# Test all failure patterns
python test_schema_enforcement.py

# Analyze schema requirements
python schema_enforcement_analysis.py
```

This ensures **Schema-Guided Reasoning** actually guides the system instead of breaking it.
