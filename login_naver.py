"""
Naver One-Time Login Setup
Launches Chrome with the dedicated profile so you can log in to Naver once.
Future automated runs will reuse this logged-in session automatically.
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
        page.goto("https://nid.naver.com/nidlogin.login")

        try:
            input("\n>> 로그인을 완료하셨으면 콘솔에서 [Enter] 키를 누르세요: ")
        except (KeyboardInterrupt, EOFError):
            pass

        # Verify login by navigating to Naver main
        page.goto(f"https://blog.naver.com/{BLOG_ID}")
        page.wait_for_timeout(3000)
        print("\n로그인 세션 저장을 완료했습니다. 브라우저를 닫습니다.")
        context.close()

    print("=" * 60)
    print("설정 완료! 이제 자동화 스크립트가 로그인 세션을 재사용합니다.")
    print("=" * 60)

if __name__ == "__main__":
    main()
