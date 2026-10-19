"""
[월별 히스토리 관리 모듈 (history_manager.py)]

주니어 개발자를 위한 아키텍처 안내:
1. 단일 대용량 파일(history.json)의 문제점:
   - 매일 글을 발행하면 하나의 JSON 파일이 수백~수천 개 포스팅으로 무한히 비대해집니다.
   - 글 하나를 추가할 때마다 거대한 JSON을 통째로 메모리에 파싱하고 다시 디스크에 쓰는 I/O 비용이 발생하며,
     작업 도중 비정상 종료(정전, 강제 종료 등)가 일어나면 전체 히스토리가 손상될 위험이 큽니다.

2. 월별 분할(Monthly Partitioning)의 장점:
   - 'history/{yyyy-mm}.json' 구조로 한 달 단위(보통 20~30개 내외)로 파일을 쪼개어 관리합니다.
   - AI가 오늘 소설을 창작할 때 필요한 '최근 소재 중복 방지'는 가장 최근 15편 정도만 확인하면 되므로,
     가장 최신 1~2개 월 파일만 읽으면 되어 성능과 안정성이 획기적으로 향상됩니다.
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from config_loader import get_config, PROJECT_ROOT

def get_history_dir() -> Path:
    """
    히스토리 저장소 디렉터리 경로를 반환합니다.
    폴더가 아직 없으면 mkdir(parents=True)를 통해 자동으로 생성합니다.
    """
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
    """현재 시스템 시간을 기준으로 'YYYY-MM' 형식의 문자열(예: '2026-10')을 반환합니다."""
    return datetime.now().strftime("%Y-%m")

def get_monthly_history_file(year_month: str = None) -> Path:
    """
    특정 연월의 히스토리 파일 경로를 반환합니다.
    예: year_month가 '2026-09'이면 'history/2026-09.json'의 Path 객체 반환.
    생략 시 현재 연월을 기준으로 합니다.
    """
    if not year_month:
        year_month = get_current_year_month()
    return get_history_dir() / f"{year_month}.json"

def load_monthly_history(year_month: str = None) -> dict:
    """
    지정된 연월의 JSON 파일을 읽어 딕셔너리로 반환합니다.
    파일이 아직 없거나 손상되었을 경우 기본 뼈대 구조를 안전하게 반환합니다.
    """
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

    # 파일이 없으면 새롭게 채워넣을 수 있도록 기본 구조를 반환합니다.
    return {
        "year_month": year_month,
        "posts": []
    }

def save_post_to_monthly_history(post_data: dict, year_month: str = None) -> Path:
    """
    단일 포스팅 정보(post_data)를 해당되는 연월의 JSON 파일에 안전하게 저장하거나 갱신합니다.
    
    주요 로직:
    1. year_month가 지정되지 않은 경우, post_data 안의 'date'나 'migrated_at' 문자열에서 연월(YYYY-MM)을 자동 추출합니다.
    2. post_data에 date 필드가 없다면 데이터 무결성을 위해 기본 date를 채워넣습니다.
    3. 동일한 logNo(네이버 글 고유번호)가 이미 있다면 내용을 덮어쓰고(Update), 없으면 새로 추가(Append)합니다.
    4. 혹시 이전 잘못된 분류로 인해 다른 달의 파일에 동일한 logNo가 남아있다면 중복을 방지하기 위해 자동 정리합니다.
    """
    if not year_month:
        date_val = post_data.get("date") or ""
        m = re.search(r"(\d{4}-\d{2})", str(date_val))
        if m:
            year_month = m.group(1)
        else:
            migrated_val = post_data.get("migrated_at") or ""
            m_mig = re.search(r"(\d{4}-\d{2})", str(migrated_val))
            if m_mig:
                year_month = m_mig.group(1)
            else:
                year_month = get_current_year_month()

    # 데이터 정합성 보장: date 필드가 비어있으면 해당 월의 1일로 기본값 지정
    if not post_data.get("date"):
        post_data["date"] = f"{year_month}-01"

    hdata = load_monthly_history(year_month)
    posts = hdata.setdefault("posts", [])
    log_no = post_data.get("logNo")

    # 동일 글(logNo 기준)이 이미 존재하면 수정, 없으면 신규 추가
    existing = next((p for p in posts if log_no and p.get("logNo") == log_no), None)
    if existing:
        existing.update(post_data)
    else:
        posts.append(post_data)

    target_file = get_monthly_history_file(year_month)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(hdata, f, ensure_ascii=False, indent=2)

    # 데이터 정리: 만약 이 글이 이전 잘못된 연월 파일에 등록되어 있었다면 그 파일에서 삭제
    if log_no:
        hdir = get_history_dir()
        for other_file in hdir.glob("????-??.json"):
            if other_file.name != f"{year_month}.json":
                try:
                    with open(other_file, "r", encoding="utf-8") as of:
                        odata = json.load(of)
                    oposts = odata.get("posts", [])
                    new_oposts = [p for p in oposts if str(p.get("logNo")) != str(log_no)]
                    if len(new_oposts) != len(oposts):
                        odata["posts"] = new_oposts
                        with open(other_file, "w", encoding="utf-8") as of:
                            json.dump(odata, of, ensure_ascii=False, indent=2)
                except Exception:
                    pass

    return target_file

def load_recent_posts(limit: int = 15) -> list[dict]:
    """
    최신 월별 파일부터 역순으로 탐색하여 가장 최근에 작성된 글들을 limit개수만큼 수집합니다.
    
    활용처:
    소설 창작 에이전트(LLM)가 프롬프트 생성 전 이 함수를 호출하여,
    최근 다루었던 소재(예: 별감정사, 거울수리공 등)가 중복 출현하지 않도록 방어하는 데 사용됩니다.
    """
    hdir = get_history_dir()
    # 파일명을 역순 정렬하면 2026-10.json -> 2026-09.json 순으로 최신 파일부터 접근합니다.
    month_files = sorted(hdir.glob("????-??.json"), reverse=True)

    collected_posts = []
    for mfile in month_files:
        try:
            with open(mfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                posts = data.get("posts", [])
                # 파일 내 포스팅 리스트를 역순(최신순)으로 순회
                for p in reversed(posts):
                    collected_posts.append(p)
                    if len(collected_posts) >= limit:
                        return collected_posts
        except Exception:
            continue

    # 만약 history/ 디렉터리에 아무 파일도 없다면 구버전 루트 history.json을 fallback으로 참조
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
    모든 월별 히스토리 파일에 등록된 네이버 글 번호(logNo)들을 set(집합) 형태로 반환합니다.
    
    태그 일괄 마이그레이션(migrate_tags.py) 시 이미 수정이 완료된 글들을
    O(1) 속도로 즉시 판별하여 중복 작업을 건너뛰기 위해 사용됩니다.
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

    # 루트 history.json도 함께 검사하여 누락 방지
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
    """
    기존 루트 디렉터리에 단일 파일로 존재하던 구버전 history.json 파일의 항목들을
    월별 분할 구조(history/{yyyy-mm}.json)로 자동 변환해 주는 1회성 마이그레이션 유틸리티입니다.
    """
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
