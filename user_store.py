# user_store.py
import hashlib
import json
import os
import re
import uuid
from datetime import datetime

from prompt_config import DEFAULT_PROMPT_TEMPLATES

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_DIR = os.path.join(DATA_DIR, "users")

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

def make_user_id(username):
    username = username.strip()
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

def ensure_user(username):
    username = username.strip()
    if not username:
        raise ValueError("用户名不能为空")

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

def list_users():
    if not os.path.exists(USERS_DIR):
        return []

    users = []
    for user_id in os.listdir(USERS_DIR):
        profile = _read_json(_profile_path(user_id), None)
        if isinstance(profile, dict) and profile.get("id"):
            users.append(profile)
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
