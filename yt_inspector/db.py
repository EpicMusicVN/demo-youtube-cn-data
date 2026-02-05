import json
import os

import psycopg2


def _get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_channels (
                    channel_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255),
                    custom_url VARCHAR(255),
                    description TEXT,
                    subscriber_count VARCHAR(255),
                    view_count VARCHAR(255),
                    video_count VARCHAR(255),
                    country VARCHAR(255),
                    keywords TEXT,
                    topics TEXT,
                    full_payload TEXT,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                ALTER TABLE saved_channels
                ADD COLUMN IF NOT EXISTS full_payload TEXT
            """)
        conn.commit()
    finally:
        conn.close()


def save_channel(data):
    channel = data.get("channel", {})
    stats = channel.get("statistics", {})
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO saved_channels (
                    channel_id, name, custom_url, description,
                    subscriber_count, view_count, video_count, country,
                    keywords, topics, full_payload, saved_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (channel_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    custom_url = EXCLUDED.custom_url,
                    description = EXCLUDED.description,
                    subscriber_count = EXCLUDED.subscriber_count,
                    view_count = EXCLUDED.view_count,
                    video_count = EXCLUDED.video_count,
                    country = EXCLUDED.country,
                    keywords = EXCLUDED.keywords,
                    topics = EXCLUDED.topics,
                    full_payload = EXCLUDED.full_payload,
                    saved_at = CURRENT_TIMESTAMP
            """, (
                channel.get("id"),
                channel.get("name"),
                channel.get("customUrl"),
                channel.get("description"),
                stats.get("subscriberCount"),
                stats.get("viewCount"),
                stats.get("videoCount"),
                channel.get("country"),
                json.dumps(channel.get("keywords") or []),
                json.dumps(channel.get("topics") or []),
                json.dumps(data),
            ))
        conn.commit()
    finally:
        conn.close()


def get_saved_channels():
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT channel_id, name, custom_url, description,
                       subscriber_count, view_count, video_count, country,
                       keywords, topics, full_payload, saved_at
                FROM saved_channels
                ORDER BY saved_at DESC
            """)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        item = dict(zip(columns, row))
        item["keywords"] = json.loads(item["keywords"]) if item["keywords"] else []
        item["topics"] = json.loads(item["topics"]) if item["topics"] else []
        item["full_payload"] = json.loads(item["full_payload"]) if item["full_payload"] else None
        if item["saved_at"]:
            item["saved_at"] = item["saved_at"].isoformat()
        results.append(item)
    return results


def delete_channel(channel_id):
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM saved_channels WHERE channel_id = %s", (channel_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    return deleted
