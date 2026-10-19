"""
[Google Drive API 1회성 OAuth 인증 도구 (gdrive_auth.py)]

주니어 개발자를 위한 OAuth 2.0 연동 안내:
1. 데스크톱 앱 인증 방식 (InstalledAppFlow):
   - 서버 환경이 아닌 사용자의 로컬 PC에서 Google Drive API에 접근하기 위한 OAuth 2.0 플로우입니다.
   - Google Cloud Console에서 발급받은 데스크톱 클라이언트 파일(client_secret*.json)을 기반으로 실행됩니다.

2. 보안 및 권한 범위 (Scope - 최소 권한의 원칙):
   - 전체 드라이브의 모든 파일을 읽고 쓰는 위험한 전체 권한(`drive`) 대신,
   - 이 프로그램이 '직접 생성한 파일'에 대해서만 접근 가능한 `https://www.googleapis.com/auth/drive.file` 권한을 요청합니다.

3. 로컬 콜백 서버 (run_local_server):
   - port=0으로 지정하면 운영체제에서 비어있는 임의의 포트로 초소형 임시 웹서버를 구동합니다.
   - 브라우저에서 사용자가 구글 로그인을 승인하면 `http://localhost:{port}/?code=...`로 리다이렉트되고,
     스크립트가 인증 코드를 자동으로 낚아채 토큰 교환을 완료합니다.

4. 토큰 저장 (gdrive_token.json):
   - 발급된 Access Token과 Refresh Token이 `gdrive_token.json`에 저장됩니다.
   - 이후에는 Access Token이 만료되더라도 Refresh Token을 사용해 자동으로 토큰을 갱신하므로,
     이 인증 과정은 최초 1회만 수행하면 됩니다.
"""
import os
import sys
import json
from pathlib import Path

# Windows 터미널에서 한국어 콘솔 출력 시 인코딩 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config_loader import PROJECT_ROOT

# 앱이 직접 생성한 파일만 다룰 수 있는 최소 권한 스코프
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = PROJECT_ROOT / "gdrive_token.json"

def find_credentials_file() -> Path:
    """
    프로젝트 루트에서 Google Cloud 콘솔에서 다운로드한 'client_secret*.json' 파일을 검색합니다.
    파일명이 client_secret_1821... 형식으로 길더라도 첫 번째 일치 파일을 찾아 반환합니다.
    """
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

        # OAuth 인증 플로우 생성
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        
        # 로컬 임시 서버를 구동하고 기본 브라우저를 열어 구글 동의 화면을 띄웁니다.
        creds = flow.run_local_server(
            port=0,
            open_browser=True,
            prompt="consent",
            authorization_prompt_message="\n[인증 링크] 브라우저가 열리지 않았거나 다시 열려면 아래 URL에 접속하세요:\n{url}\n"
        )

        # 획득한 자격 증명(Access Token, Refresh Token)을 JSON 파일로 영구 저장
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print(f"\n[+] Google Drive 연동 성공! 토큰 저장됨: {TOKEN_FILE}", flush=True)
        print("[+] 이제 스크립트가 Google Drive에 문서를 직접 생성합니다.", flush=True)
    except Exception as e:
        print(f"\n[!] 인증 중 오류 발생: {e}", flush=True)

if __name__ == "__main__":
    main()
