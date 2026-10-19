"""
[네이버 블로그 1회성 사전 로그인 도구 (login_naver.py)]

주니어 개발자를 위한 브라우저 자동화 안내:
1. 일반 브라우저 자동화(launch) vs 영속 세션(launch_persistent_context):
   - 일반 `p.chromium.launch()`는 실행할 때마다 임시 프로필을 만들어 종료 시 쿠키와 세션이 사라집니다.
   - 하지만 네이버 로그인은 캡차(CAPTCHA), 2단계 인증, 기기 등록 등 자동화 코드로 뚫기 까다로운 보안 장치가 많습니다.
   - 따라서 `launch_persistent_context`를 사용하여 로컬 디스크(`chrome_profile/` 폴더)에 사용자 프로필과
     쿠키(Cookie), 로컬 스토리지(LocalStorage)를 영구 저장합니다.

2. 동작 원리:
   - 사람이 이 스크립트를 통해 실제 브라우저를 띄우고 직접 안전하게 1회 로그인합니다.
   - 저장이 완료되면 이후 모든 일일 자동 포스팅 스크립트(`publish_story.py`, `migrate_tags.py`)가
     이 프로필을 재사용하여 로그인 과정 없이 즉시 글쓰기 에디터로 진입합니다.
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

from config_loader import get_config, PROJECT_ROOT

cfg = get_config()
PROFILE_DIR = Path(cfg.get("chrome_profile_dir", PROJECT_ROOT / "chrome_profile"))
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
BLOG_ID = cfg.get("blog_id", "sun_o_glitter")

def main():
    print("=" * 60)
    print("네이버 블로그 자동화 전용 Chrome 프로필 로그인 도구")
    print("=" * 60)
    print(f"프로필 경로: {PROFILE_DIR}")
    print("브라우저 창이 열리면 네이버에 로그인해 주세요.")
    print("※ 중요: '로그인 상태 유지'에 체크하시면 세션이 오래 유지됩니다.")
    print("로그인을 완료하고 블로그 메인 화면이 보이면 이 콘솔에서 Enter를 누르세요.")
    print("-" * 60)

    with sync_playwright() as p:
        # channel="chrome": 번들된 오픈소스 Chromium 대신 PC에 설치된 실제 구글 크롬 브라우저를 구동
        # --disable-blink-features=AutomationControlled: navigator.webdriver 플래그를 숨겨 봇 탐지 우회
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        page = context.new_page()
        # 네이버 로그인 페이지로 이동
        page.goto("https://nid.naver.com/nidlogin.login")

        # 사용자가 수동으로 아이디/비밀번호/2단계 인증을 완료할 때까지 대기
        try:
            input("\n>> 로그인을 완료하셨으면 콘솔에서 [Enter] 키를 누르세요: ")
        except (KeyboardInterrupt, EOFError):
            pass

        # 로그인 성공 여부 검증을 위해 블로그 메인 페이지로 이동
        page.goto(f"https://blog.naver.com/{BLOG_ID}")
        page.wait_for_timeout(3000)
        print("\n로그인 세션 저장을 완료했습니다. 브라우저를 닫습니다.")
        # context.close()를 호출해야 디스크에 쿠키와 세션이 최종 Flush(기록)됩니다.
        context.close()

    print("=" * 60)
    print("설정 완료! 이제 자동화 스크립트가 로그인 세션을 재사용합니다.")
    print("=" * 60)

if __name__ == "__main__":
    main()
