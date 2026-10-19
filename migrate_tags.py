"""
Naver Blog Previous Posts Tag Migration Script (Multi-Page Support)
Discovers all existing posts in Quatsch category across all pages and updates their tags to:
- Base tags: #판타지소설, #단편소설, #환상문학
- Specific tags: 2~3 tailored tags based on post title
"""
import re
import sys
import json
import time
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_TAGS = ["#판타지소설", "#단편소설", "#환상문학"]

PRESET_TAGS = {
    "224446246932": ["#판타지소설", "#단편소설", "#환상문학", "#별빛의매듭", "#방직공의탑"],
    "224446204944": ["#판타지소설", "#단편소설", "#환상문학", "#양치기와비구름", "#날씨판타지"],
    "224445625593": ["#판타지소설", "#단편소설", "#환상문학", "#한숨유리공", "#유리공예장인"],
    "224445136954": ["#판타지소설", "#단편소설", "#환상문학", "#맹세의대장간", "#구부러진성검"],
    "224443399456": ["#판타지소설", "#단편소설", "#환상문학", "#별감정사", "#가짜운석"]
}

def generate_specific_tags(title: str) -> list[str]:
    """Extracts 2-3 specific tags from title if not in preset"""
    words = [w for w in re.split(r"\s+", title) if len(w) >= 2]
    tags = list(BASE_TAGS)
    for w in words:
        clean = re.sub(r"[^\w가-힣]", "", w)
        if clean and len(clean) >= 2 and f"#{clean}" not in tags:
            tags.append(f"#{clean}")
        if len(tags) >= 5:
            break
    return tags

def migrate_tags_for_post(page, editor_frame, blog_id: str, log_no: str, target_tags: list[str]) -> bool:
    """Updates tags for a single post using SmartEditor Update URL"""
    update_url = f"https://blog.naver.com/{blog_id}?Redirect=Update&logNo={log_no}"
    print(f"\n[*] 글 수정 페이지 접근: {update_url}")
    page.goto(update_url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    frame = page
    for f in page.frames:
        if "mainFrame" in f.name:
            frame = f
            break

    # Dismiss popup if any
    try:
        cancel_btn = frame.locator('div[data-group="popupLayer"] button.se-popup-button-cancel').first
        if cancel_btn.is_visible(timeout=2000):
            cancel_btn.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    # Open publish layer
    print("[*] 상단 '발행' 버튼 클릭...")
    pub_btn = frame.locator('button[data-click-area="tpb.publish"]').first
    pub_btn.click()
    page.wait_for_timeout(2000)

    # Remove existing tags if any
    try:
        del_btns = frame.locator('button[class*="tag_delete"], button[class*="btn_delete"]').all()
        for d in del_btns:
            d.click()
            page.wait_for_timeout(100)
    except Exception:
        pass

    # Input new tags
    print(f"[*] 태그 등록 중: {target_tags}")
    tag_input = frame.locator('input[class*="tag_input"]').first
    if tag_input.is_visible(timeout=3000):
        tag_input.click()
        for tag in target_tags:
            clean_tag = tag.replace("#", "").strip()
            if clean_tag:
                tag_input.fill(clean_tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(250)
        print("[+] 태그 입력 완료")
    else:
        print("[!] 태그 입력 필드를 찾지 못했습니다.")

    # Confirm publish
    print("[*] 최종 수정 발행 클릭...")
    confirm_btn = frame.locator('button[data-click-area="tpb*i.publish"]').first
    if not confirm_btn.is_visible(timeout=3000):
        confirm_btn = frame.locator('.layer_publish button:has-text("발행"), button.confirm_btn__byZZW').first

    confirm_btn.click()
    print("[*] 수정 발행 저장 대기 중 (7초)...")
    page.wait_for_timeout(7000)
    print(f"[+] logNo: {log_no} 태그 업데이트 완료!")
    return True

def discover_all_posts(page, blog_id: str, max_pages: int = 15) -> list[dict]:
    """Crawls all pagination pages in Quatsch category to gather all posts"""
    print(f"[*] Quatsch 카테고리의 모든 페이지(최대 {max_pages}페이지) 탐색 시작...")
    all_posts = {}

    for pno in range(1, max_pages + 1):
        url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&categoryNo=6&from=postList&currentPage={pno}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        frame = page
        for f in page.frames:
            if "mainFrame" in f.name:
                frame = f
                break

        count_before = len(all_posts)
        for a in frame.locator('a').all():
            href = a.get_attribute('href') or ''
            m = re.search(r"logNo=(\d+)", href)
            if m:
                lno = m.group(1)
                txt = a.inner_text().strip()
                if txt and len(txt) > 2 and lno not in all_posts:
                    all_posts[lno] = txt

        new_found = len(all_posts) - count_before
        if new_found == 0 and pno > 3:
            # Reached end of pagination
            break

    result = [{'logNo': k, 'title': v} for k, v in all_posts.items()]
    print(f"[+] 총 {len(result)}편의 글 발견 완료!")
    return result

def main():
    parser = argparse.ArgumentParser(description="Migrate tags across all pages of Naver Blog posts")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of posts to migrate (0 = all)")
    parser.add_argument("--skip-migrated", action="store_true", default=True, help="Skip posts already in history.json")
    args = parser.parse_args()

    config_path = Path(r"D:\.repo\.private\artifacts_1\config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    blog_id = config.get("blog_id", "sun_o_glitter")
    profile_dir = Path(config.get("chrome_profile_dir", r"D:\.repo\.private\artifacts_1\chrome_profile"))
    history_file = Path(config.get("history_file", r"D:\.repo\.private\artifacts_1\history.json"))

    already_migrated_ids = set()
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                hdata = json.load(f)
                already_migrated_ids = {p.get("logNo") for p in hdata.get("posts", []) if p.get("logNo")}
        except Exception:
            pass

    print("=" * 70)
    print("네이버 블로그 전체 포스팅 태그 마이그레이션 도구 (다중 페이지 지원)")
    print(f"블로그 ID: {blog_id}")
    print(f"기본 태그: {BASE_TAGS}")
    print(f"이미 완료된 포스팅 수: {len(already_migrated_ids)}편")
    print("=" * 70)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=args.headless,
            viewport={"width": 1400, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.new_page()

        # Step 1: Discover all posts across all pages
        all_posts = discover_all_posts(page, blog_id)

        # Filter out already migrated posts if requested
        if args.skip_migrated:
            pending_posts = [p for p in all_posts if p['logNo'] not in already_migrated_ids]
        else:
            pending_posts = all_posts

        if args.limit > 0:
            pending_posts = pending_posts[:args.limit]

        print(f"\n[*] 이번 실행에서 업데이트할 글: 총 {len(pending_posts)}편")
        for idx, post in enumerate(pending_posts, 1):
            target_tags = PRESET_TAGS.get(post['logNo'], generate_specific_tags(post['title']))
            print(f"  {idx}. [{post['logNo']}] {post['title']} -> {target_tags}")

        # Step 2: Migrate
        success_count = 0
        frame = page
        for idx, post in enumerate(pending_posts, 1):
            log_no = post['logNo']
            target_tags = PRESET_TAGS.get(log_no, generate_specific_tags(post['title']))
            print(f"\n>>> [{idx}/{len(pending_posts)}] '{post['title']}' 진행 중...")
            try:
                if migrate_tags_for_post(page, frame, blog_id, log_no, target_tags):
                    success_count += 1
                    # Record to history.json
                    already_migrated_ids.add(log_no)
            except Exception as e:
                print(f"[!] '{post['title']}' 업데이트 실패: {e}")

        print("\n" + "=" * 70)
        print(f"[+] 마이그레이션 완료: 총 {len(pending_posts)}편 중 {success_count}편 업데이트 성공!")
        print("=" * 70)

        context.close()

if __name__ == "__main__":
    main()
