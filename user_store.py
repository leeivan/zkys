# user_store.py
import hashlib
import json
import os
import re
import secrets
import shutil
import uuid
from datetime import datetime, timedelta

from prompt_config import DEFAULT_PROMPT_TEMPLATES

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_DIR = os.path.join(DATA_DIR, "users")
AUTH_SESSIONS_PATH = os.path.join(DATA_DIR, "auth_sessions.json")
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000
PASSWORD_MIN_LENGTH = 6
AUTH_SESSION_DAYS = 30
SENSITIVE_PROFILE_FIELDS = {"password_hash"}

def _now_iso():
    return datetime.now().isoformat(timespec="seconds")

def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except (OSError, json.JSONDecodeError):
        return default

def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)
        json_file.write("\n")

def _parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

def _normalize_username(username):
    return "" if username is None else str(username).strip()

def _validate_username(username):
    username = _normalize_username(username)
    if not username:
        raise ValueError("用户名不能为空")
    if len(username) > 40:
        raise ValueError("用户名不能超过 40 个字符")
    return username

def _validate_password(password):
    password = "" if password is None else str(password)
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"密码至少需要 {PASSWORD_MIN_LENGTH} 位")
    return password

def _hash_password(password):
    password = _validate_password(password)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${digest}"

def _verify_password(password, stored_hash):
    if not password or not isinstance(stored_hash, str):
        return False

    try:
        algorithm, iterations, salt, expected_digest = stored_hash.split("$", 3)
        iterations = int(iterations)
    except (ValueError, TypeError):
        return False

    if algorithm != PASSWORD_ALGORITHM or iterations <= 0:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return secrets.compare_digest(digest, expected_digest)

def _public_profile(profile):
    if not isinstance(profile, dict):
        return None

    public_profile = {
        key: value
        for key, value in profile.items()
        if key not in SENSITIVE_PROFILE_FIELDS
    }
    public_profile["has_password"] = bool(profile.get("password_hash"))
    public_profile["is_admin"] = bool(profile.get("is_admin"))
    return public_profile

def make_user_id(username):
    username = _normalize_username(username)
    digest = hashlib.sha256(username.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", username).strip("_").lower()
    if not slug:
        slug = "user"
    return f"{slug[:40]}_{digest}"

def _user_dir(user_id):
    return os.path.join(USERS_DIR, user_id)

def _profile_path(user_id):
    return os.path.join(_user_dir(user_id), "profile.json")

def _templates_path(user_id):
    return os.path.join(_user_dir(user_id), "prompt_templates.json")

def _graphs_path(user_id):
    return os.path.join(_user_dir(user_id), "knowledge_graphs.json")

def _safe_user_dir(user_id):
    base_dir = os.path.abspath(USERS_DIR)
    target_dir = os.path.abspath(_user_dir(user_id))
    if os.path.commonpath([base_dir, target_dir]) != base_dir:
        raise ValueError("用户目录无效")
    return target_dir

def _list_private_profiles():
    if not os.path.exists(USERS_DIR):
        return []

    profiles = []
    for user_id in os.listdir(USERS_DIR):
        profile = _read_json(_profile_path(user_id), None)
        if isinstance(profile, dict) and profile.get("id"):
            profiles.append(profile)
    return profiles

def _admin_count():
    return sum(1 for profile in _list_private_profiles() if profile.get("is_admin"))

def has_admin_user():
    return _admin_count() > 0

def _ensure_user_profile(username):
    username = _validate_username(username)
    user_id = make_user_id(username)
    user_dir = _user_dir(user_id)
    os.makedirs(user_dir, exist_ok=True)

    profile = _read_json(_profile_path(user_id), {})
    profile.update({
        "id": user_id,
        "username": username,
        "updated_at": _now_iso(),
    })
    profile.setdefault("created_at", profile["updated_at"])
    _write_json(_profile_path(user_id), profile)

    if not os.path.exists(_templates_path(user_id)):
        save_user_prompt_templates(user_id, DEFAULT_PROMPT_TEMPLATES)

    if not os.path.exists(_graphs_path(user_id)):
        _write_json(_graphs_path(user_id), [])

    return profile

def ensure_user(username):
    return _public_profile(_ensure_user_profile(username))

def get_user(username):
    username = _normalize_username(username)
    if not username:
        return None
    return _public_profile(_read_json(_profile_path(make_user_id(username)), None))

def get_user_by_id(user_id):
    return _public_profile(_read_json(_profile_path(user_id), None))

def _session_token_hash(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

def _read_auth_sessions():
    sessions = _read_json(AUTH_SESSIONS_PATH, {})
    if not isinstance(sessions, dict):
        return {}
    return sessions

def _write_auth_sessions(sessions):
    _write_json(AUTH_SESSIONS_PATH, sessions)

def create_auth_session(user_id):
    if not get_user_by_id(user_id):
        raise ValueError("用户不存在")

    token = secrets.token_urlsafe(32)
    now = _now_iso()
    sessions = _read_auth_sessions()
    sessions[_session_token_hash(token)] = {
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
    }
    _write_auth_sessions(sessions)
    return token

def get_auth_session_user(token):
    if not token:
        return None

    sessions = _read_auth_sessions()
    token_hash = _session_token_hash(token)
    session = sessions.get(token_hash)
    if not isinstance(session, dict):
        return None

    created_at = _parse_iso(session.get("created_at"))
    if not created_at or datetime.now() - created_at > timedelta(days=AUTH_SESSION_DAYS):
        sessions.pop(token_hash, None)
        _write_auth_sessions(sessions)
        return None

    user = get_user_by_id(session.get("user_id"))
    if not user:
        sessions.pop(token_hash, None)
        _write_auth_sessions(sessions)
        return None

    session["updated_at"] = _now_iso()
    sessions[token_hash] = session
    _write_auth_sessions(sessions)
    return user

def delete_auth_session(token):
    if not token:
        return

    sessions = _read_auth_sessions()
    sessions.pop(_session_token_hash(token), None)
    _write_auth_sessions(sessions)

def create_user(username, password):
    username = _validate_username(username)
    password_hash = _hash_password(password)
    user_id = make_user_id(username)
    existing_profile = _read_json(_profile_path(user_id), None)

    if isinstance(existing_profile, dict) and existing_profile.get("password_hash"):
        raise ValueError("用户已存在，请直接登录")

    profile = _ensure_user_profile(username)
    now = _now_iso()
    profile.update({
        "password_hash": password_hash,
        "is_admin": bool(profile.get("is_admin")) or not has_admin_user(),
        "password_updated_at": now,
        "updated_at": now,
    })
    _write_json(_profile_path(user_id), profile)
    return _public_profile(profile)

def authenticate_user(username, password):
    username = _normalize_username(username)
    if not username or not password:
        return None

    user_id = make_user_id(username)
    profile = _read_json(_profile_path(user_id), None)
    if not isinstance(profile, dict):
        return None
    if not _verify_password(password, profile.get("password_hash")):
        return None

    if not has_admin_user():
        profile["is_admin"] = True
    profile["updated_at"] = _now_iso()
    _write_json(_profile_path(user_id), profile)
    return _public_profile(profile)

def change_user_password(user_id, current_password, new_password):
    profile = _read_json(_profile_path(user_id), None)
    if not isinstance(profile, dict):
        raise ValueError("用户不存在")
    if not _verify_password(current_password, profile.get("password_hash")):
        raise ValueError("当前密码不正确")

    now = _now_iso()
    profile.update({
        "password_hash": _hash_password(new_password),
        "password_updated_at": now,
        "updated_at": now,
    })
    _write_json(_profile_path(user_id), profile)
    return _public_profile(profile)

def set_user_password(user_id, new_password):
    profile = _read_json(_profile_path(user_id), None)
    if not isinstance(profile, dict):
        raise ValueError("用户不存在")

    now = _now_iso()
    profile.update({
        "password_hash": _hash_password(new_password),
        "password_updated_at": now,
        "updated_at": now,
    })
    _write_json(_profile_path(user_id), profile)
    return _public_profile(profile)

def set_user_admin(user_id, is_admin):
    profile = _read_json(_profile_path(user_id), None)
    if not isinstance(profile, dict):
        raise ValueError("用户不存在")

    next_is_admin = bool(is_admin)
    if profile.get("is_admin") and not next_is_admin and _admin_count() <= 1:
        raise ValueError("至少需要保留一个管理员")

    profile["is_admin"] = next_is_admin
    profile["updated_at"] = _now_iso()
    _write_json(_profile_path(user_id), profile)
    return _public_profile(profile)

def delete_user(user_id):
    profile = _read_json(_profile_path(user_id), None)
    if not isinstance(profile, dict):
        raise ValueError("用户不存在")
    if profile.get("is_admin") and _admin_count() <= 1:
        raise ValueError("至少需要保留一个管理员")

    user_dir = _safe_user_dir(user_id)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    return _public_profile(profile)

def list_users():
    users = [_public_profile(profile) for profile in _list_private_profiles()]
    return sorted(users, key=lambda user: user.get("updated_at", ""), reverse=True)

def get_user_prompt_templates(user_id):
    templates = DEFAULT_PROMPT_TEMPLATES.copy()
    user_templates = _read_json(_templates_path(user_id), {})
    if isinstance(user_templates, dict):
        for key, value in user_templates.items():
            if isinstance(value, str):
                templates[key] = value
    return templates

def save_user_prompt_templates(user_id, templates):
    saved_templates = DEFAULT_PROMPT_TEMPLATES.copy()
    for key in DEFAULT_PROMPT_TEMPLATES:
        value = templates.get(key, "")
        if isinstance(value, str) and value.strip():
            saved_templates[key] = value
    _write_json(_templates_path(user_id), saved_templates)
    return saved_templates

def list_saved_graphs(user_id):
    records = _read_json(_graphs_path(user_id), [])
    if not isinstance(records, list):
        return []
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

def save_knowledge_graph(user_id, title, source_filename, nodes, edges, source_excerpt=""):
    records = _read_json(_graphs_path(user_id), [])
    if not isinstance(records, list):
        records = []

    record = {
        "id": str(uuid.uuid4()),
        "title": title.strip() or "未命名知识图谱",
        "source_filename": source_filename,
        "created_at": _now_iso(),
        "nodes": nodes,
        "edges": edges,
        "source_excerpt": source_excerpt[:1200],
    }
    records.append(record)
    _write_json(_graphs_path(user_id), records)
    return record
