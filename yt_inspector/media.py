import urllib.request

from .config import get_float
from .http import get_ssl_context


def fetch_url_bytes(url, max_bytes=450000):
    if not url:
        return None, None
    req = urllib.request.Request(url, headers={"User-Agent": "EMVN-Channel-Inspector/1.0"})
    timeout = get_float("HTTP_TIMEOUT", 20)
    context = get_ssl_context()
    with urllib.request.urlopen(req, context=context, timeout=timeout) as resp:
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None, None
        mime = resp.info().get_content_type() or "image/jpeg"
        return data, mime
