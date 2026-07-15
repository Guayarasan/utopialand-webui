"""
Reglas de alertas (Fase 3: infraestructura preparada, sin envío en vivo).

Lo que esta fase deja construido:
  - CRUD de reglas (tipos de evento + patrón de bloque + URL de webhook
    de Discord guardada para más adelante).
  - `find_matches`: dado un conjunto de reglas, busca coincidencias
    recientes en LOGDATA. Es la pieza que un futuro cron / systemd-timer
    (o el botón "Comprobar ahora" de esta misma página) puede invocar
    para disparar el envío a Discord.
  - `send_discord_notification`: ya tiene la forma exacta que va a
    necesitar (URL + payload), pero **no se llama automáticamente
    todavía**. Activarla es una decisión explícita del administrador
    (llamarla desde `find_matches` o desde un endpoint de cron), tal
    como se pidió.

No se agregó ningún scheduler en segundo plano (Celery, APScheduler,
cron...) para no sumar tecnología nueva sin que el proyecto lo pida
explícitamente. La "comprobación" hoy es manual (bajo demanda, desde
la UI) hasta que se decida cómo automatizarla.
"""

import json
import urllib.error
import urllib.request

from database import fetch_all, get_connection
from services.query_builder import TABLE
from utils.formatting import now_unix

# Plantillas sugeridas en la UI para crear reglas rápido. El usuario
# elige/edita los tipos de evento reales de su servidor (vienen de
# get_distinct_types(), no se inventan aquí) -- esto solo pre-rellena
# el nombre y el patrón de bloque.
RULE_PRESETS = [
    {"name": "Romper beacon", "block_pattern": "%beacon%", "hint_types": ["block_break"]},
    {"name": "Romper obsidiana", "block_pattern": "%obsidian%", "hint_types": ["block_break"]},
    {"name": "Abrir shulker box", "block_pattern": "%shulker%", "hint_types": ["container_open", "open"]},
    {"name": "Abrir hopper", "block_pattern": "%hopper%", "hint_types": ["container_open", "open"]},
    {"name": "Colocar TNT", "block_pattern": "%tnt%", "hint_types": ["block_place"]},
    {"name": "Colocar lava", "block_pattern": "%lava%", "hint_types": ["block_place"]},
    {"name": "Colocar agua", "block_pattern": "%water%", "hint_types": ["block_place"]},
]


def list_rules(user_id):
    return fetch_all(
        "SELECT id, name, event_types, block_pattern, enabled, discord_webhook_url, "
        "last_triggered_at, created_at FROM webui_alert_rules "
        "WHERE user_id = %s ORDER BY created_at DESC",
        [user_id],
    )


def create_rule(user_id, name, event_types, block_pattern, discord_webhook_url):
    name = (name or "").strip()
    if not name:
        raise ValueError("El nombre de la regla no puede estar vacío.")
    event_types = [t.strip() for t in (event_types or []) if t and t.strip()]
    if not event_types:
        raise ValueError("Selecciona al menos un tipo de evento.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_alert_rules "
                "(user_id, name, event_types, block_pattern, enabled, discord_webhook_url, created_at) "
                "VALUES (%s, %s, %s, %s, 1, %s, %s)",
                (user_id, name, ",".join(event_types), (block_pattern or "").strip() or None,
                 (discord_webhook_url or "").strip() or None, now_unix()),
            )
            return cur.lastrowid
    finally:
        conn.close()


def set_rule_enabled(rule_id, user_id, enabled):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE webui_alert_rules SET enabled = %s WHERE id = %s AND user_id = %s",
                (1 if enabled else 0, rule_id, user_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_rule(rule_id, user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM webui_alert_rules WHERE id = %s AND user_id = %s",
                (rule_id, user_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def _rule_matches_sql(rule):
    event_types = [t for t in (rule.get("event_types") or "").split(",") if t]
    if not event_types:
        return None, []
    placeholders = ", ".join(["%s"] * len(event_types))
    clauses = [f"type IN ({placeholders})"]
    params = list(event_types)
    if rule.get("block_pattern"):
        clauses.append("obj_name LIKE %s")
        params.append(rule["block_pattern"])
    return " AND ".join(clauses), params


def preview_matches(rule, hours=24, limit=20):
    """Eventos recientes (últimas `hours` horas) que esta regla habría capturado."""
    where, params = _rule_matches_sql(rule)
    if not where:
        return []
    since = now_unix() - hours * 3600
    sql = f"""
        SELECT id_pk, name, type, obj_name, obj_id, world, pos_x, pos_y, pos_z, time
        FROM {TABLE}
        WHERE {where} AND time >= %s
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, params + [since, limit])


def find_matches(rules, since_seconds_ago=300, limit_per_rule=20):
    """
    Para cada regla habilitada, busca eventos ocurridos desde hace
    `since_seconds_ago` segundos. Pensado para ser invocado
    periódicamente (cron / systemd-timer) una vez se decida activar el
    envío automático a Discord -- hoy no se auto-ejecuta.
    """
    results = []
    for rule in rules:
        if not rule.get("enabled"):
            continue
        matches = preview_matches(rule, hours=since_seconds_ago / 3600, limit=limit_per_rule)
        if matches:
            results.append({"rule": rule, "matches": matches})
    return results


def send_discord_notification(webhook_url, rule_name, event_row):
    """
    Envía un mensaje a un webhook de Discord usando solo la librería
    estándar (sin sumar la dependencia `requests`). No se llama desde
    ningún flujo automático todavía -- queda lista para cuando se
    conecte la Fase de Alertas con Discord de verdad.
    """
    if not webhook_url:
        return False, "Esta regla no tiene webhook de Discord configurado."

    content = (
        f"🔔 **{rule_name}**\n"
        f"Jugador: `{event_row.get('name')}`  ·  Acción: `{event_row.get('type')}`\n"
        f"Objeto: `{event_row.get('obj_name') or event_row.get('obj_id') or '?'}`  ·  "
        f"Mundo: `{event_row.get('world')}`  ·  "
        f"Coords: `{event_row.get('pos_x')}, {event_row.get('pos_y')}, {event_row.get('pos_z')}`"
    )
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300, None
    except urllib.error.URLError as exc:
        return False, str(exc)
