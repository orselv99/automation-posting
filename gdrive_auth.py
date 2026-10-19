"""
Google Drive 1-Time Authorization Setup
Enables automated uploading/document creation to Google Drive at:
__generated__/gemini-hobby-fantasy-scene
"""
import os
import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config_loader import PROJECT_ROOT

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = PROJECT_ROOT / "gdrive_token.json"

def find_credentials_file() -> Path:
    candidates = list(PROJECT_ROOT.glob("client_secret*.json"))
    if candidates:
        return candidates[0]
    return PROJECT_ROOT / "client_secret.json"

def main():
    print("=" * 70, flush=True)
    print("Google Drive 아카이빙 1회 연동 설정 도구", flush=True)
    print("대상 폴더: __generated__/gemini-hobby-fantasy-scene", flush=True)
    print("=" * 70, flush=True)

    credentials_file = find_credentials_file()
    if not credentials_file.exists():
        print(f"\n[안내] Google Drive OAuth 클라이언트 파일(client_secret*.json)을 찾을 수 없습니다.", flush=True)
        return

    print(f"[*] 클라이언트 정보 파일 발견: {credentials_file.name}", flush=True)
    print("[*] Google Drive 연동 인증을 시작합니다...", flush=True)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(
            port=0,
            open_browser=True,
            prompt="consent",
            authorization_prompt_message="\n[인증 링크] 브라우저가 열리지 않았거나 다시 열려면 아래 URL에 접속하세요:\n{url}\n"
        )

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print(f"\n[+] Google Drive 연동 성공! 토큰 저장됨: {TOKEN_FILE}", flush=True)
        print("[+] 이제 스크립트가 Google Drive에 문서를 직접 생성합니다.", flush=True)
    except Exception as e:
        print(f"\n[!] 인증 중 오류 발생: {e}", flush=True)

if __name__ == "__main__":
    main()
