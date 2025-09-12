LiteLLM + Ollama (with airsroute hook)

Overview
- This repo already supports swapping the model backend by setting `openai.base_url`.
- To run a local, OpenAI-compatible gateway in front of your existing Ollama, use LiteLLM’s proxy.
- Optionally, plug in your `airsroute` package for request-based routing. A hook is suggested below.

Quick Start
1) Install dependencies:
   pip install -r requirements.txt

2) Start Ollama (default):
   ollama serve  # ensures http://localhost:11434 is up

3) Start LiteLLM proxy in front of Ollama:
   litellm --config proxy/litellm_config.yaml --host 0.0.0.0 --port 8000

4) Point this app to the proxy:
   - Set `openai.base_url` in `config.yaml` to `http://localhost:8000/v1`
   - Optionally set `openai.api_key` to any non-empty string (LiteLLM checks a key if configured)

Configuration Notes
- Edit `proxy/litellm_config.yaml` to set the actual Ollama model (e.g., `ollama/llama3.1:8b`).
- `api_base` points to your Ollama server. Default is `http://localhost:11434`.
- `master_key` is a simple shared key for the proxy. Use a stronger value in production and pass it as the Bearer token when calling the proxy.

Using With This Project
- No code changes needed; `sgr_streaming.py` already honors `openai.base_url`.
- Example `config.yaml` snippet:
  openai:
    api_key: "dev-key"          # must match proxy master_key if enforced
    model: "research-ollama"     # maps via LiteLLM config model_list
    base_url: "http://localhost:8000/v1"

airsroute Integration (Hook)
- If you want `airsroute` to pick the target model per-request, you have two routes:
  1) LiteLLM Proxy callbacks/middleware: implement a custom callback that alters the model before dispatch based on `airsroute` and expose it via `LITELLM_CALLBACKS` or equivalent proxy config. This keeps full OpenAI-compatible streaming behavior.
  2) Write a thin FastAPI front that:
     - Accepts OpenAI-compatible requests
     - Uses `airsroute` to select a model name
     - Forwards the request to LiteLLM (e.g., set `model` to `ollama/<picked-model>`) and streams back the response

Because `airsroute` is a private package, a generic hook is suggested and left to you to wire up:

Python callback skeleton (for LiteLLM proxy):
"""
# file: proxy/airsroute_callback.py
try:
    import airsroute  # your private routing package
except ImportError:
    airsroute = None

class AirsRouteCallback:
    # Called by LiteLLM proxy before request is sent
    def before_request(self, request_data: dict, **kwargs):
        if airsroute is None:
            return
        try:
            # Example: decide target model based on messages/metadata
            chosen = airsroute.select_model(request_data)
            if chosen:
                # Overwrite requested model with routed target
                request_data["model"] = chosen
        except Exception:
            # Fail open on routing
            pass
"""

Then configure the proxy to load this callback (see LiteLLM docs for `callbacks` config or env hook). If you prefer the thin front approach, create a small FastAPI app that calls `airsroute` then forwards to the LiteLLM proxy.

Verification
- Once the proxy is running, this app should work unchanged. Run:
  python sgr_streaming.py
- The console will show `Base URL: http://localhost:8000/v1` if configured correctly.

Troubleshooting
- If streaming doesn’t show up, confirm you’re hitting the LiteLLM proxy and not Ollama directly.
- If the proxy requires a key, ensure `openai.api_key` matches the proxy `master_key`.
- If `airsroute` is installed but not routing, add logging in your callback to verify it executes.

---

Airsroute Gateway (optional, with dashboard)

Overview
- A thin FastAPI gateway that:
  - Accepts OpenAI-compatible `POST /v1/chat/completions`
  - Uses `airsroute` (if installed) to pick a model per request
  - Forwards the request to LiteLLM proxy and streams back the response
  - Exposes a simple UI with telemetry and config editing

Run
- Install deps: `pip install -r requirements.txt`
- Start: `python -m uvicorn proxy.airsroute_gateway.app:app --reload --port 8010`
- Open: http://localhost:8010/

Config
- File: `proxy/airsroute_gateway/config.yaml`
  - `litellm_base_url`: `http://localhost:8000/v1`
  - `proxy_key`: must match LiteLLM `master_key`
  - `default_model`: used if routing not available
  - `force_routing`: if true, override any incoming `model`
  - `admin_key`: optional; required to edit config via API if set
  - `allow_config_write`: toggles write API
  - `editable_configs`: list of YAML files the dashboard can edit (includes app `config.yaml` by default)

App integration
- Point this project at the gateway instead, if desired:
  - In `config.yaml`, set `openai.base_url: http://localhost:8010/v1`
  - The gateway then forwards to LiteLLM per the gateway config and airsroute logic

Security
- The dashboard/config APIs are protected via `admin_key` if set; otherwise open locally. Use a key in multi-user environments.

