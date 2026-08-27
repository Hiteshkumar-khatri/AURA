import os
import uuid
import json
import shutil
from datetime import datetime, timedelta

# ── Sessions stored here ──────────────────────────────────────
SESSIONS_DIR = r"D:\AURA\data\sessions"

def get_sessions_dir():
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return SESSIONS_DIR

def create_session():
    session_id  = str(uuid.uuid4())
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    meta = {
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
        "files": []
    }
    with open(os.path.join(session_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return session_id

def get_session(session_id):
    if not session_id:
        return None
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    meta_path   = os.path.join(session_dir, "meta.json")
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, "r") as f:
        meta = json.load(f)
    expires_at = datetime.fromisoformat(meta["expires_at"])
    if datetime.now() > expires_at:
        return None
    return meta

def get_session_dir(session_id):
    return os.path.join(SESSIONS_DIR, session_id)

def get_session_files(session_id):
    session_dir = get_session_dir(session_id)
    if not os.path.exists(session_dir):
        return []
    files = []
    for fname in os.listdir(session_dir):
        if fname.endswith((".csv", ".xlsx")):
            fpath = os.path.join(session_dir, fname)
            fsize = os.path.getsize(fpath)
            files.append({
                "name":     fname,
                "path":     fpath,
                "size":     fsize,
                "size_str": f"{fsize/1024:.1f} KB" if fsize < 1024*1024 else f"{fsize/1024/1024:.1f} MB"
            })
    return files

def save_file_to_session(session_id, filename, contents):
    session_dir = get_session_dir(session_id)
    os.makedirs(session_dir, exist_ok=True)
    filepath = os.path.join(session_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    return filepath

def cleanup_expired_sessions():
    sessions_dir = get_sessions_dir()
    cleaned = 0
    for session_id in os.listdir(sessions_dir):
        session_dir = os.path.join(sessions_dir, session_id)
        meta_path   = os.path.join(session_dir, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            expires_at = datetime.fromisoformat(meta["expires_at"])
            if datetime.now() > expires_at:
                shutil.rmtree(session_dir)
                cleaned += 1
    return cleaned