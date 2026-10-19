"""
Email notification module for failure alerts.
Sends an alert email when the scheduled task fails after max retries.
"""
import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config_loader import get_config, PROJECT_ROOT

def send_failure_email(
    schedule_title: str,
    error_message: str,
    error_traceback: str = "",
    config_path: str = None
) -> bool:
    """
    Sends an alert email to the recipient when automation fails after retries.
    Subject format: [gemini-automation-failed] {스케쥴 제목}
    """
    subject = f"[gemini-automation-failed] {schedule_title}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load configuration
    cfg = get_config()
    email_cfg = cfg.get("email_alert", {})
    recipient = email_cfg.get("recipient", "orselv99@gmail.com")
    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = email_cfg.get("smtp_port", 587)
    sender_email = email_cfg.get("sender_email", "orselv99@gmail.com")
    app_password = os.environ.get("GMAIL_APP_PASSWORD") or email_cfg.get("app_password", "")

    # Log to local failure alerts log file regardless of SMTP status
    log_dir = Path(cfg.get("output_dir", PROJECT_ROOT / "generated"))
    log_dir.mkdir(parents=True, exist_ok=True)
    alert_log_file = log_dir / "failure_alerts.log"

    log_entry = (
        f"\n{'='*70}\n"
        f"[{timestamp}] FAILURE ALERT: {subject}\n"
        f"Recipient: {recipient}\n"
        f"Error: {error_message}\n"
        f"Traceback:\n{error_traceback}\n"
        f"{'='*70}\n"
    )
    with open(alert_log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
    print(f"[*] 실패 알림 로그 기록 완료: {alert_log_file}")

    # Compose Email Body
    body_content = f"""안녕하세요,

Antigravity 자동화 시스템에서 알림을 전송합니다.
네이버 블로그 자동 포스팅 태스크가 3회 연속 실패하였습니다.

[태스크 정보]
- 스케쥴 명: {schedule_title}
- 발생 일시: {timestamp}
- 수신 대상: {recipient}

[실패 원인]
{error_message}

[상세 트레이스백]
{error_traceback if error_traceback else "트레이스백 없음"}

확인 후 설정을 점검해 주시기 바랍니다.
"""

    if not app_password:
        print("\n" + "!" * 70)
        print("[!] 이메일 발송 안내:")
        print(f"    수신자: {recipient}")
        print(f"    제목: {subject}")
        print("    Gmail 발송을 위한 앱 비밀번호(GMAIL_APP_PASSWORD)가 아직 설정되지 않았습니다.")
        print("    config.json의 'email_alert.app_password' 또는 환경변수 GMAIL_APP_PASSWORD에")
        print("    구글 앱 비밀번호(16자리)를 입력하시면 즉시 이메일이 발송됩니다.")
        print(f"    (실패 내용은 {alert_log_file} 파일에 안전하게 보관되었습니다)")
        print("!" * 70 + "\n")
        return False

    # Attempt sending email via SMTP
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body_content, "plain", "utf-8"))

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"[+] 실패 알림 이메일 전송 성공: {recipient} ({subject})")
        return True
    except Exception as e:
        print(f"[!] 이메일 전송 중 SMTP 오류 발생: {e}")
        return False

if __name__ == "__main__":
    send_failure_email(
        schedule_title="Daily Naver Blog Fantasy Novel",
        error_message="테스트 오류: 3회 재시도 실패 시뮬레이션",
        error_traceback="Traceback test..."
    )
