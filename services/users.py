"""Gestión de subusuarios de la WebUI (tabla propia webui_users)."""

from database import fetch_all, fetch_one, fetch_scalar, get_connection
from utils.formatting import now_unix
from utils.security import ROLE_LEVELS, hash_password, verify_password

VALID_ROLES = tuple(ROLE_LEVELS.keys())


class UserError(Exception):
    """Error de validación de negocio (nombre duplicado, rol inválido, etc)."""


def list_users():
    return fetch_all(
        "SELECT id, username, role, active, created_at, last_login "
        "FROM webui_users ORDER BY username ASC"
    )


def get_user_by_username(username):
    return fetch_one(
        "SELECT id, username, password_hash, role, active FROM webui_users WHERE username = %s",
        [username],
    )


def get_user_by_id(user_id):
    return fetch_one(
        "SELECT id, username, role, active, created_at, last_login FROM webui_users WHERE id = %s",
        [user_id],
    )


def authenticate(username, password):
    user = get_user_by_username((username or "").strip())
    if not user or not user["active"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def touch_last_login(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE webui_users SET last_login = %s WHERE id = %s", (now_unix(), user_id))
    finally:
        conn.close()


def create_user(username, password, role):
    username = (username or "").strip()
    if not username or len(username) < 3:
        raise UserError("El usuario debe tener al menos 3 caracteres.")
    if role not in VALID_ROLES:
        raise UserError("Rol inválido.")
    if not password or len(password) < 8:
        raise UserError("La contraseña debe tener al menos 8 caracteres.")
    if get_user_by_username(username):
        raise UserError("Ya existe un usuario con ese nombre.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_users (username, password_hash, role, active, created_at) "
                "VALUES (%s, %s, %s, 1, %s)",
                (username, hash_password(password), role, now_unix()),
            )
            return cur.lastrowid
    finally:
        conn.close()


def update_user_role(user_id, role):
    if role not in VALID_ROLES:
        raise UserError("Rol inválido.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE webui_users SET role = %s WHERE id = %s", (role, user_id))
    finally:
        conn.close()


def set_user_active(user_id, active):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE webui_users SET active = %s WHERE id = %s", (1 if active else 0, user_id))
    finally:
        conn.close()


def delete_user(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM webui_users WHERE id = %s", (user_id,))
    finally:
        conn.close()


def change_password(user_id, new_password):
    if not new_password or len(new_password) < 8:
        raise UserError("La contraseña debe tener al menos 8 caracteres.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE webui_users SET password_hash = %s WHERE id = %s",
                (hash_password(new_password), user_id),
            )
    finally:
        conn.close()


def count_admins():
    return fetch_scalar(
        "SELECT COUNT(*) AS total FROM webui_users WHERE role = 'admin' AND active = 1"
    )
