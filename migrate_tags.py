"""
Naver Blog Previous Posts Tag Migration Script
Discovers existing posts in Quatsch category and updates their tags to:
- Base tags: #판타지소설, #단편소설, #환상문학
- Specific tags: 2~3 tailored tags based on post title & content
"""
import re
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_TAGS = ["#판타지소설", "#단편소설", "#환상문학"]

# Tailored high-quality tags for known previous posts
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
    for w in words[:3]:
        clean = re.sub(r"[^\w가-힣]", "", w)
        if clean and f"#{clean}" not in tags:
            tags.append(f"#{clean}")
    return tags[:5]

def migrate_tags_for_post(page, editor_frame, blog_id: str, log_no: str, target_tags: list[str]) -> bool:
    """Updates tags for a single post using SmartEditor Update URL"""
    update_url = f"https://blog.naver.com/{blog_id}?Redirect=Update&logNo={log_no}"
    print(f"\n[*] 글 수정 페이지 접근: {update_url}")
    page.goto(update_url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    # Re-detect frame
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

def main():
    is_headless = "--headless" in sys.argv
    config_path = Path(r"D:\.repo\.private\artifacts_1\config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    blog_id = config.get("blog_id", "sun_o_glitter")
    profile_dir = Path(config.get("chrome_profile_dir", r"D:\.repo\.private\artifacts_1\chrome_profile"))

    print("=" * 70)
    print("네이버 블로그 이전 포스팅 태그 마이그레이션 도구")
    print(f"블로그 ID: {blog_id}")
    print(f"기본 태그: {BASE_TAGS}")
    print("=" * 70)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=is_headless,
            viewport={"width": 1400, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.new_page()

        # Step 1: Discover posts in Quatsch category
        list_url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&categoryNo=6"
        print(f"[*] Quatsch 카테고리 글 목록 조회: {list_url}")
        page.goto(list_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        frame = page
        for f in page.frames:
            if "mainFrame" in f.name:
                frame = f
                break

        posts_to_update = []
        for a in frame.locator("a").all():
            href = a.get_attribute("href") or ""
            txt = a.inner_text().strip()
            m = re.search(r"logNo=(\d+)", href)
            if not m:
                m = re.search(rf"{blog_id}/(\d+)", href)
            if m:
                log_no = m.group(1)
                if txt and len(txt) > 2 and not any(p['logNo'] == log_no for p in posts_to_update):
                    posts_to_update.append({'logNo': log_no, 'title': txt})

        print(f"\n[*] 마이그레이션 대상 글 총 {len(posts_to_update)}편 발견:")
        for idx, post in enumerate(posts_to_update, 1):
            target_tags = PRESET_TAGS.get(post['logNo'], generate_specific_tags(post['title']))
            print(f"  {idx}. [{post['logNo']}] {post['title']} -> 태그: {target_tags}")

        # Step 2: Migrate each post
        success_count = 0
        for idx, post in enumerate(posts_to_update, 1):
            log_no = post['logNo']
            target_tags = PRESET_TAGS.get(log_no, generate_specific_tags(post['title']))
            print(f"\n>>> [{idx}/{len(posts_to_update)}] '{post['title']}' 태그 업데이트 진행...")
            try:
                if migrate_tags_for_post(page, frame, blog_id, log_no, target_tags):
                    success_count += 1
            except Exception as e:
                print(f"[!] '{post['title']}' 업데이트 중 오류 발생 (건너뜀): {e}")

        print("\n" + "=" * 70)
        print(f"[+] 태그 마이그레이션 완료: 총 {len(posts_to_update)}편 중 {success_count}편 업데이트 성공!")
        print("=" * 70)

        context.close()

if __name__ == "__main__":
    main()
