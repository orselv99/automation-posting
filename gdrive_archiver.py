"""
Google Drive Archiver Module
Archives fantasy novels and illustrations to Google Drive:
Folder path: __generated__/gemini-hobby-fantasy-scene
Includes 3-attempt retry logic and email notification fallback on failure.
"""
import os
import sys
import json
import io
import time
import traceback
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from email_notifier import send_failure_email

SCOPES = [
    'https://www.googleapis.com/auth/drive.file'
]

def get_or_create_folder(service, folder_name: str, parent_id: str = None) -> str:
    """Finds an existing folder or creates a new one in Google Drive"""
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        return files[0]['id']

    # Create folder
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def _perform_single_archive(title: str, story_content: str, image_path: str = None, local_path: str = None) -> dict:
    # Option 1: Local Google Drive mount if configured and present
    if local_path and os.path.exists(local_path):
        target_dir = Path(local_path) / "__generated__" / "gemini-hobby-fantasy-scene"
        target_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        doc_file = target_dir / f"{today} - {title}.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(f"제목: {title}\n일자: {today}\n\n{story_content}")
        print(f"[+] 로컬 Google Drive 동기화 저장 완료: {doc_file}")
        return {"status": "success", "mode": "local", "path": str(doc_file)}

    # Option 2: Google Drive API using gdrive_token.json
    token_file = Path(r"D:\.repo\.private\artifacts_1\gdrive_token.json")
    if not token_file.exists():
        err_msg = "gdrive_token.json이 없습니다. 'python gdrive_auth.py'를 실행해 연동해 주세요."
        print(f"\n[!] Google Drive 아카이빙 오류: {err_msg}")
        return {"status": "auth_required", "message": err_msg}

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    # 1. Resolve folder hierarchy: __generated__ -> gemini-hobby-fantasy-scene
    parent_id = get_or_create_folder(service, "__generated__")
    target_folder_id = get_or_create_folder(service, "gemini-hobby-fantasy-scene", parent_id=parent_id)

    # 2. Upload Document (convert to native Google Doc)
    today = datetime.now().strftime("%Y-%m-%d")
    doc_title = f"{today} - {title}"
    doc_metadata = {
        'name': doc_title,
        'parents': [target_folder_id],
        'mimeType': 'application/vnd.google-apps.document'
    }
    media = MediaIoBaseUpload(io.BytesIO(story_content.encode('utf-8')), mimetype='text/plain', resumable=True)
    doc = service.files().create(body=doc_metadata, media_body=media, fields='id, name, webViewLink').execute()
    print(f"[+] Google Drive 문서 생성 완료: {doc.get('name')} (ID: {doc.get('id')})")

    # 3. Upload Illustration Image if provided
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
    config_path: str = r"D:\.repo\.private\artifacts_1\config.json",
    max_retries: int = 3
) -> dict:
    """
    Archives novel and illustration to Google Drive with 3-attempt retry loop.
    If all 3 attempts fail, sends a failure alert email.
    """
    config_file = Path(config_path)
    local_path = None
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                gdrive_cfg = cfg.get("google_drive", {})
                local_path = gdrive_cfg.get("local_mount_path")
        except Exception:
            pass

    last_error = ""
    last_tb = ""

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
                # Auth is missing, no point in retrying 3 times immediately
                last_error = res.get("message", "인증 필요")
                break
            else:
                last_error = res.get("error", "알 수 없는 오류")
                print(f"[!] [실패] {attempt}번째 시도 실패: {last_error}")
        except Exception as e:
            last_error = str(e)
            last_tb = traceback.format_exc()
            print(f"[!] [예외 발생] {attempt}번째 시도 오류: {last_error}")

        if attempt < max_retries:
            wait_time = 5 * attempt
            print(f"[*] {wait_time}초 대기 후 Google Drive 업로드 재시도...")
            time.sleep(wait_time)

    # All 3 attempts failed: trigger email alert
    print("\n" + "!" * 70)
    print(f"[!] Google Drive 아카이빙이 {max_retries}회 연속 실패하였습니다.")
    print("[*] 실패 알림 메일을 발송합니다: orselv99@gmail.com")
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
