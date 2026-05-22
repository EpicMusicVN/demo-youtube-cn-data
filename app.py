#!/usr/bin/env python3
import os
import time

from flask import Flask, jsonify, redirect, render_template, request, session

from yt_inspector import inspect_channel, inspect_channel_lean
from yt_inspector.comments import fetch_comments
from yt_inspector.config import load_dotenv
from yt_inspector import db

app = Flask(__name__)


def _startup_init():
    load_dotenv()
    for attempt in range(1, 6):
        try:
            db.init_db()
            print("DB init OK.")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: DB init attempt {attempt}/5 failed — {exc}")
            if attempt < 5:
                time.sleep(2)
    print("WARNING: DB init failed after 5 attempts. Saved-channels feature will be unavailable.")


_startup_init()

# Session signing key — set FLASK_SECRET_KEY in production so sessions stay
# stable across restarts and across multiple gunicorn workers.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cnl-secret-page-session-key")


def _secret_access_code():
    return os.environ.get("SECRET_ACCESS_CODE", "83867979")


def _gate(action_url):
    """Shared access-code gate for the restricted pages.

    Returns a response when the visitor is locked out (or just submitted the
    unlock form), or ``None`` when access is granted and the caller may render.
    ``action_url`` is the path the unlock form posts back to.
    """
    if request.method == "POST":
        if request.form.get("code", "").strip() == _secret_access_code():
            session["secret_unlocked"] = True
            return redirect(action_url)
        return render_template(
            "secret_locked.html", error="Incorrect access code.", action_url=action_url
        ), 401
    if not session.get("secret_unlocked"):
        return render_template("secret_locked.html", error=None, action_url=action_url)
    return None


@app.route("/")
def index():
    return render_template("index.html")


# Hidden competitor-analysis page — gated by an access code, not linked anywhere.
@app.route("/secret", methods=["GET", "POST"])
def secret():
    gate = _gate("/secret")
    return gate if gate is not None else render_template("secret.html")


# Comment fetcher — gated by the same access code as /secret.
@app.route("/comments", methods=["GET", "POST"])
def comments_page():
    gate = _gate("/comments")
    return gate if gate is not None else render_template("comments.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/inspect")
def api_inspect():
    target = request.args.get("url", "").strip()
    analysis_param = request.args.get("analysis", "").strip().lower()
    enable_analysis = analysis_param not in ("0", "false", "no", "off")
    lean_param = request.args.get("lean", "").strip().lower()
    lean = lean_param in ("1", "true", "yes", "on")
    # The lean endpoint powers /secret — keep it behind the same access gate.
    if lean and not session.get("secret_unlocked"):
        return jsonify({"error": "Locked. Open /secret and enter the access code."}), 403
    if not target:
        return jsonify({"error": "Missing url parameter."}), 400
    try:
        if lean:
            result = inspect_channel_lean(target, enable_analysis=enable_analysis)
        else:
            result = inspect_channel(target, enable_analysis=enable_analysis)
        return jsonify(result)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/comments")
def api_comments():
    # The comment fetcher lives behind the same access gate as /secret.
    if not session.get("secret_unlocked"):
        return jsonify({"error": "Locked. Open /secret and enter the access code."}), 403
    target = request.args.get("url", "").strip()
    max_results = request.args.get("max", "100").strip()
    order = request.args.get("order", "relevance").strip().lower()
    if not target:
        return jsonify({"error": "Missing url parameter."}), 400
    try:
        result = fetch_comments(target, max_results=max_results, order=order)
        return jsonify(result)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/channels/save", methods=["POST"])
def api_save_channel():
    data = request.get_json()
    if not data or not data.get("channel", {}).get("id"):
        return jsonify({"error": "Missing channel id."}), 400
    db.save_channel(data)
    return jsonify({"status": "saved"})


@app.route("/api/channels/saved")
def api_saved_channels():
    return jsonify(db.get_saved_channels())


@app.route("/api/channels/saved/<channel_id>", methods=["DELETE"])
def api_delete_channel(channel_id):
    if not db.delete_channel(channel_id):
        return jsonify({"error": "Channel not found."}), 404
    return jsonify({"status": "deleted"})


def main():
    load_dotenv()
    try:
        port = int(os.environ.get("PORT", "8080"))
    except ValueError:
        port = 8080
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
