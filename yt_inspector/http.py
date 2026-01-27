import os
import ssl


def get_ssl_context():
    if os.environ.get("YOUTUBE_SSL_NO_VERIFY") == "1":
        return ssl._create_unverified_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None

