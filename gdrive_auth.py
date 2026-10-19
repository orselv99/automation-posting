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

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = Path(r"D:\.repo\.private\artifacts_1\gdrive_token.json")

def find_credentials_file() -> Path:
    base_dir = Path(r"D:\.repo\.private\artifacts_1")
    candidates = list(base_dir.glob("client_secret*.json"))
    if candidates:
        return candidates[0]
    return base_dir / "client_secret.json"

def main():
    print("=" * 70)
    print("Google Drive 아카이빙 1회 연동 설정 도구")
    print("대상 폴더: __generated__/gemini-hobby-fantasy-scene")
    print("=" * 70)

    credentials_file = find_credentials_file()
    if not credentials_file.exists():
        print(f"\n[안내] Google Drive OAuth 클라이언트 파일(client_secret*.json)을 찾을 수 없습니다.")
        print(f"경로: {credentials_file}")
        return

    print(f"[*] 클라이언트 정보 파일 발견: {credentials_file.name}")
    print("[*] 브라우저를 열어 Google 계정(orselv99@gmail.com) 승인을 진행합니다...")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print(f"\n[+] Google Drive 연동 성공! 토큰 저장됨: {TOKEN_FILE}")
        print("[+] 이제 자동화 스크립트가 구글 드라이브에 문서를 직접 생성합니다.")
    except Exception as e:
        print(f"\n[!] 인증 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
