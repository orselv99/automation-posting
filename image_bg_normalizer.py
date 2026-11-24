"""
[삽화 배경색 #ece0c6 정밀 보정 모듈 (image_bg_normalizer.py)]

AI 이미지 생성 모델(Imagen 등)은 프롬프트에 '#ece0c6'을 명시하더라도
실제 픽셀 값이 #ecd9b0 ~ #eedebc 등으로 ±10~25 RGB 오차가 발생합니다.
이 모듈은 외부 파이썬 패키지(Pillow/NumPy) 없이 Windows 내장 .NET System.Drawing(LockBits)을 사용해
생성된 삽화의 배경을 네이버 블로그 스킨 배경색(#ece0c6, RGB 236,224,198)으로 100% 정확하게 일치시킵니다.

동작 원리:
1. 이미지 4면 테두리 픽셀의 중앙값(Median)으로 실제 생성된 배경색(bgR, bgG, bgB)을 자동 감지
2. 감지된 배경색과의 유클리드 RGB 거리가 임계값 이내인 배경 픽셀을 #ece0c6으로 부드럽게 스냅
   (d <= 22: 100% #ece0c6 / 22 < d < 48: 선형 블렌딩으로 수채화·펜화 경계 자연스럽게 유지)
3. 최외곽 20px 테두리를 #ece0c6으로 미세 페더링하여 블로그 캔버스와 이음새(사각 테두리) 완전 제거
"""
import os
import sys
import json
import subprocess
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

TARGET_HEX = "#ece0c6"
TARGET_RGB = (236, 224, 198)

_PS_SCRIPT = r'''
$InputPath   = $env:BG_NORM_INPUT
$OutputPath  = $env:BG_NORM_OUTPUT
$TargetR     = [int]$env:BG_NORM_TR
$TargetG     = [int]$env:BG_NORM_TG
$TargetB     = [int]$env:BG_NORM_TB
$LowThresh   = [double]$env:BG_NORM_LOW
$HighThresh  = [double]$env:BG_NORM_HIGH
$EdgeFeather = [int]$env:BG_NORM_EDGE

$code = @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class BgNormalizer {
    public static string Process(string inPath, string outPath, int tR, int tG, int tB, double lowT, double highT, int edgeFeather) {
        byte[] srcBytes = System.IO.File.ReadAllBytes(inPath);
        using (var ms = new System.IO.MemoryStream(srcBytes))
        using (Bitmap src = new Bitmap(ms))
        using (Bitmap bmp = new Bitmap(src.Width, src.Height, PixelFormat.Format24bppRgb)) {
            using (Graphics g = Graphics.FromImage(bmp)) {
                g.DrawImage(src, 0, 0, src.Width, src.Height);
            }
            int w = bmp.Width;
            int h = bmp.Height;
            Rectangle rect = new Rectangle(0, 0, w, h);
            BitmapData data = bmp.LockBits(rect, ImageLockMode.ReadWrite, PixelFormat.Format24bppRgb);
            int stride = data.Stride;
            int totalBytes = stride * h;
            byte[] buf = new byte[totalBytes];
            Marshal.Copy(data.Scan0, buf, 0, totalBytes);

            // 1. Sample 4 borders (inset 4px) to detect median generated background color
            List<int> rs = new List<int>();
            List<int> gs = new List<int>();
            List<int> bs = new List<int>();
            int inset = Math.Min(4, Math.Min(w / 10, h / 10));
            int stepX = Math.Max(1, w / 50);
            int stepY = Math.Max(1, h / 50);
            for (int x = inset; x < w - inset; x += stepX) {
                int idxTop = inset * stride + x * 3;
                bs.Add(buf[idxTop]); gs.Add(buf[idxTop + 1]); rs.Add(buf[idxTop + 2]);
                int idxBot = (h - 1 - inset) * stride + x * 3;
                bs.Add(buf[idxBot]); gs.Add(buf[idxBot + 1]); rs.Add(buf[idxBot + 2]);
            }
            for (int y = inset; y < h - inset; y += stepY) {
                int idxLeft = y * stride + inset * 3;
                bs.Add(buf[idxLeft]); gs.Add(buf[idxLeft + 1]); rs.Add(buf[idxLeft + 2]);
                int idxRight = y * stride + (w - 1 - inset) * 3;
                bs.Add(buf[idxRight]); gs.Add(buf[idxRight + 1]); rs.Add(buf[idxRight + 2]);
            }
            rs.Sort(); gs.Sort(); bs.Sort();
            int bgR = rs[rs.Count / 2];
            int bgG = gs[gs.Count / 2];
            int bgB = bs[bs.Count / 2];

            double span = Math.Max(1.0, highT - lowT);

            // 2. Soft color-distance snapping + outer margin vignette feathering
            for (int y = 0; y < h; y++) {
                int row = y * stride;
                int dy = Math.Min(y, h - 1 - y);
                for (int x = 0; x < w; x++) {
                    int idx = row + x * 3;
                    int b = buf[idx];
                    int g = buf[idx + 1];
                    int r = buf[idx + 2];

                    double dr = r - bgR;
                    double dg = g - bgG;
                    double db = b - bgB;
                    double dist = Math.Sqrt(dr * dr + dg * dg + db * db);

                    double nr = r, ng = g, nb = b;
                    if (dist <= lowT) {
                        nr = tR; ng = tG; nb = tB;
                    } else if (dist < highT) {
                        double alpha = (dist - lowT) / span;
                        nr = tR + (r - tR) * alpha;
                        ng = tG + (g - tG) * alpha;
                        nb = tB + (b - tB) * alpha;
                    }

                    if (edgeFeather > 0) {
                        int edgeDist = Math.Min(dy, Math.Min(x, w - 1 - x));
                        if (edgeDist < edgeFeather) {
                            double ea = (double)edgeDist / edgeFeather;
                            nr = tR + (nr - tR) * ea;
                            ng = tG + (ng - tG) * ea;
                            nb = tB + (nb - tB) * ea;
                        }
                    }

                    buf[idx]     = (byte)Math.Max(0, Math.Min(255, (int)Math.Round(nb)));
                    buf[idx + 1] = (byte)Math.Max(0, Math.Min(255, (int)Math.Round(ng)));
                    buf[idx + 2] = (byte)Math.Max(0, Math.Min(255, (int)Math.Round(nr)));
                }
            }

            Marshal.Copy(buf, 0, data.Scan0, totalBytes);
            bmp.UnlockBits(data);

            string tmpPath = outPath + ".tmp.png";
            bmp.Save(tmpPath, ImageFormat.Png);
            if (System.IO.File.Exists(outPath)) {
                System.IO.File.Delete(outPath);
            }
            System.IO.File.Move(tmpPath, outPath);

            return string.Format("{{\"detected_bg\":\"#{0:x2}{1:x2}{2:x2}\",\"target_bg\":\"#{3:x2}{4:x2}{5:x2}\",\"width\":{6},\"height\":{7}}}",
                bgR, bgG, bgB, tR, tG, tB, w, h);
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing
[BgNormalizer]::Process($InputPath, $OutputPath, $TargetR, $TargetG, $TargetB, $LowThresh, $HighThresh, $EdgeFeather)
'''


def _parse_hex(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def normalize_background(
    image_path: str | Path,
    output_path: str | Path = None,
    target_hex: str = TARGET_HEX,
    low_thresh: float = 22.0,
    high_thresh: float = 48.0,
    edge_feather: int = 20,
) -> dict:
    """
    단일 이미지의 배경색을 target_hex(#ece0c6)로 정밀 보정합니다.
    output_path 생략 시 원본 파일을 안전하게 제자리(in-place) 갱신합니다.
    """
    src = Path(image_path).resolve()
    if not src.exists():
        return {"status": "error", "error": f"파일을 찾을 수 없습니다: {src}"}

    dst = Path(output_path).resolve() if output_path else src
    dst.parent.mkdir(parents=True, exist_ok=True)
    tr, tg, tb = _parse_hex(target_hex)

    # 임시 ps1 스크립트를 통해 실행 (한글 경로는 환경변수로 UTF-8 안전 전달)
    ps_file = Path(__file__).resolve().parent / ".tmp_bg_norm.ps1"
    try:
        ps_file.write_text(_PS_SCRIPT, encoding="utf-8-sig")
        env = os.environ.copy()
        env.update({
            "BG_NORM_INPUT": str(src),
            "BG_NORM_OUTPUT": str(dst),
            "BG_NORM_TR": str(tr),
            "BG_NORM_TG": str(tg),
            "BG_NORM_TB": str(tb),
            "BG_NORM_LOW": str(low_thresh),
            "BG_NORM_HIGH": str(high_thresh),
            "BG_NORM_EDGE": str(edge_feather),
        })
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(ps_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=60)
        if res.returncode != 0 or not res.stdout.strip():
            return {"status": "error", "error": (res.stderr or res.stdout or f"exit={res.returncode}").strip()}

        out_line = res.stdout.strip().splitlines()[-1]
        info = json.loads(out_line)
        info["status"] = "ok"
        info["path"] = str(dst)
        print(f"[+] 배경색 보정 완료 ({dst.name}): {info['detected_bg']} -> {info['target_bg']} ({info['width']}x{info['height']})")
        return info
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        ps_file.unlink(missing_ok=True)


def normalize_images(image_paths: list[str | Path], target_hex: str = TARGET_HEX) -> list[dict]:
    """여러 이미지의 배경색을 순차적으로 #ece0c6에 맞춰 보정합니다."""
    results = []
    for p in image_paths:
        if p and os.path.exists(p):
            results.append(normalize_background(p, target_hex=target_hex))
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python image_bg_normalizer.py <이미지1.png> [이미지2.png ...]")
        sys.exit(1)
    for arg in sys.argv[1:]:
        r = normalize_background(arg)
        if r.get("status") != "ok":
            print(f"[!] 보정 실패 ({arg}): {r.get('error')}")
            sys.exit(1)
