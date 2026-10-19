"""
Naver Blog Previous Posts Tag Migration Script (Multi-Page Support)
Discovers all existing posts in Quatsch category across all pages and updates their tags to:
- Base tags: #판타지소설, #단편소설, #환상문학
- Specific tags: 2 tailored tags based on post title
"""
import re
import sys
import json
import time
import html
import urllib.request
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

from config_loader import get_config, PROJECT_ROOT

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_TAGS = ["#판타지소설", "#단편소설", "#환상문학"]

# Verified presets
PRESET_TAGS = {
    "224446246932": ["#판타지소설", "#단편소설", "#환상문학", "#별빛의매듭", "#방직공의탑"],
    "224446204944": ["#판타지소설", "#단편소설", "#환상문학", "#양치기와비구름", "#날씨판타지"],
    "224445625593": ["#판타지소설", "#단편소설", "#환상문학", "#한숨유리공", "#유리공예장인"],
    "224445136954": ["#판타지소설", "#단편소설", "#환상문학", "#맹세의대장간", "#구부러진성검"],
    "224443399456": ["#판타지소설", "#단편소설", "#환상문학", "#별감정사", "#가짜운석"]
}

VERB_STRIP_REGEX = (
    r'^.*?(?:거래하는|빚는|벼리는|감정하는|잇는|담는|짜\s*넣는|타는|열리는|쓰는|곱씹는|치는|'
    r'고쳐\s*쓰는|파는|고치는|증류하는|다림질하는|뛰는|청소하는|낚는|먹는|울리는|다듬는|'
    r'깁는|삼는|지키는|떠난|수확하는|덜어내는|움직이는|자라는|지어지지\s*않은|걸어야만\s*열리는|'
    r'몰고\s*다니는|몰고다니는|떨어지는|찾아서)\s+'
)

ADJ_STRIP_REGEX = (
    r'^(?:아직|이미|스스로|뒤로|잠든|밤마다|매일|내려가기만\s*하는|3초\s*먼저|'
    r'오만한|시끄러운|낭패\s*본|말\s*많은|늙은|굴러떨어진|삼천\s*살의|비뚤어진|구운|'
    r'구겨진|뚱뚱한|잃어버린|차가운|노래하는|공중에\s*뜬|도망친|결백한|멈춰\s*선|'
    r'가짜|고집불통|허공에\s*뜬|구부러진|뒤늦은|말문\s*막힌|노인|엎질러진|은빛|저주받은|완벽한|가장\s*무거운)\s+'
)

DISCARD_WORDS = {
    '비밀', '참사', '신청', '접수', '불합격', '적발', '감사', '불량', '의무화', '분쟁',
    '청구서', '비극', '한마디', '상담', '조절', '정기', '명령', '규제', '착용', '보안경',
    '마력의', '4항의', '3장', '제3장', '5G', '일흔일곱', '번의', '경고', '잉여', '완벽한'
}

def clean_chunk(text: str) -> str:
    text = re.sub(VERB_STRIP_REGEX, '', text)
    text = re.sub(ADJ_STRIP_REGEX, '', text)
    # Strip trailing particles like '을', '를', '과', '와', '에', '로'
    text = re.sub(r'(?<=[가-힣])(?:을|를|과|와|에|로)$', '', text)
    # Strip spaces and non-word characters
    clean = re.sub(r'[^\w가-힣]', '', text)
    # If the clean chunk is longer than 8 chars, shorten or extract the core noun
    if len(clean) > 8:
        m = re.search(r'의([가-힣]{2,6})$', clean)
        if m:
            clean = m.group(1)
        elif len(clean) > 8:
            clean = clean[-6:]
    return clean

def generate_specific_tags(title: str) -> list[str]:
    """
    Extracts 2 tailored, meaningful fantasy noun phrases from Korean title,
    filtering out adverbs, verbs, and particles.
    """
    clean_title = re.sub(r'\(.*?\)', '', title).strip()
    parts = re.split(r'(?:와|과)\s+', clean_title, maxsplit=1)
    specific_tags = []

    if len(parts) == 2:
        n1 = clean_chunk(parts[0])
        n2 = clean_chunk(parts[1])
        if n1 and len(n1) >= 2 and n1 not in DISCARD_WORDS and f"#{n1}" not in specific_tags:
            specific_tags.append(f"#{n1}")
        if n2 and len(n2) >= 2 and n2 not in DISCARD_WORDS and f"#{n2}" not in specific_tags:
            specific_tags.append(f"#{n2}")

    # Fallback if specific tags < 2 (e.g. titles without '와/과')
    if len(specific_tags) < 2:
        words = clean_title.split()
        filtered_words = []
        for w in words:
            w = re.sub(r'^[^\w가-힣]+|[^\w가-힣]+$', '', w)
            w = re.sub(r'(?:의|은|는|이|가|을|를|과|와|에|로|에서)$', '', w)
            if len(w) >= 2 and w not in DISCARD_WORDS:
                filtered_words.append(w)

        for w in filtered_words:
            if f"#{w}" not in specific_tags:
                specific_tags.append(f"#{w}")
            if len(specific_tags) >= 2:
                break

    tags = list(BASE_TAGS)
    for stag in specific_tags[:2]:
        if stag not in tags:
            tags.append(stag)

    return tags

def discover_all_posts(blog_id: str, category_no: str = "6", max_pages: int = 35) -> list[dict]:
    """
    Crawls all pagination pages in Quatsch category via Naver PostList API to gather all posts.
    Uses pure HTTP requests to extract socialPluginInfoJson accurately without browser iframe issues.
    """
    print(f"[*] '{blog_id}' 블로그 카테고리(no={category_no})의 전체 포스팅 탐색 시작...")
    all_posts = []
    seen_log_nos = set()

    for pno in range(1, max_pages + 1):
        url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&categoryNo={category_no}&from=postList&currentPage={pno}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode('utf-8', errors='ignore')
                m = re.search(r'id=["\']socialPluginInfoJson["\'][^>]*>(.*?)</', text)
                new_on_page = 0
                if m:
                    raw = html.unescape(m.group(1))
                    items = json.loads(raw)
                    for it in items:
                        lno = str(it.get('logNo'))
                        title = it.get('title', '').strip()
                        if lno and lno not in seen_log_nos:
                            seen_log_nos.add(lno)
                            all_posts.append({'logNo': lno, 'title': title})
                            new_on_page += 1
                if new_on_page == 0 and pno > 1:
                    print(f"[*] 총 {pno - 1}개 페이지에서 {len(all_posts)}편의 글 발견 완료!")
                    break
        except Exception as e:
            print(f"[!] {pno}페이지 탐색 중 오류: {e}")
            break

    return all_posts

from history_manager import save_post_to_monthly_history, get_all_migrated_log_nos

def migrate_tags_for_post(page, blog_id: str, log_no: str, target_tags: list[str]) -> bool:
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

def main():
    parser = argparse.ArgumentParser(description="Migrate tags across all pages of Naver Blog posts")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of posts to migrate (0 = all)")
    parser.add_argument("--skip-migrated", action="store_true", default=True, help="Skip posts already in history.json")
    parser.add_argument("--dry-run", action="store_true", help="Only preview discovered posts and generated tags without modifying blog")
    args = parser.parse_args()

    config = get_config()
    blog_id = config.get("blog_id", "sun_o_glitter")
    profile_dir = Path(config.get("chrome_profile_dir", PROJECT_ROOT / "chrome_profile"))

    already_migrated_ids = get_all_migrated_log_nos()

    print("=" * 70)
    print("네이버 블로그 전체 포스팅 태그 마이그레이션 도구 (다중 페이지 지원)")
    print(f"블로그 ID: {blog_id}")
    print(f"기본 태그: {BASE_TAGS}")
    print(f"이미 완료된 포스팅 수: {len(already_migrated_ids)}편")
    print("=" * 70)

    # Step 1: Discover all posts across all pages reliably via HTTP
    all_posts = discover_all_posts(blog_id)

    # Filter out already migrated posts if requested
    if args.skip_migrated:
        pending_posts = [p for p in all_posts if p['logNo'] not in already_migrated_ids]
    else:
        pending_posts = all_posts

    if args.limit > 0:
        pending_posts = pending_posts[:args.limit]

    print(f"\n[*] 업데이트 대상 글: 총 {len(pending_posts)}편 (전체 {len(all_posts)}편 중)")
    for idx, post in enumerate(pending_posts, 1):
        target_tags = PRESET_TAGS.get(post['logNo'], generate_specific_tags(post['title']))
        print(f"  {idx:2d}. [{post['logNo']}] {post['title']} -> {target_tags}")

    if args.dry_run:
        print("\n[안내] --dry-run 모드이므로 브라우저를 통한 실제 수정을 진행하지 않고 종료합니다.")
        return

    if not pending_posts:
        print("\n[+] 업데이트할 포스팅이 없습니다. 모든 포스팅이 이미 최신 태그로 완료되었습니다.")
        return

    # Step 2: Migrate via Playwright
    success_count = 0
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

        for idx, post in enumerate(pending_posts, 1):
            log_no = post['logNo']
            target_tags = PRESET_TAGS.get(log_no, generate_specific_tags(post['title']))
            print(f"\n>>> [{idx}/{len(pending_posts)}] '{post['title']}' 진행 중...")
            try:
                if migrate_tags_for_post(page, blog_id, log_no, target_tags):
                    success_count += 1
                    save_post_to_monthly_history({
                        "logNo": log_no,
                        "title": post['title'],
                        "tags": target_tags,
                        "migrated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    already_migrated_ids.add(log_no)
            except Exception as e:
                print(f"[!] '{post['title']}' 업데이트 실패: {e}")

        print("\n" + "=" * 70)
        print(f"[+] 마이그레이션 완료: 총 {len(pending_posts)}편 중 {success_count}편 업데이트 성공!")
        print("=" * 70)

        context.close()

if __name__ == "__main__":
    main()
