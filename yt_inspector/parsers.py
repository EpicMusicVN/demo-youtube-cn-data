import re
import shlex
import urllib.parse


def extract_video_id_from_url(u):
    try:
        parsed = urllib.parse.urlparse(u)
    except Exception:
        return None
    qs = urllib.parse.parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        return qs["v"][0]
    if parsed.netloc in ("youtu.be", "www.youtu.be"):
        vid = parsed.path.strip("/")
        return vid or None
    return None


def parse_input_target(target):
    if not target:
        return {}
    target = "".join(str(target).split())
    if target.startswith("UC") and len(target) >= 20:
        return {"channel_id": target}
    if target.startswith("@"):
        return {"handle": target[1:]}

    video_id = extract_video_id_from_url(target)
    if video_id:
        return {"video_id": video_id}

    if "://" not in target:
        return {"handle": target}

    try:
        parsed = urllib.parse.urlparse(target)
    except Exception:
        return {"handle": target}

    path = parsed.path.strip("/")
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return {"handle": target}

    for seg in segments:
        if seg.startswith("@"):
            return {"handle": seg[1:]}

    if segments[0] == "channel" and len(segments) >= 2:
        return {"channel_id": segments[1]}
    if segments[0] == "user" and len(segments) >= 2:
        return {"username": segments[1]}
    if segments[0] == "c" and len(segments) >= 2:
        return {"custom": segments[1]}

    return {"handle": segments[-1]}


def parse_keywords(raw):
    if not raw:
        return []
    try:
        return shlex.split(raw)
    except Exception:
        return raw.split()


def parse_duration_iso8601(duration):
    if not duration:
        return None
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
