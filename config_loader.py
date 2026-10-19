"""
Configuration loader with .env support.
Loads environment variables from .env and expands ${VAR} placeholders in config.json.
Resolves relative paths dynamically based on repository root directory.
"""
import os
import re
import json
from pathlib import Path

# Project root directory is always the directory containing this file
PROJECT_ROOT = Path(__file__).resolve().parent

# Automatically load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
except ImportError:
    pass

DEFAULT_ENV = {
    "BLOG_ID": "sun_o_glitter",
    "CATEGORY_NAME": "Quatsch",
    "EMAIL_RECIPIENT": "orselv99@gmail.com",
    "EMAIL_SENDER": "orselv99@gmail.com",
    "GMAIL_APP_PASSWORD": "",
    "CHROME_PROFILE_DIR": "./chrome_profile",
    "HISTORY_FILE": "./history.json",
    "OUTPUT_DIR": "./generated",
    "GOOGLE_DRIVE_FOLDER": "__generated__/gemini-hobby-fantasy-scene",
    "GOOGLE_DRIVE_LOCAL_PATH": "",
}

def _expand_var(val: str) -> str:
    if not isinstance(val, str):
        return val

    # Match ${VAR_NAME} or $VAR_NAME
    pattern = re.compile(r"\$\{(\w+)\}|\$(\w+)")
    def repl(m):
        var_name = m.group(1) or m.group(2)
        return os.environ.get(var_name, DEFAULT_ENV.get(var_name, ""))

    return pattern.sub(repl, val)

def _expand_dict(data: dict) -> dict:
    expanded = {}
    for k, v in data.items():
        if isinstance(v, dict):
            expanded[k] = _expand_dict(v)
        elif isinstance(v, list):
            expanded[k] = [_expand_var(item) if isinstance(item, str) else item for item in v]
        elif isinstance(v, str):
            expanded[k] = _expand_var(v)
        else:
            expanded[k] = v
    return expanded

def resolve_path(path_str: str) -> Path:
    """Resolves a path string; if relative, makes it absolute relative to PROJECT_ROOT."""
    if not path_str:
        return PROJECT_ROOT
    p = Path(path_str)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return p

def load_config(config_path: str | Path = None) -> dict:
    """
    Loads and expands configuration from config.json and .env.
    """
    if config_path is None:
        cfg_file = PROJECT_ROOT / "config.json"
    else:
        cfg_file = Path(config_path)

    raw_config = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
        except Exception as e:
            print(f"[!] config.json 읽기 오류 ({cfg_file}): {e}")

    config = _expand_dict(raw_config)

    # Fallback defaults if fields missing
    config.setdefault("blog_id", os.environ.get("BLOG_ID", DEFAULT_ENV["BLOG_ID"]))
    config.setdefault("category_name", os.environ.get("CATEGORY_NAME", DEFAULT_ENV["CATEGORY_NAME"]))
    config.setdefault("publish_mode", "immediate")
    config.setdefault("story_length_chars", 2000)

    # Normalize paths to absolute paths
    chrome_profile_raw = config.get("chrome_profile_dir") or os.environ.get("CHROME_PROFILE_DIR", "./chrome_profile")
    config["chrome_profile_dir"] = str(resolve_path(chrome_profile_raw))

    history_file_raw = config.get("history_file") or os.environ.get("HISTORY_FILE", "./history.json")
    config["history_file"] = str(resolve_path(history_file_raw))

    output_dir_raw = config.get("output_dir") or os.environ.get("OUTPUT_DIR", "./generated")
    config["output_dir"] = str(resolve_path(output_dir_raw))

    # Email config
    email_cfg = config.setdefault("email_alert", {})
    email_cfg.setdefault("recipient", os.environ.get("EMAIL_RECIPIENT", DEFAULT_ENV["EMAIL_RECIPIENT"]))
    email_cfg.setdefault("sender_email", os.environ.get("EMAIL_SENDER", DEFAULT_ENV["EMAIL_SENDER"]))
    email_cfg.setdefault("smtp_server", "smtp.gmail.com")
    email_cfg.setdefault("smtp_port", 587)
    email_cfg.setdefault("schedule_title", "Daily Naver Blog Fantasy Novel")
    email_cfg.setdefault("app_password", os.environ.get("GMAIL_APP_PASSWORD", ""))

    # Google Drive config
    gdrive_cfg = config.setdefault("google_drive", {})
    gdrive_cfg.setdefault("enabled", True)
    gdrive_cfg.setdefault("folder_path", os.environ.get("GOOGLE_DRIVE_FOLDER", DEFAULT_ENV["GOOGLE_DRIVE_FOLDER"]))
    gdrive_cfg.setdefault("local_mount_path", os.environ.get("GOOGLE_DRIVE_LOCAL_PATH", ""))
    gdrive_cfg.setdefault("convert_to_google_doc", True)

    return config

# Global config instance
_cached_config = None

def get_config(reload: bool = False) -> dict:
    global _cached_config
    if _cached_config is None or reload:
        _cached_config = load_config()
    return _cached_config
