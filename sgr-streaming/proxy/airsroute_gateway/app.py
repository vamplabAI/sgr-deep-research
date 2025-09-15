import asyncio
import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import yaml
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from uuid import uuid4

from .otel import ensure_tracing, tracer


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def save_yaml(path: Path, data: Dict[str, Any]):
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


class GatewayState:
    def __init__(self):
        self.config = load_yaml(CONFIG_PATH)
        self.telemetry = deque(maxlen=500)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0))
        self.subscribers = set()  # set[asyncio.Queue]

    def reload(self):
        self.config = load_yaml(CONFIG_PATH)

    def get(self, key: str, default: Any = None):
        return self.config.get(key, default)

    def admin_key(self) -> str:
        return str(self.config.get("admin_key") or "")


state = GatewayState()


app = FastAPI(title="Airsroute Gateway", version="0.1.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Initialize tracing
ensure_tracing("airsroute-gateway")


def require_admin(request: Request):
    configured = state.admin_key()
    if not configured:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing admin token")
    token = auth.split(" ", 1)[1].strip()
    if token != configured:
        raise HTTPException(status_code=403, detail="Invalid admin token")


def choose_model(request_json: Dict[str, Any]) -> str:
    # Try to delegate to airsroute if present
    try:
        import airsroute  # type: ignore
    except Exception:
        airsroute = None  # type: ignore

    incoming = (request_json or {}).copy()
    force = bool(state.get("force_routing", False))
    fallback = str(state.get("default_model", "research-ollama"))
    requested = str(incoming.get("model") or "")

    if airsroute is not None:
        try:
            routed = airsroute.select_model(incoming)
            if routed:
                return str(routed)
        except Exception:
            pass

    # Fallback behavior
    if requested and not force:
        return requested
    return fallback


def broadcast_event(event: str, payload: Dict[str, Any]):
    payload = dict(payload)
    payload["event"] = event
    try:
        for q in list(state.subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass
    except Exception:
        pass


def add_telemetry(entry: Dict[str, Any]):
    entry["ts"] = datetime.utcnow().isoformat() + "Z"
    state.telemetry.appendleft(entry)
    broadcast_event("telemetry", entry)


def resolve_target_path(target: str) -> Path:
    if target == "gateway":
        return CONFIG_PATH
    target_list = state.get("editable_configs", []) or []
    for item in target_list:
        if item.get("name") == target:
            return (BASE_DIR / Path(item.get("path", ""))).resolve()
    # default to gateway
    return CONFIG_PATH


def summarize_messages(messages: Any) -> Dict[str, Any]:
    try:
        if not isinstance(messages, list):
            return {"summary": "", "messages_count": 0}
        count = len(messages)
        content = ""
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                content = str(m.get("content") or "")
                break
        if not content and messages:
            m0 = messages[-1]
            content = str(m0.get("content")) if isinstance(m0, dict) else ""
        content = (content or "").strip().replace("\n", " ")
        if len(content) > 140:
            content = content[:140] + "…"
        return {"summary": content, "messages_count": count}
    except Exception:
        return {"summary": "", "messages_count": 0}


async def stream_upstream(req_json: Dict[str, Any], auth_header: Optional[str]) -> AsyncGenerator[bytes, None]:
    base_url = str(state.get("litellm_base_url", "http://localhost:8000/v1"))
    headers = {}
    # Always use gateway proxy_key for upstream auth
    proxy_key = state.get("proxy_key")
    if proxy_key:
        headers["Authorization"] = f"Bearer {proxy_key}"

    url = f"{base_url.rstrip('/')}/chat/completions"
    started = datetime.utcnow()
    msg_meta = summarize_messages(req_json.get("messages"))
    chunk_count = 0
    try:
        # stream from upstream
        async with state.client.stream("POST", url, json=req_json, headers=headers) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                add_telemetry({
                    "route": "/v1/chat/completions",
                    "status": "error",
                    "status_code": resp.status_code,
                    "model": str(req_json.get("model") or ""),
                    "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
                    **msg_meta,
                })
                yield body
                return

            # announce streaming start
            add_telemetry({
                "route": "/v1/chat/completions",
                "status": "streaming",
                "model": str(req_json.get("model") or ""),
                "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
                **msg_meta,
            })

            ctype = resp.headers.get("content-type", "")
            if ctype.startswith("text/event-stream"):
                async for line in resp.aiter_lines():
                    if line is None:
                        continue
                    chunk_count += 1
                    # lightweight progress sampling
                    if chunk_count in (1, 10, 50) or (chunk_count % 100 == 0):
                        add_telemetry({
                            "route": "/v1/chat/completions",
                            "status": "progress",
                            "model": str(req_json.get("model") or ""),
                            "chunks": chunk_count,
                            "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
                            **msg_meta,
                        })
                    yield (line + "\n").encode("utf-8")
            else:
                async for chunk in resp.aiter_bytes():
                    if chunk is None:
                        continue
                    chunk_count += 1
                    if chunk_count in (1, 10, 50) or (chunk_count % 100 == 0):
                        add_telemetry({
                            "route": "/v1/chat/completions",
                            "status": "progress",
                            "model": str(req_json.get("model") or ""),
                            "chunks": chunk_count,
                            "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
                            **msg_meta,
                        })
                    yield chunk
    except Exception as e:
        add_telemetry({
            "route": "/v1/chat/completions",
            "status": "error",
            "error": str(e),
            "model": str(req_json.get("model") or ""),
            "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
            **msg_meta,
        })
        raise
    finally:
        add_telemetry({
            "route": "/v1/chat/completions",
            "status": "completed",
            "model": str(req_json.get("model") or ""),
            "chunks": chunk_count,
            "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
            **msg_meta,
        })


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    cfg = state.config
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "config": cfg,
        },
    )


@app.get("/api/telemetry")
async def get_telemetry():
    return JSONResponse({
        "count": len(state.telemetry),
        "items": list(state.telemetry),
    })


def _sse_format(d: Dict[str, Any]) -> bytes:
    try:
        name = d.get("event") or "message"
        data = json.dumps(d, ensure_ascii=False)
    except Exception:
        name = "message"
        data = "{}"
    return f"event: {name}\ndata: {data}\n\n".encode("utf-8")
@app.get("/v1/models")
async def list_models(request: Request):
    # Proxy to LiteLLM /v1/models
    base_url = str(state.get("litellm_base_url", "http://localhost:8000/v1"))
    url = f"{base_url.rstrip('/')}/models"

    headers = {}
    incoming_auth = request.headers.get("Authorization")
    if incoming_auth:
        headers["Authorization"] = incoming_auth
    else:
        proxy_key = state.get("proxy_key")
        if proxy_key:
            headers["Authorization"] = f"Bearer {proxy_key}"

    resp0 = await state.client.get(url, headers=headers)
    data = resp0.content
    return Response(content=data, status_code=resp0.status_code, media_type=resp0.headers.get("content-type", "application/json"))



@app.get("/api/telemetry/stream")
async def telemetry_stream():
    queue: asyncio.Queue = asyncio.Queue()
    state.subscribers.add(queue)

    async def event_gen():
        try:
            # send last N items as bootstrap
            snapshot = list(state.telemetry)
            for item in reversed(snapshot[-50:]):
                yield _sse_format({"event": "telemetry", **item})

            # then live updates + keepalive
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _sse_format(item)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            state.subscribers.discard(queue)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/config")
async def get_config(request: Request):
    target = request.query_params.get("target")
    if target:
        path = resolve_target_path(target)
        return JSONResponse({
            "target": target,
            "path": str(path),
            "config": load_yaml(path),
        })
    return JSONResponse({
        "gateway_config": state.config,
        "editable_configs": state.get("editable_configs", []),
    })


@app.post("/api/config")
async def update_config(request: Request, _=Depends(require_admin)):
    with tracer.start_as_current_span("update_config") as span:
        span.set_attribute("component", "config")
        span.set_attribute("allow_write", bool(state.get("allow_config_write", False)))
    if not bool(state.get("allow_config_write", False)):
        raise HTTPException(status_code=403, detail="Config writing is disabled")

    data = await request.json()
    target = data.get("target", "gateway")
    updates = data.get("updates", {})

    # Resolve target path
    target_path = resolve_target_path(target)

    # Prevent writing outside repo root (rudimentary safety)
    # Project root: ../../ from this file (airsroute_gateway/app.py)
    repo_root = BASE_DIR.parents[2]
    if not str(target_path).startswith(str(repo_root)):
        raise HTTPException(status_code=403, detail="Invalid config path")

    current = load_yaml(target_path)

    # Shallow merge top-level keys
    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="Invalid updates payload")
    current.update(updates)
    save_yaml(target_path, current)

    # Reload gateway config if we modified it
    if target == "gateway" or str(target_path) == str(CONFIG_PATH):
        state.reload()
        broadcast_event("config", {"target": target, "path": str(target_path)})

    return JSONResponse({"status": "ok", "path": str(target_path)})


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    started = datetime.utcnow()
    body = await request.json()
    rid = str(uuid4())

    # Determine model via airsroute or fallback
    chosen_model = choose_model(body)
    body["model"] = chosen_model
    # Sanitize params not supported by some upstreams
    body.pop("response_format", None)

    # Forward to LiteLLM proxy
    base_url = str(state.get("litellm_base_url", "http://localhost:8000/v1"))
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {}
    # Always use gateway proxy_key for upstream auth
    proxy_key = state.get("proxy_key")
    if proxy_key:
        headers["Authorization"] = f"Bearer {proxy_key}"

    stream = bool(body.get("stream"))

    # Prepare summary for telemetry
    msg_meta = summarize_messages(body.get("messages"))

    with tracer.start_as_current_span("chat_completions") as span:
        span.set_attribute("route", "/v1/chat/completions")
        span.set_attribute("selected_model", chosen_model)
        span.set_attribute("stream", stream)
        span.set_attribute("request.id", rid)
        try:
            if stream:
                # Stream back exactly what upstream sends
                upstream = stream_upstream(body, None)
                resp = StreamingResponse(upstream, media_type="text/event-stream")
            else:
                resp0 = await state.client.post(url, json=body, headers=headers)
                data = resp0.content
                # Pass-through status and payload
                add_telemetry({
                    "route": "/v1/chat/completions",
                    "status": "ok" if resp0.status_code == 200 else "error",
                    "status_code": resp0.status_code,
                    "model": chosen_model,
                    "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
                    **msg_meta,
                })
                return Response(content=data, status_code=resp0.status_code, media_type=resp0.headers.get("content-type", "application/json"))
        except Exception as e:
            span.record_exception(e)
            add_telemetry({
                "route": "/v1/chat/completions",
                "status": "error",
                "error": str(e),
                "model": chosen_model,
                "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
                **msg_meta,
            })
            raise

    # Record telemetry for streaming case once it begins
    add_telemetry({
        "route": "/v1/chat/completions",
        "status": "streaming",
        "model": chosen_model,
        "latency_ms": (datetime.utcnow() - started).total_seconds() * 1000.0,
        **msg_meta,
    })
    return resp


# Health
@app.get("/healthz")
async def health():
    return {"ok": True}
