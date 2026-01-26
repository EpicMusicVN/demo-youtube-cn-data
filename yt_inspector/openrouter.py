import json
import os
import urllib.error
import urllib.request

from .config import load_dotenv, get_float
from .http import get_ssl_context


def openrouter_generate(prompt, image_items=None):
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("OPENROUTER_MODEL", "allenai/molmo-2-8b:free")
    base_url = os.environ.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    parts = [{"type": "text", "text": prompt}]
    if image_items:
        for label, image_url in image_items:
            if label:
                parts.append({"type": "text", "text": label})
            parts.append({"type": "image_url", "image_url": {"url": image_url}})

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": parts}],
        "temperature": 0.2,
        "max_tokens": 700,
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    referer = os.environ.get("OPENROUTER_REFERER")
    title = os.environ.get("OPENROUTER_TITLE")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    timeout = get_float("OPENROUTER_TIMEOUT", get_float("GEMINI_TIMEOUT", 30))

    context = get_ssl_context()
    try:
        with urllib.request.urlopen(req, context=context, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (TimeoutError, OSError):
        raise RuntimeError("OpenRouter request timed out.") from None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {e.code} error: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenRouter URL error: {e}") from None

    choices = data.get("choices", [])
    if not choices:
        return None
    return choices[0].get("message", {}).get("content")
