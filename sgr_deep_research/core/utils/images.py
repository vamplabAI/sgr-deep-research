import base64
import mimetypes
from pathlib import Path

import httpx

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB safety limit


def _is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _is_data_url(value: str) -> bool:
    return value.startswith("data:image/")


def _looks_like_base64(value: str) -> bool:
    # Heuristic: long base64 string without URL markers or path separators
    if _is_http_url(value) or "/" in value or "\\" in value:
        return False
    stripped = value.strip()
    if len(stripped) < 100:  # avoid treating short tokens as images
        return False
    try:
        base64.b64decode(stripped, validate=True)
        return True
    except Exception:
        return False


def _download_image(url: str) -> tuple[bytes, str]:
    """Download image bytes from HTTP(S) with size guard."""
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        if resp.headers.get("content-length"):
            try:
                content_len = int(resp.headers["content-length"])
                if content_len > MAX_IMAGE_SIZE:
                    raise ValueError(f"Remote image too large (>5MB): {content_len} bytes")
            except ValueError:
                pass
        data = resp.content
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError(f"Remote image too large after download (>5MB): {len(data)} bytes")
        mime = resp.headers.get("content-type") or mimetypes.guess_type(url)[0] or "image/png"
        return data, mime


def to_image_part(path_or_url: str) -> dict:
    """Convert a local image path or remote/base64 input to OpenAI-compatible
    image_url part.

    LM Studio vision models often expect base64 in the url field — we
    enforce that by encoding downloaded/loaded data.
    """
    path = Path(path_or_url)
    if path.exists() and path.is_file():
        data = path.read_bytes()
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError(f"Image '{path}' is too large (>5MB)")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        b64 = base64.b64encode(data).decode("utf-8")
        url = f"data:{mime};base64,{b64}"
    else:
        if not path_or_url:
            raise ValueError("Image URL/path is empty")
        if _is_data_url(path_or_url):
            url = path_or_url
        elif _looks_like_base64(path_or_url):
            url = f"data:image/png;base64,{path_or_url}"
        elif _is_http_url(path_or_url):
            data, mime = _download_image(path_or_url)
            b64 = base64.b64encode(data).decode("utf-8")
            url = f"data:{mime};base64,{b64}"
        else:
            # Could be scheme-less local/remote; refuse to avoid LM Studio errors
            raise ValueError(
                "Unsupported image reference. Use a local file path, HTTP(S) URL, or base64-encoded content."
            )

    return {"type": "image_url", "image_url": {"url": url, "detail": "auto"}}
