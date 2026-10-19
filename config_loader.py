"""
[설정 로더 모듈 (config_loader.py)]

주니어 개발자를 위한 안내:
이 모듈은 프로젝트의 모든 환경 설정(.env 및 config.json)을 하나로 통합하여 제공하는 중앙 설정 관리자입니다.

주요 역할:
1. 프로젝트 기준 경로(PROJECT_ROOT)를 파일 위치 기준으로 계산하여, 어디서 스크립트를 실행하든
   (예: Windows 작업 스케줄러, 백그라운드 cron, 다른 작업 디렉터리) 경로 오류가 발생하지 않도록 방어합니다.
2. .env 파일의 환경변수를 자동으로 로드하고, config.json에 포함된 ${변수명} 형태의 플레이스홀더를 실제 값으로 치환합니다.
3. 상대 경로로 작성된 디렉터리 경로들을 프로젝트 루트 기준의 '절대 경로'로 자동 변환하여 전달합니다.
"""
import os
import re
import json
from pathlib import Path

# [중요] 스크립트 실행 위치(os.getcwd())에 의존하지 않고,
# 현재 config_loader.py 파일이 위치한 실제 디렉터리를 프로젝트 루트로 고정합니다.
# 이렇게 해야 배치 파일이나 작업 스케줄러에서 다른 경로에서 호출해도 항상 올바른 파일을 찾습니다.
PROJECT_ROOT = Path(__file__).resolve().parent

# python-dotenv 라이브러리가 설치되어 있다면 .env 파일을 로드합니다.
# override=False로 설정하여 이미 시스템 환경변수로 선언된 값이 있다면 우선권을 줍니다.
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
except ImportError:
    pass

# 환경변수나 .env 파일에 값이 지정되지 않았을 때 적용할 안전 기본값(Fallback) 테이블입니다.
DEFAULT_ENV = {
    "BLOG_ID": "sun_o_glitter",
    "CATEGORY_NAME": "Quatsch",
    "EMAIL_RECIPIENT": "orselv99@gmail.com",
    "EMAIL_SENDER": "orselv99@gmail.com",
    "GMAIL_APP_PASSWORD": "",
    "CHROME_PROFILE_DIR": "./chrome_profile",
    "HISTORY_DIR": "./history",
    "HISTORY_FILE": "./history.json",
    "OUTPUT_DIR": "./generated",
    "GOOGLE_DRIVE_FOLDER": "__generated__/gemini-hobby-fantasy-scene",
    "GOOGLE_DRIVE_LOCAL_PATH": "",
}

def _expand_var(val: str) -> str:
    """
    문자열 내의 ${VAR_NAME} 또는 $VAR_NAME 패턴을 실제 환경변수 값으로 치환합니다.
    환경변수에 등록되지 않은 경우 DEFAULT_ENV의 기본값을 사용하며, 없으면 빈 문자열로 처리합니다.
    """
    if not isinstance(val, str):
        return val

    pattern = re.compile(r"\$\{(\w+)\}|\$(\w+)")
    def repl(m):
        var_name = m.group(1) or m.group(2)
        return os.environ.get(var_name, DEFAULT_ENV.get(var_name, ""))

    return pattern.sub(repl, val)

def _expand_dict(data: dict) -> dict:
    """
    딕셔너리 구조를 재귀적으로 순회하면서 문자열, 리스트, 하위 딕셔너리에 포함된
    모든 환경변수 플레이스홀더(${...})를 실제 값으로 치환합니다.
    """
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
    """
    경로 문자열을 Path 객체로 변환합니다.
    만약 경로가 상대 경로('./history' 등)라면 PROJECT_ROOT를 기준으로 결합하여
    완전한 절대 경로(Absolute Path)로 변환해 반환합니다.
    """
    if not path_str:
        return PROJECT_ROOT
    p = Path(path_str)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return p

def load_config(config_path: str | Path = None) -> dict:
    """
    config.json 파일과 .env 환경변수를 결합하여 완성된 설정 딕셔너리를 생성합니다.
    
    동작 순서:
    1. config.json 파일 읽기 (지정되지 않으면 PROJECT_ROOT/config.json)
    2. ${VAR} 플레이스홀더 치환
    3. 누락된 필수 필드에 대해 기본값(Default) 보충 (setdefault 사용)
    4. 디렉터리 경로들을 절대 경로로 정규화
    5. 이메일 및 Google Drive 연동 설정 구조화
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

    # 환경변수 확장
    config = _expand_dict(raw_config)

    # 필수 기본 설정 보충 (누락 방지)
    config.setdefault("blog_id", os.environ.get("BLOG_ID", DEFAULT_ENV["BLOG_ID"]))
    config.setdefault("category_name", os.environ.get("CATEGORY_NAME", DEFAULT_ENV["CATEGORY_NAME"]))
    config.setdefault("publish_mode", "immediate")
    config.setdefault("story_length_chars", 2000)

    # 주요 작업 디렉터리 경로를 절대 경로로 정규화
    chrome_profile_raw = config.get("chrome_profile_dir") or os.environ.get("CHROME_PROFILE_DIR", "./chrome_profile")
    config["chrome_profile_dir"] = str(resolve_path(chrome_profile_raw))

    history_dir_raw = config.get("history_dir") or os.environ.get("HISTORY_DIR", "./history")
    config["history_dir"] = str(resolve_path(history_dir_raw))

    history_file_raw = config.get("history_file") or os.environ.get("HISTORY_FILE", "./history.json")
    config["history_file"] = str(resolve_path(history_file_raw))

    output_dir_raw = config.get("output_dir") or os.environ.get("OUTPUT_DIR", "./generated")
    config["output_dir"] = str(resolve_path(output_dir_raw))

    # 이메일 알림 설정
    email_cfg = config.setdefault("email_alert", {})
    email_cfg.setdefault("recipient", os.environ.get("EMAIL_RECIPIENT", DEFAULT_ENV["EMAIL_RECIPIENT"]))
    email_cfg.setdefault("sender_email", os.environ.get("EMAIL_SENDER", DEFAULT_ENV["EMAIL_SENDER"]))
    email_cfg.setdefault("smtp_server", "smtp.gmail.com")
    email_cfg.setdefault("smtp_port", 587)
    email_cfg.setdefault("schedule_title", "Daily Naver Blog Fantasy Novel")
    email_cfg.setdefault("app_password", os.environ.get("GMAIL_APP_PASSWORD", ""))

    # Google Drive 아카이빙 설정
    gdrive_cfg = config.setdefault("google_drive", {})
    gdrive_cfg.setdefault("enabled", True)
    gdrive_cfg.setdefault("folder_path", os.environ.get("GOOGLE_DRIVE_FOLDER", DEFAULT_ENV["GOOGLE_DRIVE_FOLDER"]))
    gdrive_cfg.setdefault("local_mount_path", os.environ.get("GOOGLE_DRIVE_LOCAL_PATH", ""))
    gdrive_cfg.setdefault("convert_to_google_doc", True)

    return config

# 싱글톤 패턴처럼 설정을 메모리에 캐싱하여, 불필요하게 디스크 I/O를 반복하지 않도록 합니다.
_cached_config = None

def get_config(reload: bool = False) -> dict:
    """
    캐시된 설정을 반환합니다. reload=True 전달 시 디스크에서 다시 로드합니다.
    """
    global _cached_config
    if _cached_config is None or reload:
        _cached_config = load_config()
    return _cached_config
