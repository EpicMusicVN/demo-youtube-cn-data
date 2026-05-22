import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .config import load_dotenv, get_float
from .http import get_ssl_context


def _vertex_url(model):
    base = os.environ.get("VERTEX_API_BASE")
    if base:
        if "{model}" in base:
            return base.format(model=model)
        base = base.rstrip("/")
        if base.endswith(":generateContent"):
            return base
        return f"{base}/models/{model}:generateContent"

    project = os.environ.get("VERTEX_PROJECT_ID")
    if project:
        location = os.environ.get("VERTEX_LOCATION", "us-central1")
        return (
            f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
            f"/locations/{location}/publishers/google/models/{model}:generateContent"
        )

    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def vertex_generate(prompt, image_items=None):
    load_dotenv()
    api_key = os.environ.get("VERTEX_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("VERTEX_MODEL", "gemini-3.5-flash")
    url = _vertex_url(model)

    parts = [{"text": prompt}]
    if image_items:
        for label, data, mime in image_items:
            if label:
                parts.append({"text": label})
            if data:
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": mime or "image/jpeg",
                            "data": base64.b64encode(data).decode("ascii"),
                        }
                    }
                )

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            # Gemini 3.x are reasoning models — internal thinking shares this
            # budget, so it must be generous enough to also fit the JSON answer.
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    headers = {"Content-Type": "application/json"}
    if "generativelanguage.googleapis.com" in url:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        if "key" not in query:
            query["key"] = [api_key]
        url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))
    else:
        headers["x-goog-api-key"] = api_key

    def call_api(body_payload):
        req = urllib.request.Request(
            url, data=json.dumps(body_payload).encode("utf-8"), headers=headers, method="POST"
        )
        timeout = get_float("VERTEX_TIMEOUT", 30)
        context = get_ssl_context()
        with urllib.request.urlopen(req, context=context, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = call_api(payload)
    except (TimeoutError, OSError):
        raise RuntimeError("Vertex AI request timed out.") from None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if "responseMimeType" in body or "response_mime_type" in body:
            payload.get("generationConfig", {}).pop("responseMimeType", None)
            data = call_api(payload)
        else:
            raise RuntimeError(f"Vertex AI HTTP {e.code} error: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Vertex AI URL error: {e}") from None

    candidates = data.get("candidates", [])
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return None
    texts = [part.get("text", "") for part in parts if part.get("text")]
    if not texts:
        return None
    return "".join(texts)
