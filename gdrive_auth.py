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
CREDENTIALS_FILE = Path(r"D:\.repo\.private\artifacts_1\client_secret.json")

def main():
    print("=" * 70)
    print("Google Drive 아카이빙 1회 연동 설정 도구")
    print("대상 폴더: __generated__/gemini-hobby-fantasy-scene")
    print("=" * 70)

    if not CREDENTIALS_FILE.exists():
        print("\n[안내] Google Drive API를 통한 자동 생성을 위해서는 Google Cloud Console의")
        print("OAuth 클라이언트 정보(client_secret.json)가 필요합니다.")
        print(f"경로: {CREDENTIALS_FILE}")
        print("\n만약 Google Drive 데스크톱 앱(PC용 구글 드라이브)을 사용 중이시라면,")
        print("config.json의 'google_drive.local_mount_path'에 드라이브 경로(예: G:\\내 드라이브)")
        print("를 입력하시면 별도의 API 인증 없이도 자동 동기화됩니다.")
        print("-" * 70)
        return

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print(f"\n[+] Google Drive 연동 성공! 토큰 저장됨: {TOKEN_FILE}")
    except Exception as e:
        print(f"\n[!] 인증 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
