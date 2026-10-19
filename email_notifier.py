"""
[실패 알림 이메일 발송 및 장애 로그 모듈 (email_notifier.py)]

주니어 개발자를 위한 알림 및 장애 대응 아키텍처 안내:
1. 무중단 자동화 시스템에서의 실패 알림(Alerting)의 중요성:
   - 사람이 매일 아침 수동으로 시스템을 들여다보지 않더라도, 자동화 작업이 3회 재시도 끝에 실패하면
     관리자에게 즉각 이메일로 실패 내역(트레이스백 포함)을 알려주어야 빠른 조치가 가능합니다.

2. 이중 안전장치 (Dual-logging Safety Net):
   - 만약 Gmail 앱 비밀번호가 설정되지 않았거나, 인터넷 회선 문제로 SMTP 서버 연결에 실패하더라도,
     절대 에러 내용이 유실되어서는 안 됩니다.
   - 따라서 이 모듈은 네트워크를 타기 전에 먼저 로컬 디스크(`generated/failure_alerts.log`)에
     에러 로그를 확정적으로 기록한 뒤, 이메일 발송을 시도합니다.

3. Gmail SMTP와 앱 비밀번호(App Password):
   - Google 계정은 2단계 인증이 활성화되어 있어 일반 계정 비밀번호로는 로그인할 수 없습니다.
   - Google 계정 보안 설정에서 생성한 16자리 '앱 비밀번호(App Password)'를 사용하며,
     TLS 포트(587)로 암호화 통신을 수행합니다.
"""
import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Windows 터미널 한글 출력 인코딩 보정
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
    포스팅 또는 아카이빙이 최종 실패했을 때 관리자에게 알림 이메일을 전송합니다.
    
    메일 제목 형식: [gemini-automation-failed] {스케쥴 제목}
    """
    subject = f"[gemini-automation-failed] {schedule_title}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 설정 파일 및 환경변수에서 이메일 발송 정보 로드
    cfg = get_config()
    email_cfg = cfg.get("email_alert", {})
    recipient = email_cfg.get("recipient", "orselv99@gmail.com")
    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = email_cfg.get("smtp_port", 587)
    sender_email = email_cfg.get("sender_email", "orselv99@gmail.com")
    app_password = os.environ.get("GMAIL_APP_PASSWORD") or email_cfg.get("app_password", "")

    # [1단계] 로컬 파일 로깅: SMTP 발송 성공 여부와 무관하게 로컬 디스크에 영구 기록
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

    # [2단계] 메일 본문 작성 (한국어 평문)
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

    # 앱 비밀번호가 설정되지 않은 경우 친절한 안내 메시지 출력 후 종료
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

    # [3단계] SMTP 프로토콜을 통한 실제 이메일 발송
    try:
        # MIME 표준 객체 생성 (한글 깨짐 방지를 위해 utf-8 명시)
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body_content, "plain", "utf-8"))

        # Gmail SMTP 서버 연결 및 TLS 암호화 핸드셰이크
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
