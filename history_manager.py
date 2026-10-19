"""
History Manager with Monthly Partitioning (history/{yyyy-mm}.json).
Prevents history files from growing unbounded and enables fast retrieval
of recent posts for deduplication without loading full historical archives.
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from config_loader import get_config, PROJECT_ROOT

def get_history_dir() -> Path:
    """Returns the history directory path, creating it if needed."""
    cfg = get_config()
    history_dir_str = cfg.get("history_dir")
    if history_dir_str:
        hdir = Path(history_dir_str)
        if not hdir.is_absolute():
            hdir = (PROJECT_ROOT / hdir).resolve()
    else:
        hdir = PROJECT_ROOT / "history"

    hdir.mkdir(parents=True, exist_ok=True)
    return hdir

def get_current_year_month() -> str:
    """Returns current year-month string in YYYY-MM format."""
    return datetime.now().strftime("%Y-%m")

def get_monthly_history_file(year_month: str = None) -> Path:
    """Returns the path to a specific monthly history file (e.g. history/2026-10.json)."""
    if not year_month:
        year_month = get_current_year_month()
    return get_history_dir() / f"{year_month}.json"

def load_monthly_history(year_month: str = None) -> dict:
    """Loads a specific monthly history file or returns an empty structure."""
    if not year_month:
        year_month = get_current_year_month()

    file_path = get_monthly_history_file(year_month)
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("year_month", year_month)
                data.setdefault("posts", [])
                return data
        except Exception as e:
            print(f"[!] {file_path.name} 로드 오류: {e}")

    return {
        "year_month": year_month,
        "posts": []
    }

def save_post_to_monthly_history(post_data: dict, year_month: str = None) -> Path:
    """
    Saves or updates a post entry in its corresponding monthly history file.
    Automatically resolves year_month from post date or defaults to current month.
    """
    if not year_month:
        date_val = post_data.get("date") or post_data.get("migrated_at") or ""
        m = re.search(r"(\d{4}-\d{2})", str(date_val))
        if m:
            year_month = m.group(1)
        else:
            year_month = get_current_year_month()

    hdata = load_monthly_history(year_month)
    posts = hdata.setdefault("posts", [])
    log_no = post_data.get("logNo")

    # Update existing entry if present, else append
    existing = next((p for p in posts if log_no and p.get("logNo") == log_no), None)
    if existing:
        existing.update(post_data)
    else:
        posts.append(post_data)

    target_file = get_monthly_history_file(year_month)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(hdata, f, ensure_ascii=False, indent=2)

    return target_file

def load_recent_posts(limit: int = 15) -> list[dict]:
    """
    Loads recent posts across newest monthly history files.
    The creation script can inspect this to prevent duplicate themes and concepts.
    """
    hdir = get_history_dir()
    month_files = sorted(hdir.glob("????-??.json"), reverse=True)

    collected_posts = []
    for mfile in month_files:
        try:
            with open(mfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                posts = data.get("posts", [])
                # Posts within file in reverse chronological order
                for p in reversed(posts):
                    collected_posts.append(p)
                    if len(collected_posts) >= limit:
                        return collected_posts
        except Exception:
            continue

    # Fallback to root history.json if history/ is empty
    if not collected_posts:
        root_hist = PROJECT_ROOT / "history.json"
        if root_hist.exists():
            try:
                with open(root_hist, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                    for p in reversed(rdata.get("posts", [])):
                        collected_posts.append(p)
                        if len(collected_posts) >= limit:
                            break
            except Exception:
                pass

    return collected_posts

def get_all_migrated_log_nos() -> set[str]:
    """
    Gathers all migrated logNo IDs across all monthly history files.
    """
    hdir = get_history_dir()
    seen = set()

    for mfile in hdir.glob("????-??.json"):
        try:
            with open(mfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p in data.get("posts", []):
                    lno = p.get("logNo")
                    if lno:
                        seen.add(str(lno))
        except Exception:
            continue

    # Fallback to root history.json if present
    root_hist = PROJECT_ROOT / "history.json"
    if root_hist.exists():
        try:
            with open(root_hist, "r", encoding="utf-8") as f:
                rdata = json.load(f)
                for p in rdata.get("posts", []):
                    lno = p.get("logNo")
                    if lno:
                        seen.add(str(lno))
        except Exception:
            pass

    return seen

def migrate_root_history_to_monthly():
    """Migrates existing root history.json entries into history/{yyyy-mm}.json."""
    root_hist = PROJECT_ROOT / "history.json"
    if not root_hist.exists():
        return

    try:
        with open(root_hist, "r", encoding="utf-8") as f:
            data = json.load(f)
        posts = data.get("posts", [])
        migrated_count = 0
        for p in posts:
            save_post_to_monthly_history(p)
            migrated_count += 1
        print(f"[+] 기존 history.json의 {migrated_count}편 포스팅을 history/{{yyyy-mm}}.json으로 분할 저장했습니다.")
    except Exception as e:
        print(f"[!] 기존 history.json 마이그레이션 오류: {e}")
