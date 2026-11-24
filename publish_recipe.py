"""
[판타지 코미디 레시피 자동 포스팅 오케스트레이터 (publish_recipe.py)]

주요 역할:
1. 로컬 저장 규격:
   - 경로: ./generated/fantasy_recipe/{yyyy-mm}/{dd}/
   - 파일: {dd}-{title}.md, {dd}-{title}-{index}.png (예: -1.png ~ -4.png)
2. 다중 이미지 마커 파싱:
   - 본문 내 `[이미지:1]`, `[이미지:2]`, `[이미지:3]`, `[이미지:4]` 마커를 순서대로 인식하여
     텍스트 블록과 이미지 블록이 교차하는 `body_segments` 구조로 변환합니다.
   - `--images` 인자를 생략하면 레시피 `.md` 파일과 같은 폴더에서 `{stem}-{index}.png` 파일을 자동 탐지합니다.
3. 발행 및 연계 파이프라인:
   - 네이버 블로그 `Rezept` 카테고리 발행 (`naver_publisher.py`)
   - Google Drive `__generated__/gemini-hobby-fantasy-recipe/{yyyy-mm-dd} - {title}/` 아카이빙 (`gdrive_archiver.py`)
   - 레시피 전용 월별 히스토리(`history/fantasy_recipe/{yyyy-mm}.json`) 기록 (`history_manager.py`)
   - 3회 연속 실패 시 이메일 알림 발송 (`email_notifier.py`)
"""
import os
import re
import sys
import time
import traceback
import argparse
from pathlib import Path

# Windows 콘솔 한글 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from publish_scene import extract_quote_block, clean_markdown_for_naver
from naver_publisher import publish_to_naver_blog
from email_notifier import send_failure_email

# 판타지 레시피 카테고리 공통 고정 태그 (3종)
RECIPE_BASE_TAGS = ["#판타지레시피", "#판타지요리", "#코미디판타지"]
DEFAULT_RECIPE_CATEGORY = "Rezept"
DEFAULT_RECIPE_GDRIVE_FOLDER = "__generated__/gemini-hobby-fantasy-recipe"

# 레시피 머리글(소제목) 및 STEP 소제목 스타일 규격
RECIPE_HEADING_PREFIX = "✦ "
RECIPE_HEADING_STYLE = {
    "font_size": 19,
    "bold": True,
    "font_color": "#5c4033",
}
RECIPE_STEP_STYLE = {
    "font_size": 16,
    "bold": True,
    "font_color": "#7a4f2b",
}
# 주의: \s 대신 [ \t]를 사용하여 단락 간 빈 줄(\n)이 먹히지 않도록 방지
RECIPE_HEADING_PATTERN = re.compile(
    r"^[ \t]*\[(기원|레시피[ \t]*정보|재료|만드는[ \t]*법|TADA![ \t]*완성)\][ \t]*$",
    flags=re.MULTILINE
)
RECIPE_STEP_PATTERN = re.compile(r"^[ \t]*(STEP[ \t]+\d+\..+?)[ \t]*$", flags=re.MULTILINE)


def format_recipe_headings(text: str) -> tuple[str, list[str], list[str]]:
    """
    1) [기원], [레시피 정보], [재료], [만드는 법], [TADA! 완성] 마커를
       '✦ 기원' 형태의 머리글로 변환하고 앞뒤 단락 여백(빈 줄 1칸)을 보장합니다.
    2) 'STEP n. ...' 라인을 탐지하여 별도 소제목 스타일 대상으로 반환합니다.
    3) '✦ TADA! 완성' 직후 본문 첫머리에 중복된 'TADA!'가 있으면 자동 제거합니다.
    """
    headings: list[str] = []

    def repl(m):
        label = re.sub(r"\s+", " ", m.group(1).strip())
        formatted = f"{RECIPE_HEADING_PREFIX}{label}"
        if formatted not in headings:
            headings.append(formatted)
        return f"\n{formatted}\n"

    formatted_text = RECIPE_HEADING_PATTERN.sub(repl, text)

    # 3줄 이상 연속 개행은 깔끔하게 빈 줄 1칸(\n\n)으로 정규화
    formatted_text = re.sub(r"\n{3,}", "\n\n", formatted_text)

    # '✦ TADA! 완성' 직후 본문에 중복된 'TADA!' 접두사 제거
    formatted_text = re.sub(
        r"(✦ TADA! 완성\n+)[ \t]*TADA![ \t]*",
        r"\1",
        formatted_text,
        flags=re.IGNORECASE
    )

    # STEP n. 소제목 목록 추출 (순서 유지)
    step_headings: list[str] = []
    for sm in RECIPE_STEP_PATTERN.finditer(formatted_text):
        st = sm.group(1).strip()
        if st not in step_headings:
            step_headings.append(st)

    return formatted_text.strip(" \t\r\n"), headings, step_headings


def discover_recipe_images(recipe_path: Path, explicit_images: list[str] = None) -> dict[int, Path]:
    """
    레시피 마크다운 파일과 매핑되는 이미지 파일들을 {index: Path} 딕셔너리로 반환합니다.
    - explicit_images가 제공된 경우 순서대로 1..N 매핑
    - 생략된 경우 같은 폴더에서 `{stem}-{index}.png` (및 fallback `{stem}_{index}.png`) 자동 탐지
    """
    mapping: dict[int, Path] = {}

    if explicit_images:
        for idx, p_str in enumerate(explicit_images, start=1):
            p = Path(p_str)
            if p.exists():
                mapping[idx] = p.resolve()
        return mapping

    parent = recipe_path.parent
    stem = recipe_path.stem
    for idx in range(1, 20):
        candidates = [
            parent / f"{stem}-{idx}.png",
            parent / f"{stem}-{idx}.jpg",
            parent / f"{stem}_{idx}.png",
            parent / f"{stem}_{idx}.jpg",
        ]
        for cand in candidates:
            if cand.exists():
                mapping[idx] = cand.resolve()
                break
    return mapping


def parse_recipe_markdown(file_path: Path, image_map: dict[int, Path]):
    """
    레시피 마크다운 파일을 파싱하여 제목, 인용구, 다중 세그먼트(text/image), 태그, 아카이빙용 전문 텍스트를 반환합니다.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 제목 추출
    title = "오늘의 판타지 레시피"
    title_match = re.search(r"-\s*\*?제목:?\*?\s*(.+)", content)
    if title_match:
        title = title_match.group(1).strip()
    else:
        header_match = re.search(r"^#+\s*(.+)", content, re.MULTILINE)
        if header_match:
            title = header_match.group(1).strip()
    title = clean_markdown_for_naver(title)

    # 2. 태그 추출 및 규격화
    extracted_tags = []
    tag_match = re.search(r"\*?태그:?\*?\s*(.+)", content)
    if tag_match:
        for t in tag_match.group(1).split():
            clean_t = t.strip().replace(",", "")
            if clean_t.startswith("#"):
                extracted_tags.append(clean_t)
            elif clean_t:
                extracted_tags.append(f"#{clean_t}")

    specific_tags = [t for t in extracted_tags if t not in RECIPE_BASE_TAGS]
    final_tags = list(RECIPE_BASE_TAGS)
    for stag in specific_tags[:3]:
        if stag not in final_tags:
            final_tags.append(stag)

    # 3. 본문 영역 분리 (### 2. 이후)
    body_section = content
    if "### 2." in content:
        body_section = content.split("### 2.", 1)[1]
    elif "### 2" in content:
        body_section = content.split("### 2", 1)[1]

    # 본문 섹션 헤더 라인 제거 (예: '판타지 코미디 레시피 본문')
    body_section = re.sub(r"^\s*판타지\s*코미디\s*레시피\s*본문[^\n]*\n+", "", body_section)

    # 본문 하단 태그 라인 제거
    if "태그:" in body_section:
        body_section = body_section.split("태그:", 1)[0]

    # 4. 인용구 블록 추출
    quote, body_section = extract_quote_block(body_section)

    # 4.5. 머리글([기원], [레시피 정보], [재료], [만드는 법], [TADA! 완성]) 변환, STEP 탐지 및 중복 TADA! 제거
    body_section, detected_headings, detected_steps = format_recipe_headings(body_section)

    # 5. [이미지:N] 마커 기준 다중 세그먼트 분할
    marker_pattern = re.compile(r"\[이미지\s*:\s*(\d+)\]")
    segments = []
    archive_lines = []
    if quote:
        q_src = f"\n{quote['source']}" if quote.get("source") else ""
        archive_lines.append(f"[{quote['text']}{q_src}]")

    pos = 0
    used_image_paths = []
    for m in marker_pattern.finditer(body_section):
        text_chunk = body_section[pos:m.start()].strip(" \t\r\n")
        if text_chunk:
            cleaned_chunk = clean_markdown_for_naver(text_chunk)
            if cleaned_chunk:
                segments.append({"type": "text", "content": cleaned_chunk})
                archive_lines.append(cleaned_chunk)

        img_idx = int(m.group(1))
        img_path = image_map.get(img_idx)
        if img_path and img_path.exists():
            segments.append({"type": "image", "path": str(img_path), "index": img_idx})
            used_image_paths.append(str(img_path))
            archive_lines.append(f"[삽화 {img_idx}: {img_path.name}]")
        else:
            print(f"[!] 경고: [이미지:{img_idx}] 마커에 해당하는 이미지 파일을 찾지 못했습니다.")

        pos = m.end()

    tail_chunk = body_section[pos:].strip(" \t\r\n")
    if tail_chunk:
        cleaned_tail = clean_markdown_for_naver(tail_chunk)
        if cleaned_tail:
            segments.append({"type": "text", "content": cleaned_tail})
            archive_lines.append(cleaned_tail)

    archive_lines.append(f"태그: {' '.join(final_tags)}")
    archive_text = "\n\n".join(archive_lines)

    return title, quote, segments, final_tags, used_image_paths, archive_text, detected_headings, detected_steps


def main():
    parser = argparse.ArgumentParser(description="판타지 코미디 레시피와 다중 삽화를 네이버 블로그(Rezept)에 발행하고 Google Drive에 아카이빙합니다.")
    parser.add_argument("--recipe", required=True, help="레시피 마크다운(.md) 파일 경로")
    parser.add_argument("--images", nargs="*", default=None, help="삽화 이미지 경로 목록 (생략 시 {stem}-{index}.png 자동 탐지)")
    parser.add_argument("--category", default=DEFAULT_RECIPE_CATEGORY, help=f"발행할 네이버 블로그 카테고리 (기본값: {DEFAULT_RECIPE_CATEGORY})")
    parser.add_argument("--gdrive-folder", default=DEFAULT_RECIPE_GDRIVE_FOLDER, help=f"Google Drive 아카이빙 폴더 경로 (기본값: {DEFAULT_RECIPE_GDRIVE_FOLDER})")
    parser.add_argument("--headless", action="store_true", help="브라우저 창을 띄우지 않고 백그라운드 실행")
    parser.add_argument("--dry-run", action="store_true", help="실제 발행·아카이빙 없이 파싱 결과와 이미지 매핑만 검증")
    args = parser.parse_args()

    recipe_path = Path(args.recipe)
    if not recipe_path.exists():
        err_msg = f"레시피 원고 파일을 찾을 수 없습니다: {recipe_path}"
        print(f"Error: {err_msg}")
        if not args.dry_run:
            send_failure_email(
                schedule_title="Daily Naver Blog Fantasy Recipe",
                error_message=err_msg
            )
        sys.exit(1)

    image_map = discover_recipe_images(recipe_path, args.images)
    title, quote, segments, tags, used_images, archive_text, headings, step_headings = parse_recipe_markdown(recipe_path, image_map)

    print("=" * 64)
    print(f"[*] 제목: {title}")
    print(f"[*] 발행 카테고리: {args.category}")
    print(f"[*] Google Drive 경로: {args.gdrive_folder}")
    if quote:
        print(f"[*] 인용구 ({quote.get('style') or '랜덤'}): {quote.get('text')} ({quote.get('source')})")
    print(f"[*] 머리글 스타일 대상 ({len(headings)}개, 19pt Bold #5c4033): {headings}")
    print(f"[*] STEP 소제목 스타일 대상 ({len(step_headings)}개, 16pt Bold #7a4f2b): {step_headings}")
    print(f"[*] 감지된 세그먼트 수: {len(segments)}개 (이미지 {len(used_images)}장)")
    for i, seg in enumerate(segments, start=1):
        if seg["type"] == "text":
            preview = seg["content"].replace("\n", " ")[:55]
            print(f"    {i}. [TEXT] ({len(seg['content'])}자) {preview}...")
        else:
            print(f"    {i}. [IMAGE #{seg.get('index')}] {seg['path']}")
    print(f"[*] 태그 ({len(tags)}종): {tags}")
    print("=" * 64)

    if args.dry_run:
        print("\n[DRY-RUN] 파싱 및 다중 이미지 매핑 검증 완료! 실제 발행 및 아카이빙은 수행하지 않았습니다.")
        return

    # [전처리] 다중 삽화 배경색 #ece0c6 정밀 보정 (블로그 스킨 이음새 제거)
    if used_images:
        try:
            from image_bg_normalizer import normalize_images
            normalize_images(used_images)
        except Exception as berr:
            print(f"[-] 배경색 보정 알림 (원본 유지): {berr}")

    MAX_RETRIES = 3
    last_error = ""
    last_tb = ""

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n{'='*60}")
        print(f"[*] [시도 {attempt}/{MAX_RETRIES}] 네이버 블로그 '{args.category}' 발행 시작...")
        print(f"{'='*60}")
        try:
            result = publish_to_naver_blog(
                title=title,
                body_segments=segments,
                tags=tags,
                quote=quote,
                category_name=args.category,
                headless=args.headless,
                heading_groups=[
                    (headings, RECIPE_HEADING_STYLE),
                    (step_headings, RECIPE_STEP_STYLE),
                ]
            )
            if result.get("status") == "success":
                print(f"\n[+] [성공] {attempt}번째 시도에서 레시피 발행이 완료되었습니다!")

                # [연계 1] Google Drive 아카이빙 (글별 하위 폴더에 문서 + 다중 이미지 저장)
                try:
                    from gdrive_archiver import archive_to_google_drive
                    archive_to_google_drive(
                        title=title,
                        story_content=archive_text,
                        image_paths=used_images,
                        folder_path=args.gdrive_folder,
                        subfolder_per_post=True,
                        schedule_title="Google Drive Archiving - Daily Fantasy Recipe"
                    )
                except Exception as gerr:
                    print(f"[-] Google Drive 아카이빙 알림 (발행은 정상 완료됨): {gerr}")

                # [연계 2] 레시피 전용 월별 히스토리(history/fantasy_recipe/{yyyy-mm}.json)에 기록
                try:
                    from history_manager import save_post_to_monthly_history
                    save_post_to_monthly_history(
                        {
                            "date": time.strftime("%Y-%m-%d"),
                            "title": title,
                            "category": args.category,
                            "tags": tags,
                            "recipe_file": str(recipe_path),
                            "image_files": used_images,
                            "published_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        },
                        subdir="fantasy_recipe"
                    )
                    print("[+] 레시피 월별 히스토리(history/fantasy_recipe/{yyyy-mm}.json)에 기록 완료!")
                except Exception as herr:
                    print(f"[-] 히스토리 기록 알림: {herr}")
                return
            else:
                last_error = result.get("error", "알 수 없는 발행 오류")
                print(f"[!] [실패] {attempt}번째 시도 실패: {last_error}")
        except Exception as e:
            last_error = str(e)
            last_tb = traceback.format_exc()
            print(f"[!] [예외 발생] {attempt}번째 시도 오류: {last_error}")

        if attempt < MAX_RETRIES:
            wait_time = 10 * attempt
            print(f"[*] {wait_time}초 대기 후 재시도합니다...")
            time.sleep(wait_time)

    print("\n" + "!" * 70)
    print("[!] 3회 재시도 후에도 레시피 발행이 최종 실패하였습니다.")
    print("!" * 70 + "\n")
    send_failure_email(
        schedule_title="Daily Naver Blog Fantasy Recipe",
        error_message=f"레시피 블로그 포스팅 3회 연속 실패. 최종 오류: {last_error}",
        error_traceback=last_tb
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
