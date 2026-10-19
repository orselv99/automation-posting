"""
CLI Helper to publish a generated story file to Naver Blog with 3-attempt retry & email fallback.
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

def parse_story_markdown(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title
    title = "오늘의 환상 단편"
    title_match = re.search(r"-\s*\*\*제목:\*\*\s*(.+)", content)
    if title_match:
        title = title_match.group(1).strip()
    else:
        header_match = re.search(r"^#+\s*(.+)", content, re.MULTILINE)
        if header_match:
            title = header_match.group(1).strip()

    # Extract Tags
    tags = []
    tag_match = re.search(r"\*\*태그:\*\*\s*(.+)", content)
    if tag_match:
        raw_tags = tag_match.group(1)
        tags = [t.strip() for t in raw_tags.split() if t.startswith("#")]
    if not tags:
        tags = ["#판타지소설", "#단편소설", "#환상문학", "#Quatsch"]

    # Extract Story Section (under ### 2. 📖 마스터피스 단편 소설)
    story_section = content
    if "### 2." in content:
        story_section = content.split("### 2.")[1]
    elif "### 2" in content:
        story_section = content.split("### 2")[1]

    # Remove tags and separator at the bottom
    if "---" in story_section:
        story_section = story_section.split("---")[0]

    # Split by illustration marker
    parts = re.split(r"\[(?:삽화 삽입 위치|삽화 위치|삽화|ILLUSTRATION_HERE)\]", story_section, flags=re.IGNORECASE)
    if len(parts) >= 2:
        part1 = parts[0].strip()
        part2 = parts[1].strip()
    else:
        paragraphs = [p for p in story_section.strip().split("\n\n") if p.strip()]
        mid = len(paragraphs) // 2
        part1 = "\n\n".join(paragraphs[:mid])
        part2 = "\n\n".join(paragraphs[mid:])

    return title, part1, part2, tags

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
    print(f"[*] 파싱된 제목: {title}")
    print(f"[*] 본문 1부 길이: {len(part1)}자 / 2부 길이: {len(part2)}자")
    print(f"[*] 태그 목록: {tags}")

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
