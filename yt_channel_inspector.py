#!/usr/bin/env python3
import json
import sys

from yt_inspector import inspect_channel


def main():
    if len(sys.argv) < 2:
        print("Usage: yt_channel_inspector.py <channel_url_or_id_or_handle>")
        sys.exit(1)

    target = " ".join(sys.argv[1:])
    result = inspect_channel(target)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)
