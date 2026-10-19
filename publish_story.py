"""
[단편 소설 자동 포스팅 오케스트레이터 (publish_story.py)]

주니어 개발자를 위한 파이프라인 및 아키텍처 안내:
1. 마크다운 정제 (Markdown Stripping)가 필요한 이유:
   - 네이버 블로그 스마트에디터 ONE은 벨로그나 티스토리와 달리 마크다운 렌더링을 지원하지 않습니다.
   - LLM이 작성한 마크다운 원고를 그대로 복사하면 `**볼드**`, `### 제목`, `> 인용`, `---` 기호가
     문자 그대로 노출되어 독자의 몰입을 방해하고 가독성을 심각하게 해칩니다.
   - 따라서 정규식(Regex)을 이용해 문법 기호만 깔끔하게 제거하고 순수 줄글로 변환합니다.

2. 서사 흐름에 따른 삽화 위치 분할 ([삽화 삽입 위치]):
   - 단순 기계적인 50:50 중앙 배치는 소설의 기승전결과 어긋나 지루함을 유발합니다.
   - LLM이 원고 작성 시 결정적인 미스터리나 장면이 밝혀지는 순간에 `[삽화 삽입 위치]` 마커를 삽입하고,
     스크립트는 이 마커를 기점으로 본문을 1부와 2부로 자동 분할하여 삽화를 자연스럽게 배치합니다.

3. 발행 후 자동 연계 작업 (Post-Publish Pipelines):
   - 블로그 발행 성공 시:
     1) Google Drive에 구글 문서와 이미지로 백업 (`gdrive_archiver.py`)
     2) 월별 분할 히스토리(`history/{yyyy-mm}.json`)에 발행 이력 실시간 영속화
   - 3회 연속 실패 시: 관리자에게 상세 트레이스백과 함께 실패 알림 이메일 즉시 전송 (`email_notifier.py`)
"""
import os
import re
import sys
import json
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

from naver_publisher import publish_to_naver_blog
from email_notifier import send_failure_email

# 블로그 카테고리 전체 공통 고정 태그 (3종)
BASE_TAGS = ["#판타지소설", "#단편소설", "#환상문학"]

def clean_markdown_for_naver(text: str) -> str:
    """
    네이버 스마트에디터 ONE에 맞게 마크다운 기호들을 정규식으로 안전하게 제거합니다.
    - 구분선(---, ***) 제거
    - 인용구 기호(> ) 제거
    - 마크다운 헤더(### ) 제거
    - 볼드/이탤릭 기호(**, *, __) 제거
    - 백틱 코드 기호(`) 제거
    """
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        # 가로 구분선 (---, ***, ___ 등) 제거
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            continue
        # 인용구 접두사 (> ) 제거
        stripped = re.sub(r"^>\s*", "", stripped)
        # 제목 헤더 기호 (### ) 제거
        stripped = re.sub(r"^#{1,6}\s*", "", stripped)
        # 굵은 글씨 및 기울임꼴 기호 제거
        stripped = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
        stripped = re.sub(r"\*(.*?)\*", r"\1", stripped)
        stripped = re.sub(r"__(.*?)__", r"\1", stripped)
        stripped = re.sub(r"`(.*?)`", r"\1", stripped)
        lines.append(stripped)
    return "\n".join(lines).strip()

def parse_story_markdown(file_path: Path):
    """
    작성된 소설 마크다운 파일에서 제목, 태그, 본문(삽화 기준 전/후반부)을 파싱하여 정제합니다.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 제목(Title) 추출
    title = "오늘의 환상 단편"
    title_match = re.search(r"-\s*\*?제목:?\*?\s*(.+)", content)
    if title_match:
        title = title_match.group(1).strip()
    else:
        header_match = re.search(r"^#+\s*(.+)", content, re.MULTILINE)
        if header_match:
            title = header_match.group(1).strip()
    title = clean_markdown_for_naver(title)

    # 2. 태그(Tags) 추출 및 규격화
    extracted_tags = []
    tag_match = re.search(r"\*?태그:?\*?\s*(.+)", content)
    if tag_match:
        raw_tags = tag_match.group(1)
        for t in raw_tags.split():
            clean_t = t.strip().replace(",", "")
            if clean_t.startswith("#"):
                extracted_tags.append(clean_t)
            elif clean_t:
                extracted_tags.append(f"#{clean_t}")

    # 공통 고정 태그와 특정 맞춤 태그 분리
    specific_tags = [t for t in extracted_tags if t not in BASE_TAGS and t not in ["#Quatsch", "#웹소설", "#소설연재"]]
    if not specific_tags:
        # 본문에 특정 태그가 누락되어 있다면 제목 기반 스마트 명사 추출기 호출
        from migrate_tags import generate_specific_tags
        final_tags = generate_specific_tags(title)
    else:
        # 기본 태그 3종 + 고유 태그 2~3종 결합
        final_tags = list(BASE_TAGS)
        for stag in specific_tags[:3]:
            if stag not in final_tags:
                final_tags.append(stag)

    # 3. 소설 본문 영역 분리
    story_section = content
    if "### 2." in content:
        story_section = content.split("### 2.")[1]
    elif "### 2" in content:
        story_section = content.split("### 2")[1]

    # 본문 끝에 붙은 구분선 및 태그 영역 제거
    if "---" in story_section:
        story_section = story_section.split("---")[0]
    if "태그:" in story_section:
        story_section = story_section.split("태그:")[0]

    # [삽화 삽입 위치] 마커를 기준으로 본문을 전반부와 후반부로 분할
    parts = re.split(r"\[(?:삽화 삽입 위치|삽화 위치|삽화|ILLUSTRATION_HERE)\]", story_section, flags=re.IGNORECASE)
    if len(parts) >= 2:
        raw_part1 = parts[0].strip()
        raw_part2 = parts[1].strip()
    else:
        # 마커가 누락된 경우 문단 단위로 절반 위치를 계산하여 분할
        paragraphs = [p for p in story_section.strip().split("\n\n") if p.strip()]
        mid = len(paragraphs) // 2
        raw_part1 = "\n\n".join(paragraphs[:mid])
        raw_part2 = "\n\n".join(paragraphs[mid:])

    # 각 파트별 마크다운 기호 최종 제거
    part1 = clean_markdown_for_naver(raw_part1)
    part2 = clean_markdown_for_naver(raw_part2)

    return title, part1, part2, final_tags

def main():
    """
    CLI 진입점: 인자 파싱 및 3회 재시도 발행 루프 실행
    """
    parser = argparse.ArgumentParser(description="생성된 소설 마크다운과 삽화를 네이버 블로그에 3회 재시도 발행합니다.")
    parser.add_argument("--story", required=True, help="소설 마크다운(.md) 파일 경로")
    parser.add_argument("--image", required=True, help="삽화 이미지(.png) 파일 경로")
    parser.add_argument("--headless", action="store_true", help="브라우저 창을 띄우지 않고 백그라운드에서 실행")
    args = parser.parse_args()

    story_path = Path(args.story)
    image_path = Path(args.image)

    # 원고 파일 존재 여부 방어 검사
    if not story_path.exists():
        err_msg = f"소설 원고 파일을 찾을 수 없습니다: {story_path}"
        print(f"Error: {err_msg}")
        send_failure_email(
            schedule_title="Daily Naver Blog Fantasy Novel",
            error_message=err_msg
        )
        sys.exit(1)

    title, part1, part2, tags = parse_story_markdown(story_path)
    print(f"[*] 파싱 및 정제된 제목: {title}")
    print(f"[*] 본문 1부 길이: {len(part1)}자 (마크다운 문법 제거 완료)")
    print(f"[*] 본문 2부 길이: {len(part2)}자 (마크다운 문법 제거 완료)")
    print(f"[*] 규격화된 태그 목록 (기본 3종 + 특정 2~3종): {tags}")

    MAX_RETRIES = 3
    last_error = ""
    last_tb = ""

    # 최대 3회 재시도 발행 루프
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n{'='*60}")
        print(f"[*] [시도 {attempt}/{MAX_RETRIES}] 네이버 블로그 발행 시작...")
        print(f"{'='*60}")
        try:
            result = publish_to_naver_blog(
                title=title,
                body_part1=part1,
                image_path=str(image_path),
                body_part2=part2,
                tags=tags,
                headless=args.headless
            )
            if result.get("status") == "success":
                print(f"\n[+] [성공] {attempt}번째 시도에서 발행이 성공적으로 완료되었습니다!")
                
                # [연계 1] Google Drive 클라우드 아카이빙
                try:
                    from gdrive_archiver import archive_to_google_drive
                    full_content = f"{part1}\n\n[삽화]\n\n{part2}\n\n태그: {' '.join(tags)}"
                    archive_to_google_drive(title, full_content, str(image_path))
                except Exception as gerr:
                    print(f"[-] Google Drive 아카이빙 알림 (발행은 정상 완료됨): {gerr}")

                # [연계 2] 월별 히스토리(history/{yyyy-mm}.json)에 기록
                try:
                    from history_manager import save_post_to_monthly_history
                    save_post_to_monthly_history({
                        "date": time.strftime("%Y-%m-%d"),
                        "title": title,
                        "tags": tags,
                        "story_file": str(story_path),
                        "image_file": str(image_path),
                        "published_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    print(f"[+] 월별 히스토리(history/{{yyyy-mm}}.json)에 기록 완료!")
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

        # 재시도 전 대기 시간 점진적 증가 (10초, 20초)
        if attempt < MAX_RETRIES:
            wait_time = 10 * attempt
            print(f"[*] {wait_time}초 대기 후 재시도합니다...")
            time.sleep(wait_time)

    # 3회 연속 실패한 경우 최종 장애 처리
    print("\n" + "!" * 70)
    print(f"[!] 3회 재시도 후에도 최종 실패하였습니다.")
    print("[*] 실패 알림 메일 발송을 진행합니다...")
    print("!" * 70 + "\n")

    send_failure_email(
        schedule_title="Daily Naver Blog Fantasy Novel",
        error_message=f"블로그 포스팅 3회 연속 실패. 최종 오류: {last_error}",
        error_traceback=last_tb
    )
    sys.exit(2)

if __name__ == "__main__":
    main()
