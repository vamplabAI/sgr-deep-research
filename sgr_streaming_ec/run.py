from __future__ import annotations
import argparse, os, yaml
from .llm_adapters import CallableAdapter
from .loop import run, LoopConfig
from .synthesize import report_from_state
import re
from datetime import datetime

def load_config():
    """Load configuration with sensible fallbacks.

    Preference order:
    1) sgr-streaming/config.yaml (version-specific)
    2) config.yaml at repository root
    """
    for config_path in ("sgr-streaming/config.yaml", "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                try:
                    return yaml.safe_load(f) or {}
                except Exception:
                    return {}
    return {}


def _slugify(text: str, max_len: int = 60) -> str:
    """Create a filesystem-friendly slug from text."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("_")
    return slug or "report"


def save_report(content: str, query: str, cfg: dict) -> str:
    """Save report content to the configured reports directory and return the filepath."""
    exec_cfg = (cfg or {}).get("execution", {})
    reports_dir = exec_cfg.get("reports_dir", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = _slugify(query)
    filename = f"{ts}_{name}.md"
    path = os.path.join(reports_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def env_llm(prompt: str, **params):
    from openai import OpenAI
    
    # Load SGR streaming config
    config = load_config()
    openai_config = config.get('openai', {})
    
    # Use config values with environment variable fallbacks
    api_key = openai_config.get('api_key', os.getenv('OPENAI_API_KEY', 'dev-key'))
    base_url = openai_config.get('base_url', os.getenv('OPENAI_BASE_URL', 'http://localhost:8000/v1'))
    model = openai_config.get('model', os.getenv('OPENAI_MODEL', 'sgr-llama2'))
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    # Filter out parameters not supported by OpenAI API format
    # Even with LiteLLM, we need to stick to OpenAI-compatible parameters
    openai_supported_params = {
        'temperature', 'top_p', 'max_tokens', 'frequency_penalty', 
        'presence_penalty', 'stop', 'stream', 'logit_bias', 'user'
    }
    filtered_params = {k: v for k, v in params.items() if k in openai_supported_params}
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":prompt}],
        **filtered_params
    )
    return resp.choices[0].message.content

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--max-steps", type=int, default=8)
    args = ap.parse_args()

    llm = CallableAdapter(env_llm)
    cfg = LoopConfig(max_steps=args.max_steps)
    base_params = {"temperature":0.3, "top_p":0.85, "repetition_penalty":1.12}

    state = run(llm, args.query, cfg, base_params)
    report = report_from_state(state)

    # Always show the report in the console
    print(report)

    # Persist the report to file for later reference
    config = load_config()
    out_path = save_report(report, args.query, config)
    print(f"\nSaved report to: {out_path}")

if __name__ == "__main__":
    main()
