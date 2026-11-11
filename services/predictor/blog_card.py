"""사모펀드 수급 리포트 블로그 글에 넣을 "오늘의 요약 카드" 이미지 생성.

배경(어두운 금융 리포트풍 그래픽)은 ChatGPT(Codex CLI)에게 한 번만 생성을
시키고 로컬에 캐싱해서 매일 재사용한다 — AI 이미지 생성은 한글 텍스트를
정확히 못 그리는 경우가 많고(실측: diffusion 계열 모델이 한글을 깨진
글자로 그림), 매일 새로 생성하면 사용량도 아깝다. 대신 종목명/숫자 같은
실제 텍스트는 Pillow로 직접 그려서(맑은 고딕 폰트) 정확성을 보장한다.

배경 생성은 이 워크스테이션에 로그인된 codex CLI(ChatGPT 계정)를 그대로
쓴다 — chatgpt-cli-image-gen 스킬과 같은 방식(codex exec에 stdin으로
지시문을 보내고, 결과를 지정 경로로 복사하게 시킴)이지만, 스킬 파일
경로(사용자 홈 디렉터리 밑)에 의존하지 않도록 이 프로젝트 안에 필요한
로직만 자체적으로 구현했다(다른 환경에서도 git으로 그대로 재현 가능).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_BACKGROUND_PATH = _ASSETS_DIR / "blog_card_bg.png"
_FONT_DIR = Path("C:/Windows/Fonts")

_BACKGROUND_PROMPT = (
    "A dark navy financial report card background, minimalist, professional "
    "stock market theme. Subtle abstract line chart trending upward in the "
    "bottom third, thin glowing teal and white gridlines, soft gradient from "
    "deep navy to near-black, small abstract candlestick bar motifs scattered "
    "faintly in the background, plenty of empty clean space in the upper 60% "
    "of the image for text overlay, no text, no numbers, no letters, no logos, "
    "corporate finance report aesthetic, flat vector style, 16:9"
)

_ACCENT_COLORS = [
    (110, 231, 183),  # teal
    (110, 231, 183),
    (255, 210, 110),  # amber
    (255, 160, 160),  # coral
]


def _generate_background_via_codex(timeout: int = 300) -> bool:
    codex_exe = shutil.which("codex")
    if codex_exe is None:
        logger.warning("codex CLI를 못 찾음 — 요약 카드 배경 생성 건너뜀")
        return False

    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    prompt = textwrap.dedent(f"""
        You are acting as an image-generation worker, not a coding assistant. Do not
        write application code for this task.

        Use your built-in image-generation tool to create the image described below,
        then save the result to this exact path. Create parent directories if needed,
        and overwrite the file if it already exists.

        Target path: {_BACKGROUND_PATH}

        Image description: {_BACKGROUND_PROMPT}

        Requirements:
        - Target resolution: 1536x1024.

        Your image tool saves its raw output under a Codex-managed directory
        (typically CODEX_HOME/generated_images/<session>/call_*.png) - after calling
        it, copy or move that output file to the exact target path above using a
        shell command. Do not just leave it in the Codex-managed directory.

        Do not ask for confirmation and do not stop to explain your plan - pick a
        reasonable approach and execute it. When finished, verify the target path
        exists and is a non-empty real image file, then print the absolute path as
        your final message.
    """).strip()

    cmd = [codex_exe, "exec", "-C", str(_ASSETS_DIR), "--skip-git-repo-check", "-s", "workspace-write"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        last_message_file = f.name
    cmd += ["-o", last_message_file, "-"]

    try:
        subprocess.run(cmd, input=prompt.encode("utf-8"), timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.exception("codex 배경 이미지 생성 실패")
        return False

    return _BACKGROUND_PATH.exists() and _BACKGROUND_PATH.stat().st_size > 0


def ensure_background() -> Path | None:
    """캐싱된 배경이 있으면 그대로 쓰고, 없으면 codex로 한 번만 생성한다."""
    if _BACKGROUND_PATH.exists() and _BACKGROUND_PATH.stat().st_size > 0:
        return _BACKGROUND_PATH
    if _generate_background_via_codex():
        return _BACKGROUND_PATH
    return None


def render_summary_card(trade_date_kr: str, highlights: list[dict], out_path: Path) -> Path | None:
    """highlights: [{"name":, "ticker":, "card_big":, "card_label":}, ...] (최대 4개, card_label 없으면 card_stat).
    성공하면 out_path, 배경이 없으면(codex 실패) None."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow 미설치 — 요약 카드 생성 건너뜀")
        return None

    bg_path = ensure_background()
    if bg_path is None:
        return None

    # 2026-11-12 개편(『스틱!』 원칙 — 한눈에): 제목은 질문형 훅, 각 줄은
    # "종목명 + 쉬운 설명(왼쪽) / 핵심 숫자 크게(오른쪽)" 2단 구성.
    # 예전엔 공시 사유 원문을 그대로 써서 줄이 화면 끝까지 넘쳤다.
    font_title = ImageFont.truetype(str(_FONT_DIR / "malgunbd.ttf"), 60)
    font_date = ImageFont.truetype(str(_FONT_DIR / "malgun.ttf"), 30)
    font_name = ImageFont.truetype(str(_FONT_DIR / "malgunbd.ttf"), 40)
    font_stat = ImageFont.truetype(str(_FONT_DIR / "malgun.ttf"), 28)
    font_big = ImageFont.truetype(str(_FONT_DIR / "malgunbd.ttf"), 52)
    font_num = ImageFont.truetype(str(_FONT_DIR / "malgunbd.ttf"), 30)

    img = Image.open(bg_path).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    draw.text((70, 48), "오늘 큰손이 담은 종목은?", font=font_title, fill=(255, 255, 255, 255))
    draw.text((72, 126), f"{trade_date_kr} · 사모펀드 장바구니 공개", font=font_date, fill=(150, 200, 220, 255))
    draw.line([(70, 182), (W - 70, 182)], fill=(80, 140, 160, 180), width=2)

    y = 206
    row_h = 96
    right_x = W - 70
    for i, h in enumerate(highlights[:4]):
        color = _ACCENT_COLORS[i % len(_ACCENT_COLORS)]
        # 반투명 줄 배경 — 아래쪽 차트 그래픽과 겹쳐도 글자가 읽히게
        draw.rounded_rectangle([(60, y), (W - 60, y + row_h - 10)], radius=14, fill=(8, 20, 40, 170))
        draw.ellipse([(78, y + 22), (122, y + 66)], fill=color + (255,))
        num = str(i + 1)
        draw.text((100 - draw.textlength(num, font=font_num) / 2, y + 24), num, font=font_num, fill=(10, 25, 45, 255))
        draw.text((142, y + 4), h["name"], font=font_name, fill=(255, 255, 255, 255))
        label = h.get("card_label") or h.get("card_stat", "")
        draw.text((142, y + 50), label, font=font_stat, fill=(190, 205, 220, 255))
        big = h.get("card_big")
        if big:
            draw.text((right_x - 20 - draw.textlength(big, font=font_big), y + 12), big, font=font_big, fill=color + (255,))
        y += row_h

    draw.text((70, H - 60), "kosdap · KRX·DART 공개 데이터 매일 자동 수집 · 투자 권유 아님", font=font_date, fill=(140, 150, 165, 220))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
