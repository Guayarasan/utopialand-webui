"""
Personalización visual (Fase 4), guardada por usuario en la base de
datos. Se valida todo estrictamente antes de guardar porque estos
valores se inyectan luego en un <style> del <head> -- nada de texto
libre sin validar llega a una plantilla.
"""

import json
import re

from database import fetch_one, get_connection
from utils.formatting import now_unix

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

FONT_OPTIONS = {
    "system": '"Segoe UI", Roboto, Inter, Arial, sans-serif',
    "inter": '"Inter", "Segoe UI", sans-serif',
    "poppins": '"Poppins", "Segoe UI", sans-serif',
    "mono": '"JetBrains Mono", "SFMono-Regular", Consolas, monospace',
}

RADIUS_PRESETS = {
    "sm": ("4px", "6px", "10px"),
    "md": ("6px", "10px", "16px"),
    "lg": ("10px", "16px", "22px"),
    "xl": ("14px", "22px", "30px"),
}

DENSITY_PRESETS = {
    "compact": {"cell": "6px 10px", "item": "7px 9px", "font": "13px"},
    "comfortable": {"cell": "10px 14px", "item": "10px 12px", "font": "14px"},
    "spacious": {"cell": "14px 18px", "item": "14px 16px", "font": "15px"},
}

# Multiplicador aplicado a las duraciones de transición/animación base.
ANIM_SPEED_MULT = {"off": 0, "slow": 1.6, "normal": 1, "fast": 0.5}

DEFAULTS = {
    "theme": "dark",
    "primary_color": "#5b8cff",
    "bg_gradient_from": "#5b8cff",
    "bg_gradient_to": "#0f1420",
    "bg_image_url": "",
    "bg_blur": 0,
    "bg_opacity": 20,
    "font_family": "system",
    "radius_scale": "md",
    "density": "comfortable",
    "animations_enabled": True,
    "animation_speed": "normal",
}


def _clamp_int(value, lo, hi, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value))


def validate_settings(raw):
    """Devuelve una copia limpia y segura de `raw` fusionada sobre DEFAULTS.
    Cualquier valor inválido o fuera de rango se descarta silenciosamente
    y se sustituye por el valor por defecto correspondiente (nunca se
    deja pasar texto libre sin validar hacia el <style> generado)."""
    raw = raw or {}
    clean = dict(DEFAULTS)

    theme = raw.get("theme")
    if theme in ("dark", "light"):
        clean["theme"] = theme

    for key in ("primary_color", "bg_gradient_from", "bg_gradient_to"):
        value = raw.get(key)
        if isinstance(value, str) and HEX_RE.match(value):
            clean[key] = value

    bg_image_url = raw.get("bg_image_url")
    if isinstance(bg_image_url, str):
        bg_image_url = bg_image_url.strip()
        if bg_image_url == "" or bg_image_url.startswith(("http://", "https://")):
            clean["bg_image_url"] = bg_image_url[:500]

    clean["bg_blur"] = _clamp_int(raw.get("bg_blur"), 0, 30, DEFAULTS["bg_blur"])
    clean["bg_opacity"] = _clamp_int(raw.get("bg_opacity"), 0, 100, DEFAULTS["bg_opacity"])

    font_family = raw.get("font_family")
    if font_family in FONT_OPTIONS:
        clean["font_family"] = font_family

    radius_scale = raw.get("radius_scale")
    if radius_scale in RADIUS_PRESETS:
        clean["radius_scale"] = radius_scale

    density = raw.get("density")
    if density in DENSITY_PRESETS:
        clean["density"] = density

    clean["animations_enabled"] = bool(raw.get("animations_enabled", DEFAULTS["animations_enabled"]))

    animation_speed = raw.get("animation_speed")
    if animation_speed in ANIM_SPEED_MULT:
        clean["animation_speed"] = animation_speed

    return clean


def get_settings(user_id):
    if not user_id:
        return dict(DEFAULTS)
    row = fetch_one("SELECT settings_json FROM webui_appearance_settings WHERE user_id = %s", [user_id])
    if not row:
        return dict(DEFAULTS)
    try:
        stored = json.loads(row["settings_json"])
    except (TypeError, ValueError):
        stored = {}
    # merge sobre DEFAULTS por si se añaden claves nuevas en el futuro
    merged = dict(DEFAULTS)
    merged.update(validate_settings(stored))
    return merged


def save_settings(user_id, partial):
    current = get_settings(user_id)
    current.update(partial or {})
    clean = validate_settings(current)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_appearance_settings (user_id, settings_json, updated_at) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE settings_json = VALUES(settings_json), updated_at = VALUES(updated_at)",
                (user_id, json.dumps(clean), now_unix()),
            )
    finally:
        conn.close()
    return clean


def reset_settings(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM webui_appearance_settings WHERE user_id = %s", [user_id])
    finally:
        conn.close()
    return dict(DEFAULTS)


def css_variables(settings):
    """Genera los pares CSS custom-property listos para volcar en un <style>."""
    radius = RADIUS_PRESETS[settings["radius_scale"]]
    density = DENSITY_PRESETS[settings["density"]]

    return {
        "--primary": settings["primary_color"],
        "--bg-gradient-from": settings["bg_gradient_from"],
        "--bg-gradient-to": settings["bg_gradient_to"],
        "--radius-sm": radius[0],
        "--radius": radius[1],
        "--radius-lg": radius[2],
        "--density-pad-cell": density["cell"],
        "--density-pad-item": density["item"],
        "--base-font-size": density["font"],
        "--font-family": FONT_OPTIONS[settings["font_family"]],
        "--bg-blur": f"{settings['bg_blur']}px",
        "--bg-opacity": str(settings["bg_opacity"] / 100),
    }
