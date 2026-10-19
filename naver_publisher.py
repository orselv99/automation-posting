"""
Naver Blog SmartEditor ONE Playwright Publisher
Automates writing, image uploading, and publishing on Naver Blog.
"""
import os
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

def publish_to_naver_blog(
    title: str,
    body_part1: str,
    image_path: str,
    body_part2: str,
    tags: list[str],
    config_path: str = r"D:\.repo\.private\artifacts_1\config.json",
    headless: bool = False
) -> dict:
    """
    Publishes a novel and illustration to Naver Blog using Playwright.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    blog_id = config.get("blog_id", "sun_o_glitter")
    category_name = config.get("category_name", "Quatsch")
    profile_dir = Path(config.get("chrome_profile_dir", r"D:\.repo\.private\artifacts_1\chrome_profile"))
    output_dir = Path(config.get("output_dir", r"D:\.repo\.private\artifacts_1\generated"))
    output_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = output_dir / f"publish_{int(time.time())}.png"

    print(f"[*] 블로그 자동 발행 시작: https://blog.naver.com/{blog_id}")
    print(f"[*] 대상 카테고리: {category_name}")
    print(f"[*] 글 제목: {title}")
    print(f"[*] 삽화 경로: {image_path}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=headless,
            viewport={"width": 1400, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.new_page()
        # Navigate to blog write URL
        write_url = f"https://blog.naver.com/{blog_id}?Redirect=Write&"
        print(f"[*] 글쓰기 페이지 이동: {write_url}")
        page.goto(write_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        # Check if wrapped in mainFrame iframe or direct page
        editor_frame = page
        frames = page.frames
        for frame in frames:
            if "mainFrame" in frame.name:
                editor_frame = frame
                print("[*] mainFrame 프레임 발견 및 전환 완료")
                break

        # Check for popup: '작성 중인 글이 있습니다' -> Click cancel to start fresh
        try:
            cancel_btn = editor_frame.locator(".se-popup-button-cancel, .se-popup-cancel, button:has-text('취소')").first
            if cancel_btn.is_visible(timeout=2500):
                print("[*] 이전 작성 중인 글 팝업 발견 -> '취소' 클릭하여 새 글 작성")
                cancel_btn.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # Check for help tooltip or tutorial popup
        try:
            help_close = editor_frame.locator(".se-help-panel-close-button, button[aria-label='도움말 닫기']").first
            if help_close.is_visible(timeout=1500):
                help_close.click()
        except Exception:
            pass

        # 1. Input Title
        print("[*] 제목 입력 시도 중...")
        title_locator = editor_frame.locator(".se-documentTitle, .se-title-text, .se-ff-nanumgothic.se-fs32").first
        if not title_locator.is_visible(timeout=5000):
            title_locator = editor_frame.locator("p.se-text-paragraph, [contenteditable='true']").first

        title_locator.click()
        page.wait_for_timeout(500)
        editor_frame.keyboard.type(title, delay=30)
        editor_frame.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        print("[+] 제목 입력 완료")

        # 2. Input Part 1 of Novel
        print("[*] 소설 본문 전반부 입력 중...")
        # Split body part 1 by newlines to keep paragraph formatting
        for paragraph in body_part1.strip().split("\n"):
            line = paragraph.strip()
            if not line:
                editor_frame.keyboard.press("Enter")
                continue
            editor_frame.keyboard.type(line, delay=15)
            editor_frame.keyboard.press("Enter")
            page.wait_for_timeout(100)

        page.wait_for_timeout(1000)
        print("[+] 소설 본문 전반부 입력 완료")

        # 3. Upload Illustration Image at current position
        if image_path and os.path.exists(image_path):
            print(f"[*] 삽화 업로드 중: {image_path}")
            # Locate file input element for image upload
            try:
                file_input = editor_frame.locator("input[type='file'][accept*='image']").first
                if not file_input.count():
                    # Click picture toolbar button to trigger input
                    pic_btn = editor_frame.locator("button[data-name='image'], button.se-image-toolbar-button, button:has-text('사진')").first
                    if pic_btn.is_visible(timeout=3000):
                        pic_btn.click()
                        page.wait_for_timeout(1000)
                    file_input = editor_frame.locator("input[type='file'][accept*='image']").first

                file_input.set_input_files(image_path)
                print("[*] 이미지 파일 첨부 성공, 업로드 대기 중...")
                page.wait_for_timeout(5000)
                print("[+] 삽화 이미지 업로드 및 삽입 완료")
            except Exception as e:
                print(f"[!] 이미지 업로드 중 예외 발생 (건너뜀): {e}")

        # 4. Input Part 2 of Novel
        print("[*] 소설 본문 후반부 입력 중...")
        for paragraph in body_part2.strip().split("\n"):
            line = paragraph.strip()
            if not line:
                editor_frame.keyboard.press("Enter")
                continue
            editor_frame.keyboard.type(line, delay=15)
            editor_frame.keyboard.press("Enter")
            page.wait_for_timeout(100)

        page.wait_for_timeout(1500)
        print("[+] 소설 본문 후반부 입력 완료")

        # 5. Click Top "발행" button
        print("[*] '발행' 버튼 클릭하여 발행 레이어 열기...")
        publish_top_btn = editor_frame.locator("button:has-text('발행'), button[class*='publish_btn']").first
        publish_top_btn.click()
        page.wait_for_timeout(2000)

        # 6. Select Category in Publish Layer
        try:
            print(f"[*] 카테고리 '{category_name}' 확인/선택 시도...")
            cat_item = editor_frame.locator(f"label:has-text('{category_name}'), span:has-text('{category_name}'), div:has-text('{category_name}')").first
            if cat_item.is_visible(timeout=3000):
                cat_item.click()
                print(f"[+] 카테고리 '{category_name}' 선택 완료")
        except Exception as e:
            print(f"[-] 카테고리 선택 알림 (기본값 유지): {e}")

        # 7. Input Tags
        if tags:
            try:
                print(f"[*] 태그 입력 시도: {tags[:5]}...")
                tag_input = editor_frame.locator("input[placeholder*='태그'], .tag_input__... input, input.tag_input").first
                if tag_input.is_visible(timeout=3000):
                    tag_input.click()
                    for tag in tags[:10]:
                        clean_tag = tag.replace("#", "").strip()
                        if clean_tag:
                            tag_input.fill(clean_tag)
                            editor_frame.keyboard.press("Enter")
                            page.wait_for_timeout(300)
                    print("[+] 태그 입력 완료")
            except Exception as e:
                print(f"[-] 태그 입력 알림: {e}")

        # 8. Confirm Publication
        print("[*] 최종 발행 버튼 클릭...")
        confirm_btn = editor_frame.locator("button.confirm_btn__..., button[class*='confirm_btn'], button[type='submit']:has-text('발행')").first
        if not confirm_btn.is_visible(timeout=3000):
            # Fallback to any visible publish button inside layer
            confirm_btn = editor_frame.locator(".layer_publish button:has-text('발행')").first

        confirm_btn.click()
        print("[*] 최종 발행 처리 대기 중...")
        page.wait_for_timeout(7000)

        # Take screenshot for proof
        page.screenshot(path=str(screenshot_path))
        print(f"[+] 발행 완료 화면 캡처 저장: {screenshot_path}")

        context.close()

    return {
        "status": "success",
        "title": title,
        "screenshot": str(screenshot_path)
    }

if __name__ == "__main__":
    print("naver_publisher module loaded. Run run_daily_post.py to execute the full pipeline.")
