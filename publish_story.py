"""
CLI Helper to publish a generated story file to Naver Blog with 3-attempt retry & email fallback.
Cleans markdown syntax for Naver SmartEditor ONE and applies standard typography & tag rules.
Usage:
  python publish_story.py --story path/to/story.md --image path/to/illustration.png
"""
import os
import re
import sys
import json
import time
import traceback
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from naver_publisher import publish_to_naver_blog
from email_notifier import send_failure_email

BASE_TAGS = ["#판타지소설", "#단편소설", "#환상문학"]

def clean_markdown_for_naver(text: str) -> str:
    """
    Strips markdown formatting symbols so text displays cleanly in Naver SmartEditor ONE.
    """
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Remove markdown horizontal rules
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            continue
        # Remove markdown quote prefix ('> ')
        stripped = re.sub(r"^>\s*", "", stripped)
        # Remove markdown headers ('### ')
        stripped = re.sub(r"^#{1,6}\s*", "", stripped)
        # Remove bold/italic markers (**text**, *text*, __text__)
        stripped = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
        stripped = re.sub(r"\*(.*?)\*", r"\1", stripped)
        stripped = re.sub(r"__(.*?)__", r"\1", stripped)
        stripped = re.sub(r"`(.*?)`", r"\1", stripped)
        lines.append(stripped)
    return "\n".join(lines).strip()

def parse_story_markdown(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Extract title
    title = "오늘의 환상 단편"
    title_match = re.search(r"-\s*\*?제목:?\*?\s*(.+)", content)
    if title_match:
        title = title_match.group(1).strip()
    else:
        header_match = re.search(r"^#+\s*(.+)", content, re.MULTILINE)
        if header_match:
            title = header_match.group(1).strip()
    title = clean_markdown_for_naver(title)

    # 2. Extract and format Tags
    # Base tags: #판타지소설, #단편소설, #환상문학
    # Specific tags: 2~3 specific tags
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

    # Separate into base tags and specific tags
    specific_tags = [t for t in extracted_tags if t not in BASE_TAGS and t not in ["#Quatsch", "#웹소설", "#소설연재"]]
    if not specific_tags:
        # Generate smart specific tags from title if none provided
        verb_strip = r'^.*?(?:거래하는|빚는|벼리는|감정하는|잇는|담는|짜\s*넣는|타는|열리는|쓰는|곱씹는|치는|고쳐\s*쓰는|파는|고치는|증류하는|다림질하는|뛰는|청소하는|낚는|먹는|울리는|다듬는|깁는|삼는|지키는|떠난|수확하는|덜어내는|움직이는|자라는|지어지지\s*않은|걸어야만\s*열리는|몰고\s*다니는)\s+'
        adj_strip = r'^(?:아직|이미|스스로|뒤로|잠든|밤마다|매일|내려가기만\s*하는|3초\s*먼저|오만한|시끄러운|낭패\s*본|말\s*많은|늙은|굴러떨어진|삼천\s*살의|비뚤어진|구운|구겨진|뚱뚱한|잃어버린|차가운|노래하는|공중에\s*뜬|도망친|결백한|멈춰\s*선|가짜|고집불통|허공에\s*뜬|구부러진|뒤늦은|말문\s*막힌|노인|엎질러진|은빛)\s+'
        parts = re.split(r'(?:와|과)\s+', title, maxsplit=1)
        for p in parts:
            p_clean = re.sub(verb_strip, '', p)
            p_clean = re.sub(adj_strip, '', p_clean)
            p_clean = re.sub(r'^[은는이가을를의과와]\s*', '', p_clean)
            c = re.sub(r'[^\w가-힣]', '', p_clean)
            if c and len(c) >= 2 and f"#{c}" not in specific_tags:
                specific_tags.append(f"#{c}")

    # Final tags: 3 base tags + 2~3 specific tags
    final_tags = list(BASE_TAGS)
    for stag in specific_tags[:3]:
        if stag not in final_tags:
            final_tags.append(stag)

    # 3. Extract Story Section
    story_section = content
    if "### 2." in content:
        story_section = content.split("### 2.")[1]
    elif "### 2" in content:
        story_section = content.split("### 2")[1]

    # Remove tags and bottom separator from body
    if "---" in story_section:
        story_section = story_section.split("---")[0]
    if "태그:" in story_section:
        story_section = story_section.split("태그:")[0]

    # Split by illustration marker
    parts = re.split(r"\[(?:삽화 삽입 위치|삽화 위치|삽화|ILLUSTRATION_HERE)\]", story_section, flags=re.IGNORECASE)
    if len(parts) >= 2:
        raw_part1 = parts[0].strip()
        raw_part2 = parts[1].strip()
    else:
        paragraphs = [p for p in story_section.strip().split("\n\n") if p.strip()]
        mid = len(paragraphs) // 2
        raw_part1 = "\n\n".join(paragraphs[:mid])
        raw_part2 = "\n\n".join(paragraphs[mid:])

    # Clean markdown syntax from story parts
    part1 = clean_markdown_for_naver(raw_part1)
    part2 = clean_markdown_for_naver(raw_part2)

    return title, part1, part2, final_tags

def main():
    parser = argparse.ArgumentParser(description="Publish generated story to Naver Blog with 3 retries")
    parser.add_argument("--story", required=True, help="Path to story markdown file")
    parser.add_argument("--image", required=True, help="Path to illustration image file")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()

    story_path = Path(args.story)
    image_path = Path(args.image)

    if not story_path.exists():
        err_msg = f"Story file not found: {story_path}"
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
                # Archive to Google Drive: __generated__/gemini-hobby-fantasy-scene
                try:
                    from gdrive_archiver import archive_to_google_drive
                    full_content = f"{part1}\n\n[삽화]\n\n{part2}\n\n태그: {' '.join(tags)}"
                    archive_to_google_drive(title, full_content, str(image_path))
                except Exception as gerr:
                    print(f"[-] Google Drive 아카이빙 알림 (발행은 정상 완료됨): {gerr}")
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

    # If all 3 attempts failed
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
