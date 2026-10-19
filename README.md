# Naver Blog Daily Fantasy Novel Automation (Quatsch)

네이버 블로그([sun_o_glitter](https://blog.naver.com/sun_o_glitter))의 `Quatsch` 카테고리에 매일 오전 09:00 (KST), 2000자 내외의 고품격 환상문학 단편 소설과 고전 펜화 에칭 스타일 삽화를 자동으로 집필하고 게시하는 자동화 시스템입니다.

---

## 📁 주요 구성 파일

* `prompt_spec.md`: 고전 중세 다크판타지/신비주의 문학 창작 명세서 (테마 A~J 순환 및 금지어/서식 규칙)
* `history.json`: 매일 발행된 소설의 날짜, 제목, 테마, 핵심 컨셉, 태그 아카이브 (소재 중복 원천 차단)
* `config_loader.py`: `.env` 파일과 `config.json`을 연동하여 환경변수 및 상대경로를 자동 확장하는 중앙 설정 로더
* `config.json`: 블로그 기본 설정 템플릿 (`.env` 환경변수로 값 바인딩)
* `.env.example`: 로컬 환경 설정 템플릿 (블로그 ID, 이메일 알림 수신자, 크롬 프로필 경로 등)
* `login_naver.py`: 전용 크롬 프로필(`chrome_profile/`)을 띄워 네이버에 1회 사전 로그인하는 도구
* `naver_publisher.py`: Playwright 기반 스마트에디터 ONE 자동 글쓰기 (기본서체, 15pt, 마크다운 문법 자동 제거, 삽화 중간 삽입, 태그 등록 및 즉시 발행)
* `publish_story.py`: 3회 재시도 루프와 최종 실패 시 이메일 알림(Fallback)이 내장된 블로그 발행기
* `email_notifier.py`: 3회 연속 실패 시 `[gemini-automation-failed] {스케쥴 제목}` 메일 발송 및 로그 기록기
* `migrate_tags.py`: 블로그 내 기존 이전 글들을 검색하여 신규 태그 규칙에 맞게 일괄 업데이트하는 마이그레이션 도구
* `gdrive_archiver.py`: Google Drive의 `__generated__/gemini-hobby-fantasy-scene` 경로에 문서를 자동 생성/동기화하는 아카이버
* `gdrive_auth.py`: Google Drive API 1회 인증 도구

---

## 🎨 문서 스타일 및 태그 규칙

1. **마크다운 문법 자동 정제**: 네이버 블로그는 마크다운을 지원하지 않으므로 본문 내 `>`, `**`, `---`, `###` 등의 문법 기호를 발행 전 완전 제거하여 깔끔한 순수 줄글로 포스팅합니다.
2. **타이포그래피**: 네이버 스마트에디터 ONE 표준 스타일인 **기본서체**, **글씨크기 15pt**, **색상없음(기본 검정)**으로 발행됩니다.
3. **태그 규칙 (정확히 5~6종)**:
   * **기본 태그 (3종 고정)**: `#판타지소설`, `#단편소설`, `#환상문학`
   * **특정 태그 (2~3종 맞춤)**: 소설의 고유 테마, 제목, 핵심 소재에서 유입에 유리한 키워드 추출

---

## 🚨 실패에 대한 Fallback (재시도 및 이메일 알림)

* 발행 중 일시적 네트워크 오류나 에디터 지연 발생 시 **최대 3회 자동 재시도** (10초, 20초 간격 점진적 대기)
* 3회 모두 실패할 경우:
  * 수신자: `.env`의 `EMAIL_RECIPIENT`로 설정된 이메일 주소
  * 메일 제목: `[gemini-automation-failed] Daily Naver Blog Fantasy Novel`
  * 본문: 실패 사유, 발생 일시, 상세 트레이스백
  * `.env`의 `GMAIL_APP_PASSWORD`에 구글 앱 비밀번호(16자리)를 입력하시면 즉시 이메일 발송 연동이 완료됩니다. (미설정 시에도 `./generated/failure_alerts.log`에 에러 내역이 안전하게 보존됩니다.)

---

## ⏰ 일일 자동화 동작 방식 (매일 09:00 KST)

1. **히스토리 확인 & 테마 선정**: `history.json`을 읽어 최근 다룬 테마/소재를 제외하고 신규 테마(A~J)를 선정.
2. **소설 창작**: `prompt_spec.md` 명세에 맞춰 2,000자 내외의 옴니버스 단편 소설과 에칭풍 삽화 영문 프롬프트 생성.
3. **삽화 생성**: 영문 프롬프트로 고해상도 펜화 에칭 일러스트를 생성하여 `./generated/{yyyy-mm}/{dd}-{title}.png`로 저장.
4. **소설 저장**: `./generated/{yyyy-mm}/{dd}-{title}.md`에 원고 저장.
5. **블로그 즉시 발행**: `publish_story.py` 실행 (마크다운 정제 -> 기본서체/15pt 입력 -> 삽화 중간 삽입 -> 태그 5종 입력 -> 즉시 발행).
6. **히스토리 업데이트**: 발행된 글의 메타데이터를 `history.json`에 기록.

---

## 🛠️ 수동 실행 명령어 가이드 (Manual Commands)

### 1. 초기 환경 설정 및 1회성 계정 연동

* **네이버 블로그 로그인 세션 등록**
  ```bash
  python login_naver.py
  ```
  전용 크롬 프로필(`chrome_profile/`) 창이 열리면 네이버 계정에 로그인(‘로그인 상태 유지’ 권장)한 후 콘솔에서 `Enter`를 누릅니다. 이후 자동화 스크립트가 해당 로그인 세션을 영구 재사용합니다.

* **Google Drive API 인증**
  ```bash
  python gdrive_auth.py
  ```
  OAuth 인증 브라우저 창이 열리면 대상 구글 계정으로 로그인 및 권한을 승인합니다. 완료 시 `gdrive_token.json`이 자동 저장됩니다.

---

### 2. 단편 소설 및 삽화 수동 발행 (`publish_story.py`)

지정된 소설 마크다운 원고와 삽화 이미지를 정제하여 네이버 블로그에 포스팅하고 Google Drive에 동시 아카이빙합니다.

* **기본 실행 (브라우저 확인 가능)**
  ```bash
  python publish_story.py --story ./generated/2026-10/19-침묵의\ 방직공과\ 별빛의\ 매듭.md --image ./generated/2026-10/19-침묵의\ 방직공과\ 별빛의\ 매듭.png
  ```

* **헤드리스 모드 실행 (백그라운드)**
  ```bash
  python publish_story.py --story <소설.md> --image <삽화.png> --headless
  ```

> **포함 동작**:
> 1. 마크다운 문법 기호(`>`, `**`, `---` 등) 자동 정제
> 2. 스마트에디터 ONE 서식(기본서체, 15pt, 기본색상) 적용
> 3. 본문 내 `[삽화 삽입 위치]`에 이미지 자동 업로드
> 4. 기본 태그 3종 + 제목/내용 기반 특정 태그 2~3종 자동 등록
> 5. 즉시 발행 및 Google Drive(`__generated__/gemini-hobby-fantasy-scene`) 문서/삽화 동기화
> 6. 실패 시 최대 3회 재시도 루프 및 최종 실패 시 이메일 알림 발송

---

### 3. 이전 포스팅 태그 일괄 마이그레이션 (`migrate_tags.py`)

기존에 태그 없이 발행되었던 블로그 포스팅들을 고속 스캔하여 최신 규격 태그(기본 3종 + 고유 명사 2종)로 일괄 업데이트합니다.

* **태그 추출 결과 미리보기 (브라우저 없이 고속 확인)**
  ```bash
  python migrate_tags.py --dry-run
  ```

* **전체 미반영 포스팅 순차 마이그레이션**
  ```bash
  python migrate_tags.py
  ```

* **지정 개수만 순차 마이그레이션 (예: 5편만 테스트)**
  ```bash
  python migrate_tags.py --limit 5
  ```

* **백그라운드(헤드리스) 모드로 실행**
  ```bash
  python migrate_tags.py --headless
  ```

> **포함 동작**:
> - `history.json`에 이미 기록된 완료 글은 자동 건너뛰기
> - 수정 완료 즉시 `history.json`에 실시간 영속화하여 중단 후 재실행 가능

---

### 4. 개별 모듈 및 Fallback 테스트

* **Google Drive 아카이빙 단독 테스트**
  ```bash
  python gdrive_archiver.py
  ```

* **실패 알림 이메일(SMTP) 발송 및 로그 저장 테스트**
  ```bash
  python email_notifier.py
  ```

* **중앙 환경변수 및 상대경로 로더 검증**
  ```bash
  python -c "from config_loader import get_config; import json; print(json.dumps(get_config(), indent=2, ensure_ascii=False))"
  ```
