"""
[Google Drive 아카이빙 및 클라우드 동기화 모듈 (gdrive_archiver.py)]

주니어 개발자를 위한 Google Drive API 안내:
1. Google Drive의 파일 시스템 구조 (ID 기반 구조):
   - 일반 로컬 파일 시스템(Windows/Linux)은 '/a/b/c' 형태의 문자열 경로를 사용합니다.
   - 하지만 Google Drive는 모든 폴더와 파일이 고유한 'ID'를 갖는 객체 그래프 구조입니다.
   - 따라서 `__generated__/gemini-hobby-fantasy-scene` 폴더를 만들려면 먼저 최상위(root)에서
     `__generated__` 폴더를 찾거나 생성(ID 획득)한 뒤, 그 ID를 부모(parent)로 지정하여
     `gemini-hobby-fantasy-scene` 하위 폴더를 생성해야 합니다.

2. 일반 텍스트 -> Google Docs 자동 변환 (MIME Type 지정):
   - 단순히 .txt 파일로 업로드하는 대신, 메타데이터의 mimeType을 `application/vnd.google-apps.document`로
     지정하면 구글 드라이브가 텍스트 내용을 파싱하여 즉시 열고 편집할 수 있는 '구글 문서(Google Docs)'로 변환해 줍니다.

3. 3회 재시도(Retry) 및 이메일 Fallback:
   - 외부 API 통신은 네트워크 순단, 속도 제한(Rate Limit) 등으로 간헐적 실패가 일어날 수 있습니다.
   - 따라서 점진적 대기 시간(5초, 10초)을 두며 최대 3회까지 재시도합니다.
   - 3회 모두 실패하면 시스템 장애로 간주하고 관리자에게 즉시 실패 알림 메일을 발송합니다.
"""
import os
import sys
import json
import io
import time
import traceback
from pathlib import Path
from datetime import datetime

# Windows 터미널 한글 인코딩 처리
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from email_notifier import send_failure_email

# 앱이 직접 생성한 파일에만 접근하는 안전 스코프
SCOPES = [
    'https://www.googleapis.com/auth/drive.file'
]

def get_or_create_folder(service, folder_name: str, parent_id: str = None) -> str:
    """
    구글 드라이브에서 지정된 이름의 폴더를 검색하고, 없으면 새로 생성하여 폴더의 'ID'를 반환합니다.
    
    매개변수:
    - service: 구글 드라이브 API 클라이언트 객체
    - folder_name: 찾거나 생성할 폴더 이름 (예: '__generated__')
    - parent_id: 부모 폴더의 ID (생략 시 루트 폴더를 부모로 취급)
    """
    # 폴더 검색 쿼리 작성 (휴지통에 있지 않고, mimeType이 폴더인 항목)
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"

    # API 호출로 기존 폴더 검색
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        # 이미 존재하는 폴더 ID 반환
        return files[0]['id']

    # 존재하지 않으면 새 폴더 생성
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def _perform_single_archive(title: str, story_content: str, image_path: str = None, local_path: str = None) -> dict:
    """
    단일 아카이빙 실행 단위 함수입니다.
    로컬 동기화 경로가 설정되어 있으면 로컬 디스크에 저장하고,
    그렇지 않으면 Google Drive REST API를 사용하여 클라우드에 직접 업로드합니다.
    """
    # 옵션 1: 사용자가 Google Drive PC 클라이언트(동기화 마운트 폴더)를 설정한 경우
    if local_path and os.path.exists(local_path):
        target_dir = Path(local_path) / "__generated__" / "gemini-hobby-fantasy-scene"
        target_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        doc_file = target_dir / f"{today} - {title}.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(f"제목: {title}\n일자: {today}\n\n{story_content}")
        print(f"[+] 로컬 Google Drive 동기화 저장 완료: {doc_file}")
        return {"status": "success", "mode": "local", "path": str(doc_file)}

    # 옵션 2: Google Drive API (OAuth 토큰 기반 클라우드 직접 통신)
    from config_loader import PROJECT_ROOT
    token_file = PROJECT_ROOT / "gdrive_token.json"
    if not token_file.exists():
        err_msg = "gdrive_token.json이 없습니다. 'python gdrive_auth.py'를 실행해 연동해 주세요."
        print(f"\n[!] Google Drive 아카이빙 오류: {err_msg}")
        return {"status": "auth_required", "message": err_msg}

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload

    # 저장된 토큰 로드 및 만료 시 자동 갱신(Refresh)
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    # 드라이브 v3 클라이언트 빌드
    service = build('drive', 'v3', credentials=creds)

    # 1. 2단계 폴더 계층 구조 확보: __generated__ -> gemini-hobby-fantasy-scene
    parent_id = get_or_create_folder(service, "__generated__")
    target_folder_id = get_or_create_folder(service, "gemini-hobby-fantasy-scene", parent_id=parent_id)

    # 2. 소설 본문 업로드 (Google Docs 형식으로 자동 변환)
    today = datetime.now().strftime("%Y-%m-%d")
    doc_title = f"{today} - {title}"
    doc_metadata = {
        'name': doc_title,
        'parents': [target_folder_id],
        'mimeType': 'application/vnd.google-apps.document'  # 구글 문서로 변환
    }
    # 텍스트 메모리 버퍼를 업로드 스트림으로 연결
    media = MediaIoBaseUpload(io.BytesIO(story_content.encode('utf-8')), mimetype='text/plain', resumable=True)
    doc = service.files().create(body=doc_metadata, media_body=media, fields='id, name, webViewLink').execute()
    print(f"[+] Google Drive 문서 생성 완료: {doc.get('name')} (ID: {doc.get('id')})")

    # 3. 삽화 이미지가 존재하는 경우 이미지 파일도 같은 폴더에 업로드
    img_id = None
    if image_path and os.path.exists(image_path):
        img_metadata = {
            'name': f"{today} - {title} - 삽화.png",
            'parents': [target_folder_id]
        }
        img_media = MediaFileUpload(image_path, mimetype='image/png')
        img_file = service.files().create(body=img_metadata, media_body=img_media, fields='id').execute()
        img_id = img_file.get('id')
        print(f"[+] Google Drive 삽화 업로드 완료: (ID: {img_id})")

    return {
        "status": "success",
        "doc_id": doc.get('id'),
        "image_id": img_id,
        "web_link": doc.get('webViewLink')
    }

def archive_to_google_drive(
    title: str,
    story_content: str,
    image_path: str = None,
    config_path: str = None,
    max_retries: int = 3
) -> dict:
    """
    소설과 삽화를 Google Drive에 아카이빙합니다.
    최대 3회 재시도(Exponential Backoff)를 수행하며, 모두 실패하면 실패 알림 이메일을 전송합니다.
    """
    from config_loader import get_config
    cfg = get_config()
    gdrive_cfg = cfg.get("google_drive", {})
    local_path = gdrive_cfg.get("local_mount_path")

    last_error = ""
    last_tb = ""

    # 최대 max_retries회 재시도 루프
    for attempt in range(1, max_retries + 1):
        print(f"\n[*] [Google Drive 시도 {attempt}/{max_retries}] 아카이빙 시도 중: '{title}'...")
        try:
            res = _perform_single_archive(
                title=title,
                story_content=story_content,
                image_path=image_path,
                local_path=local_path
            )
            if res.get("status") == "success":
                print(f"[+] [성공] Google Drive 아카이빙이 {attempt}번째 시도에서 완료되었습니다.")
                return res
            elif res.get("status") == "auth_required":
                # 인증 토큰 누락은 즉시 재시도해도 실패하므로 루프 중단
                last_error = res.get("message", "인증 필요")
                break
            else:
                last_error = res.get("error", "알 수 없는 오류")
                print(f"[!] [실패] {attempt}번째 시도 실패: {last_error}")
        except Exception as e:
            last_error = str(e)
            last_tb = traceback.format_exc()
            print(f"[!] [예외 발생] {attempt}번째 시도 오류: {last_error}")

        # 다음 재시도 전 점진적 대기 (5초, 10초...)
        if attempt < max_retries:
            wait_time = 5 * attempt
            print(f"[*] {wait_time}초 대기 후 Google Drive 업로드 재시도...")
            time.sleep(wait_time)

    # 3회 모두 실패한 경우: 관리자에게 이메일 알림 전송
    recipient = cfg.get("email_alert", {}).get("recipient", "configured recipient")
    print("\n" + "!" * 70)
    print(f"[!] Google Drive 아카이빙이 {max_retries}회 연속 실패하였습니다.")
    print(f"[*] 실패 알림 메일을 발송합니다: {recipient}")
    print("!" * 70 + "\n")

    send_failure_email(
        schedule_title="Google Drive Archiving - Daily Fantasy Novel",
        error_message=f"Google Drive 아카이빙 3회 연속 실패 ('{title}'): {last_error}",
        error_traceback=last_tb
    )

    return {
        "status": "error",
        "error": last_error
    }

if __name__ == "__main__":
    archive_to_google_drive(
        title="테스트 문서",
        story_content="Google Drive 아카이빙 재시도 및 이메일 알림 테스트입니다."
    )
