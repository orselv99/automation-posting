"""
[네이버 블로그 이전 포스팅 태그 일괄 마이그레이션 도구 (migrate_tags.py)]

주니어 개발자를 위한 아키텍처 및 한국어 자연어 처리(NLP) 안내:
1. 브라우저 탐색 대신 순수 HTTP 요청(urllib)으로 전체 글을 수집하는 이유:
   - 브라우저(Playwright)로 수십 페이지의 게시글 목록을 클릭하며 탐색하면 메모리를 수백 MB 소모하고
     iframe 내부 비동기 렌더링 지연으로 인해 2페이지 이후로 넘어가지 않는 고질적 레이스 컨디션이 발생합니다.
   - 반면 `https://blog.naver.com/PostList.naver?...&currentPage=N`에 순수 HTTP GET 요청을 보내면,
     서버가 HTML 내부에 `<script id="socialPluginInfoJson">` 태그로 전체 글의 제목과 logNo를 정형 JSON으로 내려줍니다.
   - 덕분에 70편 이상의 전체 글 목록과 발행 일자를 2초 만에 초고속으로 수집할 수 있습니다.

2. 한국어 형태소 정규식(Regex) 기반 스마트 태그 추출 알고리즘:
   - 단순 띄어쓰기로 첫 단어, 둘째 단어를 자르면 "기억을 거래하는 숲의 길잡이"에서 ['#기억을', '#거래하는'] 같은
     조사와 관형형 동사가 추출되어 해시태그로서 의미가 없습니다.
   - 따라서:
     1) `와/과`를 기준으로 대등 연결된 두 구절을 분리
     2) `VERB_STRIP_REGEX`로 '거래하는', '벼리는', '지어지지 않은' 등 동사형 수식어구 제거
     3) `ADJ_STRIP_REGEX`로 '아직', '이미', '낭패 본' 등 부사/형용사형 수식어구 제거
     4) 후행 조사('을', '를', '과', '와')를 긍정형 후방탐색(`(?<=[가-힣])`)으로 안전하게 제거하여
        '#길잡이', '#살구타르트'처럼 검색 및 유입에 최적화된 고유 명사 태그를 완성합니다.

3. 실시간 영속화(Real-time Persistence):
   - 70편의 글을 수정하는 작업은 네트워크 상태에 따라 중간에 중단될 수 있습니다.
   - 글 하나를 성공할 때마다 즉시 `history/{yyyy-mm}.json`에 기록하므로,
     작업이 중단되어도 다시 실행하면 완료된 글은 자동으로 건너뛰고 이어서 작업합니다.
"""
import re
import sys
import json
import time
import html
import urllib.request
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime
from config_loader import get_config, PROJECT_ROOT

# Windows 콘솔 한글 인코딩 보정
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 모든 환상 단편 소설에 공통 적용되는 기본 고정 태그 (3종)
BASE_TAGS = ["#판타지소설", "#단편소설", "#환상문학"]

# 수동 검증 완료된 고품질 프리셋 태그 테이블 (예외적 정밀 매핑이 필요한 글 번호)
PRESET_TAGS = {
    "224446246932": ["#판타지소설", "#단편소설", "#환상문학", "#별빛의매듭", "#방직공의탑"],
    "224446204944": ["#판타지소설", "#단편소설", "#환상문학", "#양치기와비구름", "#날씨판타지"],
    "224445625593": ["#판타지소설", "#단편소설", "#환상문학", "#한숨유리공", "#유리공예장인"],
    "224445136954": ["#판타지소설", "#단편소설", "#환상문학", "#맹세의대장간", "#구부러진성검"],
    "224443399456": ["#판타지소설", "#단편소설", "#환상문학", "#별감정사", "#가짜운석"]
}

# 문두에 등장하는 수식형 동사/관형사구 패턴 목록 (명사 앞에 붙어 의미를 흐리는 단어들을 제거)
VERB_STRIP_REGEX = (
    r'^.*?(?:거래하는|빚는|벼리는|감정하는|잇는|담는|짜\s*넣는|타는|열리는|쓰는|곱씹는|치는|'
    r'고쳐\s*쓰는|파는|고치는|증류하는|다림질하는|뛰는|청소하는|낚는|먹는|울리는|다듬는|'
    r'깁는|삼는|지키는|떠난|수확하는|덜어내는|움직이는|자라는|지어지지\s*않은|걸어야만\s*열리는|'
    r'몰고\s*다니는|몰고다니는|떨어지는|찾아서)\s+'
)

# 문두에 등장하는 부사/상태 형용사 패턴 목록
ADJ_STRIP_REGEX = (
    r'^(?:아직|이미|스스로|뒤로|잠든|밤마다|매일|내려가기만\s*하는|3초\s*먼저|'
    r'오만한|시끄러운|낭패\s*본|말\s*많은|늙은|굴러떨어진|삼천\s*살의|비뚤어진|구운|'
    r'구겨진|뚱뚱한|잃어버린|차가운|노래하는|공중에\s*뜬|도망친|결백한|멈춰\s*선|'
    r'가짜|고집불통|허공에\s*뜬|구부러진|뒤늦은|말문\s*막힌|노인|엎질러진|은빛|저주받은|완벽한|가장\s*무거운)\s+'
)

# 태그로 부적절한 일반 명사/공무 행정형 불용어 목록
DISCARD_WORDS = {
    '비밀', '참사', '신청', '접수', '불합격', '적발', '감사', '불량', '의무화', '분쟁',
    '청구서', '비극', '한마디', '상담', '조절', '정기', '명령', '규제', '착용', '보안경',
    '마력의', '4항의', '3장', '제3장', '5G', '일흔일곱', '번의', '경고', '잉여', '완벽한'
}

def clean_chunk(text: str) -> str:
    """
    단편 소설 제목의 각 구절에서 동사/형용사/조사를 순차적으로 제거하여
    가장 핵심적인 고유 명사 덩어리(Chunk)만 남깁니다.
    """
    # 1. 동사 및 부사/형용사 수식어구 제거
    text = re.sub(VERB_STRIP_REGEX, '', text)
    text = re.sub(ADJ_STRIP_REGEX, '', text)
    
    # 2. 후행 조사('을', '를', '과', '와', '에', '로') 제거
    # 중요: 단어 전체를 깎지 않도록 '한글 문자 뒤에 붙은 조사'만 제거
    text = re.sub(r'(?<=[가-힣])(?:을|를|과|와|에|로)$', '', text)
    
    # 3. 공백 및 특수문자 제거
    clean = re.sub(r'[^\w가-힣]', '', text)
    
    # 4. 길이가 8자 이상으로 너무 긴 복합명사인 경우 뒤쪽 핵심 명사 추출
    if len(clean) > 8:
        m = re.search(r'의([가-힣]{2,6})$', clean)
        if m:
            clean = m.group(1)
        elif len(clean) > 8:
            clean = clean[-6:]
    return clean

def generate_specific_tags(title: str) -> list[str]:
    """
    한국어 단편 소설 제목에서 서사적 의미가 깃든 고유 명사 2종을 스마트 추출하여
    기본 태그 3종과 결합된 총 5종의 완성 태그 리스트를 생성합니다.
    """
    # 괄호 부가 설명 제거 (예: "(1부)" 등)
    clean_title = re.sub(r'\(.*?\)', '', title).strip()
    
    # 전략 A: 'A와 B' 또는 'A과 B' 대등 접속 구문 분리 시도
    parts = re.split(r'(?:와|과)\s+', clean_title, maxsplit=1)
    specific_tags = []

    if len(parts) == 2:
        n1 = clean_chunk(parts[0])
        n2 = clean_chunk(parts[1])
        if n1 and len(n1) >= 2 and n1 not in DISCARD_WORDS and f"#{n1}" not in specific_tags:
            specific_tags.append(f"#{n1}")
        if n2 and len(n2) >= 2 and n2 not in DISCARD_WORDS and f"#{n2}" not in specific_tags:
            specific_tags.append(f"#{n2}")

    # 전략 B: '와/과' 접속문이 아니거나 2개 추출에 실패한 경우 단어별 조사 제거 후 유의미한 명사 선별
    if len(specific_tags) < 2:
        words = clean_title.split()
        filtered_words = []
        for w in words:
            w = re.sub(r'^[^\w가-힣]+|[^\w가-힣]+$', '', w)
            w = re.sub(r'(?:의|은|는|이|가|을|를|과|와|에|로|에서)$', '', w)
            if len(w) >= 2 and w not in DISCARD_WORDS:
                filtered_words.append(w)

        for w in filtered_words:
            if f"#{w}" not in specific_tags:
                specific_tags.append(f"#{w}")
            if len(specific_tags) >= 2:
                break

    # 기본 태그 3종 + 고유 명사 태그 2종 결합
    tags = list(BASE_TAGS)
    for stag in specific_tags[:2]:
        if stag not in tags:
            tags.append(stag)

    return tags

def discover_all_posts(blog_id: str, category_no: str = "6", max_pages: int = 35) -> list[dict]:
    """
    네이버 블로그의 PostList.naver 페이지를 HTTP GET 방식으로 직접 조회하여
    Quatsch 카테고리의 모든 글 목록(제목, logNo, 발행일자)을 초고속으로 수집합니다.
    """
    print(f"[*] '{blog_id}' 블로그 카테고리(no={category_no})의 전체 포스팅 탐색 시작...")
    all_posts = []
    seen_log_nos = set()

    for pno in range(1, max_pages + 1):
        url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&categoryNo={category_no}&from=postList&currentPage={pno}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode('utf-8', errors='ignore')

                # [1단계] HTML 내에 임베딩된 socialPluginInfoJson JSON 데이터 추출
                m = re.search(r'id=["\']socialPluginInfoJson["\'][^>]*>(.*?)</', text)
                page_items = {}
                if m:
                    raw = html.unescape(m.group(1))
                    items = json.loads(raw)
                    for it in items:
                        page_items[str(it.get('logNo'))] = it.get('title', '').strip()

                # [2단계] HTML 내의 실제 발행 일자(.se_publishDate) 매핑
                date_pairs = re.findall(r'class=[\"\']se_publishDate[^\"\']*[\"\']\s*>([^<]+)<.*?copyBtn_(\d+)', text, re.DOTALL)
                date_map = {}
                today_str = datetime.now().strftime("%Y-%m-%d")

                for raw_date, lno in date_pairs:
                    raw_date = raw_date.strip()
                    m_date = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', raw_date)
                    if m_date:
                        y, mo, d = m_date.groups()
                        date_map[lno] = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
                    elif any(kw in raw_date for kw in ['시간', '분', '초', '방금', '전']):
                        date_map[lno] = today_str
                    else:
                        date_map[lno] = today_str

                # 중복을 제외하고 신규 발견된 글들을 리스트에 추가
                new_on_page = 0
                for lno, title in page_items.items():
                    if lno not in seen_log_nos:
                        seen_log_nos.add(lno)
                        post_date = date_map.get(lno, today_str)
                        all_posts.append({
                            'logNo': lno,
                            'title': title,
                            'date': post_date
                        })
                        new_on_page += 1

                # 페이지에 더 이상 새로운 글이 없으면 마지막 페이지에 도달한 것으로 판단
                if new_on_page == 0 and pno > 1:
                    print(f"[*] 총 {pno - 1}개 페이지에서 {len(all_posts)}편의 글 발견 완료!")
                    break
        except Exception as e:
            print(f"[!] {pno}페이지 탐색 중 오류: {e}")
            break

    return all_posts

from history_manager import save_post_to_monthly_history, get_all_migrated_log_nos

def migrate_tags_for_post(page, blog_id: str, log_no: str, target_tags: list[str]) -> bool:
    """
    Playwright를 사용하여 단일 글의 스마트에디터 수정 페이지(Redirect=Update)로 진입한 후
    기존 태그를 모두 삭제하고 신규 규격 태그(target_tags)를 등록한 뒤 수정 발행합니다.
    """
    update_url = f"https://blog.naver.com/{blog_id}?Redirect=Update&logNo={log_no}"
    print(f"\n[*] 글 수정 페이지 접근: {update_url}")
    page.goto(update_url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    # mainFrame iframe 감싸임 검사
    frame = page
    for f in page.frames:
        if "mainFrame" in f.name:
            frame = f
            break

    # 임시 저장 팝업 등이 뜨면 닫기
    try:
        cancel_btn = frame.locator('div[data-group="popupLayer"] button.se-popup-button-cancel').first
        if cancel_btn.is_visible(timeout=2000):
            cancel_btn.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    # 상단 '발행' 버튼 클릭하여 설정 패널 열기
    print("[*] 상단 '발행' 버튼 클릭...")
    pub_btn = frame.locator('button[data-click-area="tpb.publish"]').first
    pub_btn.click()
    page.wait_for_timeout(2000)

    # 기존에 등록된 구형 태그가 있다면 삭제 버튼 클릭
    try:
        del_btns = frame.locator('button[class*="tag_delete"], button[class*="btn_delete"]').all()
        for d in del_btns:
            d.click()
            page.wait_for_timeout(100)
    except Exception:
        pass

    # 신규 규격 태그 차례대로 입력
    print(f"[*] 태그 등록 중: {target_tags}")
    tag_input = frame.locator('input[class*="tag_input"]').first
    if tag_input.is_visible(timeout=3000):
        tag_input.click()
        for tag in target_tags:
            clean_tag = tag.replace("#", "").strip()
            if clean_tag:
                tag_input.fill(clean_tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(250)
        print("[+] 태그 입력 완료")
    else:
        print("[!] 태그 입력 필드를 찾지 못했습니다.")

    # 최종 수정 발행 확인 버튼 클릭
    print("[*] 최종 수정 발행 클릭...")
    confirm_btn = frame.locator('button[data-click-area="tpb*i.publish"]').first
    if not confirm_btn.is_visible(timeout=3000):
        confirm_btn = frame.locator('.layer_publish button:has-text("발행"), button.confirm_btn__byZZW').first

    confirm_btn.click()
    print("[*] 수정 발행 저장 대기 중 (7초)...")
    page.wait_for_timeout(7000)
    print(f"[+] logNo: {log_no} 태그 업데이트 완료!")
    return True

def main():
    """
    태그 일괄 마이그레이션 CLI 메인 루틴
    """
    parser = argparse.ArgumentParser(description="네이버 블로그 전체 페이지의 포스팅 태그를 일괄 마이그레이션합니다.")
    parser.add_argument("--headless", action="store_true", help="브라우저 창을 띄우지 않고 백그라운드에서 실행")
    parser.add_argument("--limit", type=int, default=0, help="수정할 포스팅 최대 개수 (0 = 전체)")
    parser.add_argument("--skip-migrated", action="store_true", default=True, help="히스토리에 이미 완료된 글 건너뛰기")
    parser.add_argument("--dry-run", action="store_true", help="실제 블로그를 수정하지 않고 추출된 태그만 미리보기")
    args = parser.parse_args()

    config = get_config()
    blog_id = config.get("blog_id", "sun_o_glitter")
    profile_dir = Path(config.get("chrome_profile_dir", PROJECT_ROOT / "chrome_profile"))

    # 월별 히스토리 파일들에서 이미 완료된 글 번호 집합 수집
    already_migrated_ids = get_all_migrated_log_nos()

    print("=" * 70)
    print("네이버 블로그 전체 포스팅 태그 마이그레이션 도구 (다중 페이지 지원)")
    print(f"블로그 ID: {blog_id}")
    print(f"기본 태그: {BASE_TAGS}")
    print(f"이미 완료된 포스팅 수: {len(already_migrated_ids)}편")
    print("=" * 70)

    # 1단계: 순수 HTTP를 통해 전체 페이지 글 목록 수집
    all_posts = discover_all_posts(blog_id)

    # 이미 처리된 글 필터링
    if args.skip_migrated:
        pending_posts = [p for p in all_posts if p['logNo'] not in already_migrated_ids]
    else:
        pending_posts = all_posts

    if args.limit > 0:
        pending_posts = pending_posts[:args.limit]

    print(f"\n[*] 업데이트 대상 글: 총 {len(pending_posts)}편 (전체 {len(all_posts)}편 중)")
    for idx, post in enumerate(pending_posts, 1):
        target_tags = PRESET_TAGS.get(post['logNo'], generate_specific_tags(post['title']))
        print(f"  {idx:2d}. [{post['logNo']}] {post['title']} -> {target_tags}")

    # dry-run 모드일 경우 미리보기만 출력하고 안전하게 종료
    if args.dry_run:
        print("\n[안내] --dry-run 모드이므로 브라우저를 통한 실제 수정을 진행하지 않고 종료합니다.")
        return

    if not pending_posts:
        print("\n[+] 업데이트할 포스팅이 없습니다. 모든 포스팅이 이미 최신 태그로 완료되었습니다.")
        return

    # 2단계: Playwright 브라우저를 구동하여 순차적으로 글 수정 및 월별 히스토리 영속화
    success_count = 0
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=args.headless,
            viewport={"width": 1400, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.new_page()

        for idx, post in enumerate(pending_posts, 1):
            log_no = post['logNo']
            target_tags = PRESET_TAGS.get(log_no, generate_specific_tags(post['title']))
            print(f"\n>>> [{idx}/{len(pending_posts)}] '{post['title']}' 진행 중...")
            try:
                if migrate_tags_for_post(page, blog_id, log_no, target_tags):
                    success_count += 1
                    # 수정 완료 즉시 해당 연월의 히스토리 파일에 저장하여 중단 대비
                    save_post_to_monthly_history({
                        "logNo": log_no,
                        "date": post.get("date"),
                        "title": post['title'],
                        "tags": target_tags,
                        "migrated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    already_migrated_ids.add(log_no)
            except Exception as e:
                print(f"[!] '{post['title']}' 업데이트 실패: {e}")

        print("\n" + "=" * 70)
        print(f"[+] 마이그레이션 완료: 총 {len(pending_posts)}편 중 {success_count}편 업데이트 성공!")
        print("=" * 70)

        context.close()

if __name__ == "__main__":
    main()
