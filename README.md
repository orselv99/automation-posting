# Naver Blog Daily Fantasy Novel Automation (Quatsch)

네이버 블로그([sun_o_glitter](https://blog.naver.com/sun_o_glitter))의 `Quatsch` 카테고리에 매일 오전 09:00 (KST), 2000자 내외의 고품격 환상문학 단편 소설과 고전 펜화 에칭 스타일 삽화를 자동으로 집필하고 게시하는 자동화 시스템입니다.

---

## 📁 디렉토리 구조 및 저장 규격

생성된 소설과 삽화는 다음 규칙에 따라 아카이빙됩니다:

```
./generated/
  └── {yyyy-mm}/
        ├── {dd}-{title}.md   (소설 본문 및 메타데이터)
        └── {dd}-{title}.png  (16:9 에칭 펜화 삽화)
```

### 주요 파일

* `prompt_spec.md`: 고전 중세 다크판타지/신비주의 문학 창작 명세서 (테마 A~J 순환 및 금지어/서식 규칙)
* `history.json`: 매일 발행된 소설의 날짜, 제목, 테마, 핵심 컨셉 아카이브 (소재 중복 원천 차단)
* `config.json`: 블로그 ID (`sun_o_glitter`), 카테고리(`Quatsch`), 프로필 경로 등 환경 설정
* `login_naver.py`: 전용 크롬 프로필(`chrome_profile/`)을 띄워 네이버에 1회 사전 로그인하는 도구
* `naver_publisher.py`: Playwright 기반 스마트에디터 ONE 자동 글쓰기, 삽화 중간 삽입, 카테고리/태그 설정 및 발행 스크립트
* `publish_story.py`: 생성된 마크다운 소설과 삽화 이미지를 전달받아 네이버 블로그에 포스팅하는 실행기

---

## 🚀 사전 1회 설정: 네이버 로그인 세션 등록

최초 1회만 아래 명령어를 실행하여 전용 브라우저에서 네이버에 로그인해 둡니다. (완료됨)

```bash
python login_naver.py
```

---

## ⏰ 일일 자동화 동작 방식 (매일 09:00 KST)

1. **히스토리 확인 & 테마 선정**: `history.json`을 읽어 최근 다룬 테마/소재를 제외하고 신규 테마(A~J)를 선정.
2. **소설 창작**: `prompt_spec.md` 명세에 맞춰 2,000자 내외의 옴니버스 단편 소설과 에칭풍 삽화 영문 프롬프트 생성.
3. **삽화 생성**: 생성된 영문 프롬프트로 고해상도 펜화 에칭 일러스트를 생성하여 `./generated/{yyyy-mm}/{dd}-{title}.png`로 저장.
4. **소설 저장**: `./generated/{yyyy-mm}/{dd}-{title}.md`에 원고 저장.
5. **블로그 즉시 발행**: `publish_story.py`를 실행하여 스마트에디터 본문의 `[삽화 삽입 위치]`에 이미지를 삽입하고 `Quatsch` 카테고리로 발행.
6. **히스토리 업데이트**: 발행된 글의 메타데이터를 `history.json`에 기록.
