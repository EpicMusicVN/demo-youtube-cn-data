import os
import ssl
import urllib.error
import urllib.request

from .config import get_float


def get_ssl_context():
    if os.environ.get("YOUTUBE_SSL_NO_VERIFY") == "1":
        return ssl._create_unverified_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def urlopen_json(req, timeout, error_prefix):
    context = get_ssl_context()
    try:
        with urllib.request.urlopen(req, context=context, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (TimeoutError, OSError) as e:
        raise RuntimeError(f"{error_prefix} request timed out.") from None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{error_prefix} HTTP {e.code} error: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"{error_prefix} URL error: {e}") from None


def get_timeout(env_name, default):
    return get_float(env_name, default)
