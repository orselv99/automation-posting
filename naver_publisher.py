"""
[네이버 스마트에디터 ONE 자동 포스팅 모듈 (naver_publisher.py)]

주니어 개발자를 위한 웹 자동화(Playwright) 기술 안내:
1. 스마트에디터 ONE의 특성과 React 가상 DOM (Virtual DOM):
   - 네이버 블로그 에디터(SmartEditor ONE)는 단순한 HTML textarea가 아니라, React 기반의 contenteditable 복합 캔버스입니다.
   - 일반 자바스크립트나 셀렉터로 `element.innerHTML = '내용'`처럼 직접 DOM을 조작하면,
     React의 내부 상태(State)와 동기화되지 않아 글이 사라지거나 발행 시 빈 글이 저장됩니다.
   - 따라서 실제 사용자가 키보드를 치는 것처럼 `keyboard.insert_text()`와 `keyboard.press("Enter")` 이벤트를
     발생시켜야 에디터의 State가 올바르게 갱신됩니다.

2. iframe(mainFrame) 분기 처리:
   - 네이버 블로그는 접속 주소나 환경에 따라 최상위 페이지에 에디터가 바로 뜨거나,
     `iframe name="mainFrame"` 내부에 에디터가 감싸져서 로드될 수 있습니다.
   - 따라서 `page.frames`를 순회하여 mainFrame이 존재하면 해당 프레임 콘텍스트로 전환하는 방어 로직을 갖춥니다.

3. 예외 팝업 핸들링:
   - 이전 작성 중이던 임시 저장 글이 남아있으면 '작성 중인 글이 있습니다' 팝업이 에디터를 가로막습니다.
   - 이 경우 자동으로 '취소' 버튼을 클릭하여 새 글 작성 상태로 초기화합니다.
"""
import os
import sys
import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# Windows 터미널 한글 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config_loader import get_config, PROJECT_ROOT

# 네이버 스마트에디터 ONE 제공 인용구 6종 스타일 매핑
ALL_QUOTE_STYLES = [
    ("default", "따옴표"),
    ("quotation_line", "버티컬 라인"),
    ("quotation_bubble", "말풍선"),
    ("quotation_underline", "라인&따옴표"),
    ("quotation_postit", "포스트잇"),
    ("quotation_corner", "프레임")
]

QUOTE_STYLE_MAP = {
    "따옴표": "default", "default": "default", "quote": "default",
    "버티컬라인": "quotation_line", "버티컬 라인": "quotation_line", "quotation_line": "quotation_line", "line": "quotation_line",
    "말풍선": "quotation_bubble", "quotation_bubble": "quotation_bubble", "bubble": "quotation_bubble",
    "라인따옴표": "quotation_underline", "라인&따옴표": "quotation_underline", "밑줄": "quotation_underline", "quotation_underline": "quotation_underline", "underline": "quotation_underline",
    "포스트잇": "quotation_postit", "메모지": "quotation_postit", "quotation_postit": "quotation_postit", "postit": "quotation_postit",
    "프레임": "quotation_corner", "액자": "quotation_corner", "모서리": "quotation_corner", "quotation_corner": "quotation_corner", "corner": "quotation_corner"
}

def publish_to_naver_blog(
    title: str,
    body_part1: str,
    image_path: str,
    body_part2: str,
    tags: list[str],
    quote: dict = None,
    config_path: str = None,
    headless: bool = False
) -> dict:
    """
    Playwright를 사용하여 네이버 블로그 스마트에디터 ONE에 소설과 삽화를 입력하고 즉시 발행합니다.
    
    매개변수:
    - title: 소설 제목
    - body_part1: 삽화 이전의 본문 전반부
    - image_path: 본문 중간에 삽입할 삽화 이미지 경로
    - body_part2: 삽화 이후의 본문 후반부
    - tags: 등록할 태그 리스트 (기본 3종 + 고유 2~3종)
    - quote: 선택적 버티컬 라인 인용구 딕셔너리 ({"text": "...", "source": "..."})
    - headless: 백그라운드 무화면 브라우저 모드 여부
    """
    config = get_config()

    blog_id = config.get("blog_id", "sun_o_glitter")
    category_name = config.get("category_name", "Quatsch")
    profile_dir = Path(config.get("chrome_profile_dir", PROJECT_ROOT / "chrome_profile"))
    output_dir = Path(config.get("output_dir", PROJECT_ROOT / "generated"))
    output_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = output_dir / f"publish_result_{int(time.time())}.png"

    print(f"[*] 블로그 자동 발행 시작: https://blog.naver.com/{blog_id}")
    print(f"[*] 대상 카테고리: {category_name}")
    print(f"[*] 글 제목: {title}")
    print(f"[*] 삽화 경로: {image_path}")

    with sync_playwright() as p:
        # 사전 로그인된 크롬 프로필 디렉터리를 로드하여 세션 유지
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
        # 네이버 블로그 스마트에디터 글쓰기 URL 진입
        write_url = f"https://blog.naver.com/{blog_id}?Redirect=Write&"
        print(f"[*] 글쓰기 페이지 이동: {write_url}")
        page.goto(write_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        # 로그인 풀림 또는 세션 만료 검사 (nidlogin 리다이렉트 발생 여부)
        current_url = page.url
        if "nidlogin" in current_url or "nid.naver.com" in current_url:
            print("\n" + "!" * 60)
            print("[!] 네이버 로그인이 필요합니다!")
            print(f"[!] 현재 접속 페이지: {current_url}")
            print(f"[!] 전용 프로필({profile_dir})에 로그인 세션이 없습니다.")
            print("[!] 터미널에서 다음 명령어를 실행하여 1회 로그인해 주세요:")
            print("    python login_naver.py")
            print("!" * 60 + "\n")
            page.screenshot(path=str(output_dir / "login_required.png"))
            context.close()
            return {
                "status": "error",
                "error": "로그인이 필요합니다. 터미널에서 'python login_naver.py'를 실행해 로그인 세션을 등록해 주세요."
            }

        # mainFrame iframe 감싸임 여부 확인
        editor_frame = page
        for frame in page.frames:
            if "mainFrame" in frame.name:
                editor_frame = frame
                print("[*] mainFrame 프레임 발견 및 전환 완료")
                break

        # 팝업 1: '작성 중인 글이 있습니다' 팝업 방어 처리 -> 새 글 작성을 위해 '취소' 클릭
        try:
            cancel_btn = editor_frame.locator('div[data-group="popupLayer"] button.se-popup-button-cancel').first
            if cancel_btn.is_visible(timeout=3000):
                print("[*] 이전 작성 중인 글 팝업 발견 -> '취소' 클릭하여 새 글 작성")
                cancel_btn.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # 팝업 2: 스마트에디터 신규 도움말 패널이 떠있는 경우 닫기
        try:
            help_close = editor_frame.locator(".se-help-panel-close-button, button[aria-label='도움말 닫기']").first
            if help_close.is_visible(timeout=1500):
                help_close.click()
        except Exception:
            pass

        # [단계 1: 제목 입력]
        print("[*] 제목 입력 시도 중...")
        title_locator = editor_frame.locator(".se-documentTitle, .se-title-text, .se-ff-nanumgothic.se-fs32").first
        if not title_locator.is_visible(timeout=5000):
            title_locator = editor_frame.locator("p.se-text-paragraph, [contenteditable='true']").first

        title_locator.click()
        page.wait_for_timeout(500)
        # insert_text를 사용하여 가상 DOM 이벤트 트리거
        page.keyboard.insert_text(title)
        page.keyboard.press("Enter")
        page.wait_for_timeout(800)
        print("[+] 제목 입력 완료")

        # [단계 1.5: 선택적 6종 인용구 입력 (지정 또는 6종 전체 랜덤)]
        if quote and quote.get("text"):
            req_style = quote.get("style")
            if req_style and req_style in QUOTE_STYLE_MAP:
                style_code = QUOTE_STYLE_MAP[req_style]
                style_name = next((name for code, name in ALL_QUOTE_STYLES if code == style_code), req_style)
            else:
                style_code, style_name = random.choice(ALL_QUOTE_STYLES)

            print(f"[*] 스마트에디터 인용구 입력 중 (스타일: '{style_name}' [{style_code}]): '{quote.get('text')[:30]}...'")
            try:
                # 1. 툴바의 인용구 드롭다운 옵션 버튼 클릭
                q_opt_btn = editor_frame.locator("button.se-document-toolbar-select-option-button[data-name='quotation']").first
                if not q_opt_btn.is_visible(timeout=3000):
                    q_opt_btn = editor_frame.locator("button[data-name='quotation']").first

                if q_opt_btn.is_visible(timeout=3000):
                    q_opt_btn.click()
                    page.wait_for_timeout(400)

                    # 2. 선택된 인용구 스타일 옵션 버튼 클릭
                    target_btn = editor_frame.locator(
                        f"button.se-toolbar-option-insert-quotation-{style_code}-button, button[data-value='{style_code}']"
                    ).first
                    if target_btn.is_visible(timeout=2000):
                        target_btn.click()
                        page.wait_for_timeout(600)

                        # 3. 인용구 본문 텍스트 입력
                        page.keyboard.insert_text(quote["text"])
                        page.wait_for_timeout(300)

                        # 4. 출처 텍스트가 있을 경우 출처 영역 클릭 후 입력
                        if quote.get("source"):
                            cite_p = editor_frame.locator("div.se-cite p, .se-quotation-source").first
                            if cite_p.is_visible(timeout=2000):
                                cite_p.click()
                                page.wait_for_timeout(300)
                                page.keyboard.insert_text(quote["source"])
                                page.wait_for_timeout(300)

                        # 5. 인용구 블록 밖으로 나와 일반 본문 영역으로 커서 이동
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("ArrowDown")
                        page.wait_for_timeout(300)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(300)
                        print(f"[+] '{style_name}'({style_code}) 인용구 입력 완료")
            except Exception as qe:
                print(f"[!] 인용구 입력 중 알림 (본문 계속 진행): {qe}")

        # [단계 2: 본문 전반부 입력]
        print("[*] 소설 본문 전반부 입력 중...")
        for paragraph in body_part1.strip("\r\n").split("\n"):
            line = paragraph.strip(" \t\r\n")
            if not line:
                page.keyboard.press("Enter")
                continue
            page.keyboard.insert_text(line)
            page.keyboard.press("Enter")
            page.wait_for_timeout(30)

        page.wait_for_timeout(1000)
        print("[+] 소설 본문 전반부 입력 완료")

        # [단계 3: 삽화 이미지 업로드]
        # 에디터 툴바의 사진 버튼을 클릭하고 Playwright의 file_chooser 이벤트로 이미지 주입
        if image_path and os.path.exists(image_path):
            print(f"[*] 삽화 업로드 중: {image_path}")
            abs_image_path = os.path.abspath(image_path)
            try:
                pic_btn = editor_frame.locator("button[data-name='image'], button.se-image-toolbar-button, button:has-text('사진')").first
                if pic_btn.is_visible(timeout=3000):
                    with page.expect_file_chooser(timeout=6000) as fc_info:
                        pic_btn.click()
                    file_chooser = fc_info.value
                    file_chooser.set_files(abs_image_path)
                    print("[*] 파일 선택기를 통해 이미지 첨부 성공")
                else:
                    file_input = editor_frame.locator("input[type='file'][accept*='image']").first
                    file_input.set_input_files(abs_image_path)
                    print("[*] 파일 인풋을 통해 이미지 첨부 성공")

                # 네이버 이미지 업로드 및 CDN 렌더링 완료 대기
                print("[*] 이미지 업로드 완료 대기 중 (6초)...")
                page.wait_for_timeout(6000)
                print("[+] 삽화 이미지 업로드 및 삽입 완료")
            except Exception as e:
                print(f"[!] 이미지 첨부 중 알림: {e}")
                try:
                    file_input = editor_frame.locator("input[type='file'][accept*='image']").first
                    file_input.set_input_files(abs_image_path)
                    page.wait_for_timeout(5000)
                except Exception as e2:
                    print(f"[!] 이미지 재시도 실패: {e2}")

        # 업로드된 이미지 블록 하단으로 커서를 이동하여 후반부 본문 작성 위치 확보
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)

        # [단계 4: 본문 후반부 입력]
        print("[*] 소설 본문 후반부 입력 중...")
        for paragraph in body_part2.strip("\r\n").split("\n"):
            line = paragraph.strip(" \t\r\n")
            if not line:
                page.keyboard.press("Enter")
                continue
            page.keyboard.insert_text(line)
            page.keyboard.press("Enter")
            page.wait_for_timeout(30)

        page.wait_for_timeout(1500)
        print("[+] 소설 본문 후반부 입력 완료")

        # [단계 4.5: 본문 타이포그래피 서식 스타일 일괄 적용]
        try:
            from editor_style import apply_post_style
            style_cfg = config.get("post_style", {})
            apply_post_style(editor_frame, page, style_cfg)
        except Exception as se:
            print(f"[-] 서식 스타일 적용 알림 (기본값 유지): {se}")

        # [단계 5: 우측 상단 '발행' 버튼 클릭하여 설정 레이어 열기]
        print("[*] 상단 '발행' 버튼 클릭하여 발행 레이어 열기...")
        publish_top_btn = editor_frame.locator("button[data-click-area='tpb.publish']").first
        publish_top_btn.click()
        page.wait_for_timeout(2500)

        # [단계 6: 카테고리 선택]
        try:
            print(f"[*] 카테고리 '{category_name}' 확인/선택 시도...")
            select_btn = editor_frame.locator("button.selectbox_button__IxraO, button[class*='selectbox_button']").first
            if select_btn.is_visible(timeout=3000):
                current_cat = select_btn.inner_text().strip()
                if category_name not in current_cat:
                    select_btn.click()
                    page.wait_for_timeout(500)
                    editor_frame.locator(f"li:has-text('{category_name}'), span:has-text('{category_name}')").first.click()
                    page.wait_for_timeout(500)
                    print(f"[+] 카테고리 '{category_name}' 선택 완료")
                else:
                    print(f"[+] 카테고리가 이미 '{category_name}'으로 지정되어 있습니다.")
        except Exception as e:
            print(f"[-] 카테고리 선택 알림 (기본값 유지): {e}")

        # [단계 7: 태그 입력]
        if tags:
            try:
                print(f"[*] 태그 입력 시도: {tags[:5]}...")
                tag_input = editor_frame.locator("input[class*='tag_input']").first
                if tag_input.is_visible(timeout=3000):
                    tag_input.click()
                    for tag in tags[:10]:
                        clean_tag = tag.replace("#", "").strip()
                        if clean_tag:
                            tag_input.fill(clean_tag)
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(250)
                    print("[+] 태그 입력 완료")
            except Exception as e:
                print(f"[-] 태그 입력 알림: {e}")

        # [단계 8: 최종 발행 버튼 클릭]
        print("[*] 최종 발행 버튼 클릭...")
        confirm_btn = editor_frame.locator("button[data-click-area='tpb*i.publish']").first
        if not confirm_btn.is_visible(timeout=3000):
            confirm_btn = editor_frame.locator(".layer_publish button:has-text('발행'), button.confirm_btn__byZZW").first

        confirm_btn.click()
        print("[*] 최종 발행 처리 대기 중 (8초)...")
        page.wait_for_timeout(8000)

        # 성공 증빙용 스크린샷 캡처
        page.screenshot(path=str(screenshot_path))
        print(f"[+] 발행 완료 화면 캡처 저장: {screenshot_path}")

        context.close()

    return {
        "status": "success",
        "title": title,
        "screenshot": str(screenshot_path)
    }

if __name__ == "__main__":
    print("naver_publisher 모듈이 로드되었습니다. 실제 발행은 publish_story.py를 실행하세요.")
