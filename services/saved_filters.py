"""Filtros favoritos por usuario y por página (tabla propia webui_saved_filters)."""

import json

from database import fetch_all, get_connection
from utils.formatting import now_unix


def list_saved_filters(user_id, page):
    rows = fetch_all(
        "SELECT id, name, filters_json, created_at FROM webui_saved_filters "
        "WHERE user_id = %s AND page = %s ORDER BY created_at DESC",
        [user_id, page],
    )
    for row in rows:
        try:
            row["filters"] = json.loads(row["filters_json"])
        except (TypeError, ValueError):
            row["filters"] = {}
        del row["filters_json"]
    return rows


def save_filter(user_id, page, name, filters_dict):
    name = (name or "").strip()
    if not name:
        raise ValueError("El nombre del filtro no puede estar vacío.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_saved_filters (user_id, page, name, filters_json, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, page, name, json.dumps(filters_dict), now_unix()),
            )
            return cur.lastrowid
    finally:
        conn.close()


def delete_saved_filter(filter_id, user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM webui_saved_filters WHERE id = %s AND user_id = %s",
                (filter_id, user_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()
