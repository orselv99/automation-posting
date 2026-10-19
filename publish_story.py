"""
CLI Helper to publish a generated story file to Naver Blog.
Usage:
  python publish_story.py --story path/to/story.md --image path/to/illustration.png
"""
import os
import re
import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from naver_publisher import publish_to_naver_blog

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
        tags = ["#판타지소설", "#단편소설", "#자작소설", "#웹소설", "#Quatsch"]

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
    parser = argparse.ArgumentParser(description="Publish generated story to Naver Blog")
    parser.add_argument("--story", required=True, help="Path to story markdown file")
    parser.add_argument("--image", required=True, help="Path to illustration image file")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()

    story_path = Path(args.story)
    image_path = Path(args.image)

    if not story_path.exists():
        print(f"Error: Story file not found: {story_path}")
        sys.exit(1)

    title, part1, part2, tags = parse_story_markdown(story_path)
    print(f"[*] 파싱된 제목: {title}")
    print(f"[*] 본문 1부 길이: {len(part1)}자 / 2부 길이: {len(part2)}자")
    print(f"[*] 태그 목록: {tags}")

    result = publish_to_naver_blog(
        title=title,
        body_part1=part1,
        image_path=str(image_path),
        body_part2=part2,
        tags=tags,
        headless=args.headless
    )

    print("[*] 실행 결과:", result)
    if result.get("status") == "error":
        sys.exit(2)

if __name__ == "__main__":
    main()
