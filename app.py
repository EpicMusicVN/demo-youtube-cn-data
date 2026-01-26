#!/usr/bin/env python3
import os

from flask import Flask, jsonify, render_template, request

from yt_inspector import inspect_channel
from yt_inspector.config import load_dotenv

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/inspect")
def api_inspect():
    target = request.args.get("url", "").strip()
    analysis_param = request.args.get("analysis", "").strip().lower()
    enable_analysis = analysis_param not in ("0", "false", "no", "off")
    if not target:
        return jsonify({"error": "Missing url parameter."}), 400
    try:
        result = inspect_channel(target, enable_analysis=enable_analysis)
        return jsonify(result)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400


def main():
    load_dotenv()
    try:
        port = int(os.environ.get("PORT", "8080"))
    except ValueError:
        port = 8080
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
