import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

from .config import load_dotenv, get_float
from .http import get_ssl_context

API_BASE = "https://www.googleapis.com/youtube/v3"


def api_get(path, params):
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY env var")
    params = dict(params)
    params["key"] = api_key
    url = API_BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    timeout = get_float("HTTP_TIMEOUT", 20)
    context = get_ssl_context()
    try:
        with urllib.request.urlopen(req, context=context, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} error: {body}") from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                "SSL verify failed. For shareable runs, install certifi "
                "(pip install certifi) or run macOS 'Install Certificates.command'. "
                "As a last resort for testing only, set YOUTUBE_SSL_NO_VERIFY=1."
            ) from None
        raise RuntimeError(f"URL error: {e}") from None
