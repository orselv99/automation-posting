"""
[스마트에디터 ONE 서식 및 스타일 자동화 모듈 (editor_style.py)]

주니어 개발자를 위한 서식 자동화 기술 안내:
1. 스마트에디터 ONE의 스타일 구조:
   - 네이버 블로그 에디터는 본문 텍스트의 폰트, 크기, 색상, 정렬, 줄간격을 툴바 버튼을 통해 설정합니다.
   - 각 문단(<p>)이나 구문(<span>)에 `se-ff-nanummyeongjo`, `se-fs16`, `style="color: #333333"` 같은
     클래스와 인라인 스타일이 적용됩니다.

2. 일괄 스타일 적용 메커니즘 (Batch Style Application):
   - 본문 첫 번째 문단을 클릭한 후 키보드 'Control+A'를 전송하면, 스마트에디터 ONE은
     소설 본문 전체(삽화 이전 및 이후 문단 전체)를 한 번에 선택(Block Selection)합니다.
   - 이때 상단 툴바의 서체, 크기, 색상, 정렬, 줄간격 드롭다운을 호출하여 원하는 옵션을 클릭하면
     본문 전체의 스타일이 찰나의 순간에 일괄 변경됩니다.

3. 지원하는 서식 속성 및 옵션:
   - 폰트(font_family): 기본서체, 나눔고딕, 나눔명조, 나눔바른고딕, 나눔스퀘어, 마루부리, 다시시작해, 바른히피, 우리딸손글씨
   - 크기(font_size): 11, 13, 15, 16, 19, 24, 28, 30, 34, 38 (단위: pt)
   - 색상(font_color): '색상없음'(기본 검정) 또는 팔레트/커스텀 HEX(#000000, #333333 등)
   - 정렬(align): left(왼쪽), center(가운데), right(오른쪽), justify(양쪽)
   - 줄간격(line_height): 150, 160, 170, 180, 190, 200, 210 (%)
"""
import re
from typing import Dict, Any, Optional

# 스마트에디터 ONE 폰트 매핑 테이블 (한국어 명칭 및 영문 식별자)
FONT_FAMILY_MAP = {
    "기본서체": "default", "default": "default",
    "나눔고딕": "nanumgothic", "nanumgothic": "nanumgothic",
    "나눔명조": "nanummyeongjo", "nanummyeongjo": "nanummyeongjo",
    "나눔바른고딕": "nanumbarungothic", "nanumbarungothic": "nanumbarungothic",
    "나눔스퀘어": "nanumsquare", "nanumsquare": "nanumsquare",
    "마루부리": "nanummaruburi", "nanummaruburi": "nanummaruburi", "maruburi": "nanummaruburi",
    "다시시작해": "nanumdasisijaghae", "nanumdasisijaghae": "nanumdasisijaghae",
    "바른히피": "nanumbareunhipi", "nanumbareunhipi": "nanumbareunhipi",
    "우리딸손글씨": "nanumuriddalsongeulssi", "nanumuriddalsongeulssi": "nanumuriddalsongeulssi"
}

# 텍스트 정렬 매핑 테이블
ALIGN_MAP = {
    "left": "align-left", "왼쪽": "align-left",
    "center": "align-center", "가운데": "align-center", "중앙": "align-center",
    "right": "align-right", "오른쪽": "align-right",
    "justify": "align-justify", "양쪽": "align-justify"
}

# 허용되는 글자 크기 및 줄간격 유효 목록
VALID_FONT_SIZES = [11, 13, 15, 16, 19, 24, 28, 30, 34, 38]
VALID_LINE_HEIGHTS = [150, 160, 170, 180, 190, 200, 210]

def apply_post_style(frame, page, style: Optional[Dict[str, Any]] = None) -> bool:
    """
    스마트에디터 ONE 내의 본문 텍스트에 지정된 스타일(폰트, 크기, 색상, 정렬, 줄간격)을 일괄 적용합니다.

    매개변수:
    - frame: 스마트에디터 ONE이 포함된 Playwright Frame 또는 Page 객체
    - page: 상위 Page 객체 (키보드 및 타이머 제어용)
    - style: 적용할 스타일 딕셔너리 (생략 시 config.json의 기본 post_style 적용)
      예: {
          "font_family": "기본서체",
          "font_size": 15,
          "font_color": "색상없음",
          "align": "left",
          "line_height": 180
      }
    """
    if not style:
        from config_loader import get_config
        style = get_config().get("post_style", {})

    print(f"[*] 스마트에디터 본문 스타일 일괄 적용 시작: {style}")

    # [1단계] 본문 첫 번째 문단 클릭 후 전체 선택 (Control+A)
    # 제목(p[0])을 제외한 첫 번째 본문 문단(p[1])을 클릭합니다.
    all_p = frame.locator("p.se-text-paragraph").all()
    if len(all_p) < 2:
        # 단일 문단 또는 아직 본문이 없는 경우
        print("[!] 본문 문단을 찾지 못하여 스타일 적용을 건너뜁니다.")
        return False

    first_body_p = all_p[1]
    first_body_p.click()
    page.wait_for_timeout(400)
    # Control+A로 본문 전체 선택
    page.keyboard.press("Control+A")
    page.wait_for_timeout(400)

    # [2단계] 폰트 서체 (Font Family) 적용
    font_fam = style.get("font_family")
    if font_fam:
        target_val = FONT_FAMILY_MAP.get(font_fam, font_fam)
        try:
            ff_btn = frame.locator("button[data-name='font-family']").first
            if ff_btn.is_visible(timeout=3000):
                ff_btn.click()
                page.wait_for_timeout(400)
                opt = frame.locator(
                    f"button.se-toolbar-option-font-family-{target_val}-button, button[data-value='{target_val}']"
                ).first
                if opt.is_visible(timeout=2000):
                    opt.click()
                    print(f"[+] 폰트 서체 적용 완료: {font_fam} (코드: {target_val})")
                else:
                    print(f"[-] 폰트 옵션을 찾지 못함: {font_fam}")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"[!] 폰트 서체 적용 중 알림: {e}")

    # [3단계] 글자 크기 (Font Size) 적용
    font_sz = style.get("font_size")
    if font_sz:
        sz_val = str(font_sz).replace("pt", "").replace("px", "").strip()
        try:
            fs_btn = frame.locator("button[data-name='font-size']").first
            if fs_btn.is_visible(timeout=3000):
                fs_btn.click()
                page.wait_for_timeout(400)
                opt = frame.locator(
                    f"button.se-toolbar-option-font-size-code-fs{sz_val}-button, button[data-value='fs{sz_val}']"
                ).first
                if opt.is_visible(timeout=2000):
                    opt.click()
                    print(f"[+] 글자 크기 적용 완료: {sz_val}pt")
                else:
                    print(f"[-] 글자 크기 옵션을 찾지 못함: {sz_val}")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"[!] 글자 크기 적용 중 알림: {e}")

    # [4단계] 글자 색상 (Font Color) 적용
    font_color = style.get("font_color")
    if font_color:
        try:
            fc_btn = frame.locator("button[data-name='font-color']").first
            if fc_btn.is_visible(timeout=3000):
                fc_btn.click()
                page.wait_for_timeout(400)

                # 케이스 A: 색상없음 (네이버 기본 투명/기본 검정)
                if font_color in ["색상없음", "none", "default", "기본", ""]:
                    no_col = frame.locator("button.se-color-palette-no-color").first
                    if no_col.is_visible(timeout=2000):
                        no_col.click()
                        print("[+] 글자 색상 '색상없음' 적용 완료")
                else:
                    # 케이스 B: HEX 색상 코드 지정 (#000000, #333333 등)
                    hex_str = font_color.lower().strip()
                    if not hex_str.startswith("#"):
                        hex_with_hash = f"#{hex_str}"
                        hex_raw = hex_str
                    else:
                        hex_with_hash = hex_str
                        hex_raw = hex_str[1:]

                    # 1) 프리셋 팔레트에 존재하는지 먼저 확인
                    palette_btn = frame.locator(f"button.se-color-palette[data-color='{hex_with_hash}']").first
                    if palette_btn.is_visible(timeout=1000):
                        palette_btn.click()
                        print(f"[+] 팔레트 프리셋 색상 적용 완료: {hex_with_hash}")
                    else:
                        # 2) 프리셋에 없으면 '더보기' 버튼 클릭 후 커스텀 HEX 입력
                        more_btn = frame.locator(".se-color-picker-more-button").first
                        if more_btn.is_visible(timeout=1500):
                            more_btn.click()
                            page.wait_for_timeout(300)

                        hex_inp = frame.locator("input.se-selected-color-hex").first
                        apply_btn = frame.locator("button.se-color-picker-apply-button").first
                        if hex_inp.is_visible(timeout=2000) and apply_btn.is_visible(timeout=2000):
                            hex_inp.fill(hex_raw)
                            page.wait_for_timeout(200)
                            apply_btn.click()
                            print(f"[+] 커스텀 HEX 색상 적용 완료: {hex_with_hash}")
                        else:
                            print(f"[-] 색상 입력 필드를 찾지 못함: {hex_with_hash}")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"[!] 글자 색상 적용 중 알림: {e}")

    # [5단계] 텍스트 정렬 (Alignment) 적용
    align = style.get("align")
    if align:
        target_align = ALIGN_MAP.get(align, align)
        try:
            align_btn = frame.locator("button[data-name='align-drop-down-with-justify']").first
            if align_btn.is_visible(timeout=3000):
                align_btn.click()
                page.wait_for_timeout(400)
                opt = frame.locator(f"button.se-toolbar-option-{target_align}-button").first
                if opt.is_visible(timeout=2000):
                    opt.click()
                    print(f"[+] 텍스트 정렬 적용 완료: {align} ({target_align})")
                else:
                    print(f"[-] 정렬 옵션을 찾지 못함: {align}")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"[!] 텍스트 정렬 적용 중 알림: {e}")

    # [6단계] 줄간격 / 행간 (Line Height) 적용
    line_h = style.get("line_height")
    if line_h:
        lh_val = str(line_h).replace("%", "").strip()
        try:
            lh_btn = frame.locator("button[data-name='line-height']").first
            if lh_btn.is_visible(timeout=3000):
                lh_btn.click()
                page.wait_for_timeout(400)
                opt = frame.locator(
                    f"button.se-toolbar-option-line-height-{lh_val}-button, button[data-value='{lh_val}']"
                ).first
                if opt.is_visible(timeout=2000):
                    opt.click()
                    print(f"[+] 줄간격 적용 완료: {lh_val}%")
                else:
                    print(f"[-] 줄간격 옵션을 찾지 못함: {lh_val}")
                page.wait_for_timeout(300)
        except Exception as e:
            print(f"[!] 줄간격 적용 중 알림: {e}")

    return True
