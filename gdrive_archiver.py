"""
Google Drive Archiver Module
Archives fantasy novels and illustrations to Google Drive:
Folder path: __generated__/gemini-hobby-fantasy-scene
"""
import os
import sys
import json
import io
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

def archive_to_google_drive(
    title: str,
    story_content: str,
    image_path: str = None,
    config_path: str = r"D:\.repo\.private\artifacts_1\config.json"
) -> dict:
    """
    Archives the novel as a Google Docs document and uploads the illustration
    to '__generated__/gemini-hobby-fantasy-scene' in Google Drive.
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
        print("\n" + "=" * 70)
        print("[!] Google Drive 아카이빙 안내:")
        print("    '__generated__/gemini-hobby-fantasy-scene'에 자동 저장을 위해")
        print("    최초 1회 인증이 필요합니다.")
        print("    터미널에서 'python gdrive_auth.py'를 실행하여 Google 계정 연동을 완료해 주세요.")
        print("=" * 70 + "\n")
        return {"status": "auth_required", "message": "Run gdrive_auth.py once to authenticate."}

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload

        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
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
            'mimeType': 'application/vnd.google-apps.document'  # Converts to Google Doc
        }
        media = MediaIoBaseUpload(io.BytesIO(story_content.encode('utf-8')), mimetype='text/plain', resumable=True)
        doc = service.files().create(body=doc_metadata, media_body=media, fields='id, name, webViewLink').execute()
        print(f"[+] Google Drive 문서 생성 완료: {doc.get('name')} (ID: {doc.get('id')})")

        # 3. Upload Illustration Image if provided
        if image_path and os.path.exists(image_path):
            img_metadata = {
                'name': f"{today} - {title} - 삽화.png",
                'parents': [target_folder_id]
            }
            img_media = MediaFileUpload(image_path, mimetype='image/png')
            img_file = service.files().create(body=img_metadata, media_body=img_media, fields='id').execute()
            print(f"[+] Google Drive 삽화 업로드 완료: (ID: {img_file.get('id')})")

        return {
            "status": "success",
            "doc_id": doc.get('id'),
            "web_link": doc.get('webViewLink')
        }
    except Exception as e:
        print(f"[!] Google Drive 아카이빙 중 오류 발생: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    archive_to_google_drive(
        title="테스트 문서",
        story_content="이것은 Google Drive 아카이빙 테스트 문서입니다."
    )
