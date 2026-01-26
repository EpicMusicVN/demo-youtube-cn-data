import os


def load_dotenv(path=".env"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                if raw.startswith("export "):
                    raw = raw[len("export "):].strip()
                if "=" not in raw:
                    continue
                key, value = raw.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        return


def get_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def get_float(name, default):
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default
