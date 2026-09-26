"""사모펀드(PEF) 수급 데이터를 분석해서 네이버 블로그에 매일 자동으로 글을
쓰고 발행한다. main.py의 하루 1회 가드(_maybe_post_daily_blog)에서 호출됨.

브라우저 자동화는 Playwright로 --remote-debugging-port=9222
--user-data-dir=C:\\ChromeDebugProfile 로 띄워둔, 네이버에 이미 로그인된
크롬에 CDP로 붙는 방식이다(스킬 전용 .naver_profile 프로필은 이 프로젝트
에선 로그인 세션이 없어서 대신 이 방식을 쓴다). 그 크롬이 안 떠있으면
조용히 건너뛴다 — 예측 파이프라인을 막을 이유가 없다.

2026-09-23 실측으로 확인한 것들(전부 여기 반영돼 있음):
- 창 크기를 Playwright로 강제 조정(set_viewport_size)하면 사용자가 보고
  있는 실제 창이 계속 커졌다 작아졌다 해서 방해가 된다 — 안 건드린다.
- 고정 픽셀 좌표 클릭은 창 크기가 조금만 달라져도 다 어긋난다. 버튼은
  매번 bounding_box()로 실제 위치를 새로 구해서 그 중심을 클릭해야
  안정적으로 먹힌다.
- 폰트크기 드롭다운은 자동화로 다루면 간헐적으로 안 닫힌 채 남아서
  나중에 발행 버튼 클릭을 가로채는 사고가 났다 — 그래서 본문 서식은
  아예 안 건드리고 문단 사이 빈 줄로만 가독성을 준다.
- "이어서 작성하시겠습니까?" 팝업은 새 글 작성(Redirect=Write) 때는
  "취소"를 눌러야 진짜 새 글로 시작한다. 기존 글 수정(logNo= 지정)일 땐
  이 팝업의 확인/취소와 무관하게 예전 임시저장 내용이 뜰 수 있어서,
  제목/본문을 항상 쓰고 나서 검증하는 게 안전하다(여기서는 새 글만
  다루므로 취소로 충분).
- 제목/본문은 keyboard.type이 아니라 에디터의 input_buffer iframe에
  paste 이벤트를 쏴서 넣는다(_paste 참고) — 글자 단위 타이핑은 제목과
  본문이 섞이는 문제가 있었다(2026-09-26 원인 확인·수정).
- 발행 성공 여부는 블로그 홈을 다시 긁어서 logNo를 찾는 방식이 아니라
  (예전 글의 logNo를 잘못 주워서 성공한 것처럼 오탐났었다), 발행 버튼
  클릭 후 실제로 URL이 .../숫자 로 바뀌는지로 확인해야 한다.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import logging
import re
from pathlib import Path

import blog_card

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CDP_URL = "http://127.0.0.1:9222"  # localhost는 ::1로 풀려 연결 거부됨
_BLOG_ID = "opzx77"
_CATEGORY = "매일 주식 추천"
_SITE_URL = "https://ziego0445.github.io/kosdap/pef"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("%s 읽기 실패", path)
        return default


def _fmt_eok(won: float) -> str:
    return f"{won / 1e8:.1f}억"


def _ro(word: str) -> str:
    """받침 있으면 '으로', 없으면 '로' (한글 마지막 글자 기준)."""
    if not word:
        return "로"
    code = ord(word[-1]) - 0xAC00
    if 0 <= code <= 11171:
        return "으로" if code % 28 != 0 else "로"
    return "로"


def select_highlights() -> tuple[str | None, list[dict]]:
    """오늘자 PEF 데이터에서 블로그에 짚을 종목 최대 4개를 고른다.
    (tradeDate, [{"kind":..., "ticker":..., "name":..., "headline":..., "body":...}, ...])
    """
    flow = _load_json(_DATA_DIR / "pef_flow_activity.json", {})
    combined = _load_json(_DATA_DIR / "pef_combined_signal.json", {})
    activity = _load_json(_DATA_DIR / "pef_activity.json", {})

    trade_date = flow.get("tradeDate")
    flow_rows = flow.get("rows", [])
    combined_rows = combined.get("rows", [])
    activity_rows = activity.get("rows", [])

    highlights: list[dict] = []
    used_tickers: set[str] = set()

    # 1) 사모펀드 단독 연속매수 최장 스트릭
    if flow_rows:
        top = max(flow_rows, key=lambda r: r.get("consecutiveBuyDays", 0))
        used_tickers.add(top["ticker"])
        highlights.append({
            "name": top["corpName"],
            "ticker": top["ticker"],
            "card_stat": f"사모펀드 연속매수 {top['consecutiveBuyDays']}일째",
            "headline": f"{top['corpName']}({top['ticker']}) — 사모펀드 연속 매수 {top['consecutiveBuyDays']}일째",
            "body": (
                f"오늘로 {top['consecutiveBuyDays']}거래일 연속 순매수가 이어졌습니다. "
                f"오늘 하루 {_fmt_eok(top['netBuyValueKrw'])}, 누적으로는 {_fmt_eok(top['streakTotalValueKrw'])}이 "
                f"들어왔어요. 쉬지 않고 매일 사들이고 있다는 게 핵심으로, 단기 트레이딩이 아니라 "
                f"포지션을 꾸준히 쌓아가는 모습으로 읽힙니다."
            ),
        })

    # 2) 오늘 하루 유입액이 가장 큰 종목 (1번과 겹치면 다음으로)
    if flow_rows:
        by_today = sorted(flow_rows, key=lambda r: r.get("netBuyValueKrw", 0), reverse=True)
        for r in by_today:
            if r["ticker"] not in used_tickers:
                used_tickers.add(r["ticker"])
                inst_days = 0
                for c in combined_rows:
                    if c.get("ticker") == r["ticker"]:
                        inst_days = c.get("institutionConsecutiveBuyDays", 0)
                        break
                extra = (
                    f" 기관투자자도 {inst_days}거래일 연속으로 같이 들어오고 있어, 서로 다른 큰손 두 곳이 "
                    f"같은 방향을 보고 있다는 점이 눈에 띕니다."
                    if inst_days > 0 else ""
                )
                highlights.append({
                    "name": r["corpName"],
                    "ticker": r["ticker"],
                    "card_stat": f"오늘 하루 {_fmt_eok(r['netBuyValueKrw'])} 유입",
                    "headline": f"{r['corpName']}({r['ticker']}) — 오늘 하루만 {_fmt_eok(r['netBuyValueKrw'])} 유입",
                    "body": (
                        f"오늘 명단 중 하루 유입액이 가장 큰 종목입니다. 사모펀드가 {r['consecutiveBuyDays']}거래일 "
                        f"연속 순매수 중이에요.{extra}"
                    ),
                })
                break

    # 3) 사모+기관 동시 진입 중 가장 점수 높은 것 (겹치지 않는 종목)
    for c in combined_rows:
        if c["ticker"] in used_tickers:
            continue
        if c.get("pefConsecutiveBuyDays", 0) > 0 and c.get("institutionConsecutiveBuyDays", 0) > 0:
            used_tickers.add(c["ticker"])
            total = c.get("pefStreakTotalValueKrw", 0) + c.get("institutionStreakTotalValueKrw", 0)
            highlights.append({
                "name": c["corpName"],
                "ticker": c["ticker"],
                "card_stat": "사모+기관 동시 진입",
                "headline": (
                    f"{c['corpName']}({c['ticker']}) — 사모 {c['pefConsecutiveBuyDays']}일 + "
                    f"기관 {c['institutionConsecutiveBuyDays']}일, 두 세력이 동시에 진입"
                ),
                "body": (
                    f"사모펀드와 기관투자자가 같은 시기에 나란히 순매수를 이어가고 있는 케이스입니다. "
                    f"두 세력의 누적 순매수를 합치면 약 {_fmt_eok(total)} 규모예요. 서로 다른 성격의 큰손 "
                    f"두 곳이 동시에 같은 방향을 보고 있다는 건, 어느 한쪽만 사는 것보다 의미 있는 신호로 "
                    f"볼 수 있습니다."
                ),
            })
            break

    # 4) 최근 DART 5%룰 신규/변경 공시 중 가장 최신 것
    if activity_rows:
        recent = sorted(activity_rows, key=lambda r: r.get("latestReportDate", ""), reverse=True)[0]
        reporters = ", ".join(recent.get("pefReporters", []))
        reason = recent.get("latestReportReason", "대량보유")
        value_krw = recent.get("pefNetBuyValueKrw") or 0
        is_partial = recent.get("pefNetBuyValueIsPartial")
        amount_clause = (
            f"(약 {_fmt_eok(value_krw)} 규모) " if value_krw and not is_partial else ""
        )
        highlights.append({
            "name": recent["corpName"],
            "ticker": recent["stockCode"],
            "card_stat": f"{reason}{_ro(reason)} 지분 {recent['pefNetBuyRatioPercent']}% 확보",
            "headline": (
                f"{recent['corpName']}({recent['stockCode']}) — {reason}{_ro(reason)} "
                f"지분 {recent['pefNetBuyRatioPercent']}% 신규 확보 공시"
            ),
            "body": (
                f"이건 매일 조금씩 쌓이는 순매수와는 결이 다른 이벤트예요. {reporters}가 "
                f"{recent.get('latestReportDate', '')}에 지분 {recent['pefNetBuyRatioPercent']}% "
                f"{amount_clause}대량보유 공시를 냈습니다. 사유는 '{reason}'입니다."
            ),
        })

    return trade_date, highlights[:4]


def generate_post(trade_date: str, highlights: list[dict]) -> tuple[str, list[str], str, str]:
    """(제목, 본문 줄 리스트('' = 빈 줄), 태그문자열, 한글날짜) 반환."""
    date_kr = trade_date
    try:
        d = dt.date.fromisoformat(trade_date)
        date_kr = f"{d.year}년 {d.month}월 {d.day}일"
    except (ValueError, TypeError):
        pass

    title = f"[사모펀드 수급 리포트] {date_kr} 거래일 — {highlights[0]['headline'].split(' — ',1)[1]}" if highlights else \
        f"[사모펀드 수급 리포트] {date_kr} 거래일"

    lines: list[str] = [
        "매일 코스피·코스닥 전 종목의 사모펀드(PEF) 순매수 동향과 DART 5%룰 대량보유 공시를 자동으로 "
        f"취합해서, 그중 흐름이 눈에 띄는 종목을 짚어보는 코너입니다. 오늘은 {date_kr} 거래일 기준 데이터예요.",
        "",
    ]
    for h in highlights:
        lines.append(f"▶ {h['headline']}")
        lines.append(h["body"])
        lines.append("")

    lines += [
        "오늘 짚은 종목들은 '사모펀드/기관이 순매수했다 = 주가가 오른다'는 뜻이 아니라, 공개된 수급 "
        "데이터에서 흐름이 두드러졌다는 사실을 정리한 겁니다. 투자 판단은 각자의 몫이고, 이 글은 투자 "
        "권유가 아닌 정보 공유 목적임을 밝힙니다.",
        "",
        "이 데이터는 제가 직접 만든 사이트에서 매일 자동으로 수집·정리하고 있어요. 전체 랭킹과 상세 "
        "수급 흐름은 아래 주소에서 직접 확인하실 수 있습니다.",
        _SITE_URL,
        "",
        "다음 거래일 데이터도 정리되는 대로 이어서 올릴게요.",
    ]

    tickers = [h["ticker"] for h in highlights]
    tags = ",".join(["사모펀드", "기관수급", "주식투자", "DART공시", *tickers[:4]])
    return title, lines, tags, date_kr


_PASTE_JS = """
([text, htmlStr]) => {
  const dt = new DataTransfer();
  dt.setData('text/plain', text);
  if (htmlStr) dt.setData('text/html', htmlStr);
  const target = document.activeElement || document.body;
  target.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
}
"""


def _click_center(page, locator) -> None:
    b = locator.bounding_box()
    page.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)


def _paste(frame, text: str, html_str: str | None) -> bool:
    # 스마트에디터는 모든 칸이 공유하는 숨은 input_buffer iframe으로 키 입력을
    # 받아 포커스된 칸에 옮겨 적는다. 한 글자씩 치면 칸을 옮길 때 버퍼에 남은
    # 글자가 다른 칸으로 새서 제목/본문이 섞였다 — 통째로 paste 이벤트 한 번.
    for child in frame.child_frames:
        if child.name.startswith("input_buffer"):
            child.evaluate(_PASTE_JS, [text, html_str])
            return True
    return False


def _lines_to_html(lines: list[str]) -> str:
    out = []
    for ln in lines:
        if ln == "":
            out.append("<p><br></p>")
        elif ln.startswith("▶"):
            out.append(f"<p><b>{html.escape(ln)}</b></p>")
        else:
            out.append(f"<p>{html.escape(ln)}</p>")
    return "".join(out)


def publish_to_naver(title: str, lines: list[str], tags: str, image_path: Path | None = None) -> str | None:
    """새 글로 작성해서 발행. 성공하면 게시글 URL, 실패하면 None (예외를
    올리지 않는다 — 크롬이 안 떠있거나 로그인이 안 된 상태가 흔할 수 있어서
    호출부가 조용히 넘어가게 한다)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright 미설치 — 블로그 발행 건너뜀")
        return None

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(_CDP_URL, timeout=5000)
            except Exception:
                logger.warning(
                    "디버그 크롬(%s)에 연결 실패 — 블로그 발행 건너뜀 "
                    "(--remote-debugging-port=9222 --user-data-dir=C:\\ChromeDebugProfile 로 "
                    "네이버 로그인된 크롬을 띄워두면 다음 사이클에 자동으로 됨)",
                    _CDP_URL,
                )
                return None

            context = browser.contexts[0]
            page = context.new_page()  # 창 크기는 절대 건드리지 않는다 (실측: 사용자 창이 계속 리사이즈됨)

            write_url = f"https://blog.naver.com/{_BLOG_ID}?Redirect=Write"
            page.goto(write_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

            if "nidlogin" in page.url or any("nidlogin" in f.url for f in page.frames):
                logger.warning("네이버 로그인이 안 되어 있음 — 블로그 발행 건너뜀")
                page.close()
                return None

            frame = page.frame(url=lambda u: "PostWriteForm" in u)
            if frame is None:
                logger.warning("에디터 프레임을 못 찾음 — 블로그 발행 건너뜀")
                page.close()
                return None

            try:
                if frame.locator(".se-popup-alert-confirm").count() > 0:
                    cancel = frame.locator(".se-popup-alert-confirm").locator("text=취소").first
                    box = cancel.bounding_box()
                    if box:
                        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    page.wait_for_timeout(1200)
            except Exception:
                pass

            title_el = frame.locator(".se-title-text").first
            _click_center(page, title_el)
            page.wait_for_timeout(400)
            if not _paste(frame, title, None):
                logger.warning("에디터 입력 버퍼를 못 찾음 — 발행 중단")
                page.close()
                return None
            page.wait_for_timeout(800)

            _click_center(page, frame.locator(".se-component-content .se-text-paragraph, .se-placeholder").last)
            page.wait_for_timeout(400)
            _paste(frame, "\n".join(lines), _lines_to_html(lines))
            page.wait_for_timeout(2000)

            if image_path and image_path.exists():
                try:
                    _click_center(page, frame.locator(".se-component-content .se-text-paragraph").last)
                    page.keyboard.press("End")
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        frame.click("button[data-name='image']", timeout=5000)
                    fc_info.value.set_files(str(image_path))
                    page.wait_for_timeout(5000)
                    if frame.locator(".se-popup-transfer-error").count() > 0:
                        logger.warning("요약 카드 이미지 업로드 실패")
                        page.keyboard.press("Escape")
                except Exception:
                    logger.exception("요약 카드 이미지 삽입 실패 — 이미지 없이 진행")

            page.wait_for_timeout(1500)
            got_title = title_el.inner_text().replace("\xa0", " ").strip()
            if got_title != title:
                logger.warning("제목 검증 실패 — 발행 중단 (기대=%r, 실제=%r)", title, got_title)
                return None

            open_btn = frame.get_by_text("발행", exact=True).first
            obox = open_btn.bounding_box()
            page.mouse.click(obox["x"] + obox["width"] / 2, obox["y"] + obox["height"] / 2)
            page.wait_for_timeout(1500)

            try:
                cat_label = frame.get_by_text("카테고리", exact=True).first
                cbox = cat_label.bounding_box()
                page.mouse.click(cbox["x"] + 280, cbox["y"] + cbox["height"] / 2)
                page.wait_for_timeout(600)
                target = frame.get_by_text(_CATEGORY, exact=True).first
                tbox2 = target.bounding_box()
                if tbox2:
                    page.mouse.click(tbox2["x"] + tbox2["width"] / 2, tbox2["y"] + tbox2["height"] / 2)
                    page.wait_for_timeout(300)
            except Exception:
                logger.warning("카테고리 설정 실패 — 기본 카테고리로 발행됨")

            if tags:
                try:
                    tag_input = frame.locator("input[placeholder*='태그 입력']")
                    tag_input.click(timeout=3000)
                    for tag in tags.split(","):
                        tag = tag.strip()
                        if tag:
                            page.keyboard.type(tag, delay=12)
                            page.keyboard.press("Enter")
                    page.wait_for_timeout(300)
                except Exception:
                    logger.warning("태그 입력 실패")

            confirm_btns = frame.get_by_text("발행", exact=True)
            real_btn, best_y = None, -1
            for i in range(confirm_btns.count()):
                b = confirm_btns.nth(i).bounding_box()
                if b and b["y"] > best_y:
                    best_y, real_btn = b["y"], b
            if real_btn is None:
                logger.warning("발행 버튼을 못 찾음 — 발행 실패")
                page.close()
                return None

            pre_url = page.url
            page.mouse.click(real_btn["x"] + real_btn["width"] / 2, real_btn["y"] + real_btn["height"] / 2)
            page.wait_for_timeout(4000)

            for _ in range(10):
                if page.url != pre_url and re.search(r"/\d+$", page.url.split("?")[0]):
                    break
                page.wait_for_timeout(1000)

            page.close()
            if page.url != pre_url and re.search(r"/\d+$", page.url.split("?")[0]):
                return page.url.split("?")[0]
            logger.warning("발행 확인 실패 — 최종 URL: %s", page.url)
            return None
    except Exception:
        logger.exception("네이버 블로그 발행 중 예외 발생")
        return None


_DRAFT_PATH = _DATA_DIR / "blog_post_draft.txt"
_PUBLISHED_PATH = _DATA_DIR / "blog_last_published.json"


def save_draft(title: str, lines: list[str], tags: str, card_path: Path | None, trade_date: str) -> Path:
    """발행은 안 하고(2026-09-24부터: 실제 업로드는 사람이 ChatGPT 등을 통해
    직접 한다 — 네이버 에디터 자동화가 발행 직전에 제목/본문 첫 줄이 서로
    섞이는 문제가 반복돼서, 브라우저 자동 발행은 당분간 포기하고 준비만
    한다) 그냥 사람이 바로 복사해서 쓸 수 있는 텍스트 파일로 저장한다."""
    body = "\n".join(lines)
    content = (
        f"# {title}\n\n"
        f"(기준 거래일: {trade_date} / 카테고리: {_CATEGORY} / 태그: {tags})\n"
        f"(맨 위 ▶ 로 시작하는 줄은 굵게 넣으면 좋습니다. 요약 카드 이미지는 "
        f"맨 아래에 첨부: {card_path})\n\n"
        f"{body}\n"
    )
    _DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DRAFT_PATH.write_text(content, encoding="utf-8")
    return _DRAFT_PATH


def run_daily_post() -> None:
    trade_date, highlights = select_highlights()
    if not trade_date or not highlights:
        logger.warning("PEF 데이터가 비어있어 블로그 글을 못 만듦 — 건너뜀")
        return
    title, lines, tags, date_kr = generate_post(trade_date, highlights)

    card_path = None
    try:
        card_path = blog_card.render_summary_card(
            date_kr, highlights, _DATA_DIR / "blog_card_today.png"
        )
    except Exception:
        logger.exception("요약 카드 이미지 생성 실패 — 이미지 없이 준비")

    draft_path = save_draft(title, lines, tags, card_path, trade_date)
    logger.info("네이버 블로그용 글 준비 완료 (%s 기준): %s", trade_date, draft_path)

    published = _load_json(_PUBLISHED_PATH, {})
    if published.get("trade_date") == trade_date:
        logger.info("%s 거래일 글은 이미 발행됨(%s) — 휴장일 중복 발행 방지로 건너뜀",
                    trade_date, published.get("url"))
        return

    url = publish_to_naver(title, lines, tags, card_path)
    if url:
        _PUBLISHED_PATH.write_text(
            json.dumps({"trade_date": trade_date, "url": url}, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("네이버 블로그 발행 완료: %s", url)
    else:
        logger.warning("네이버 블로그 자동 발행 실패 — draft 파일로 수동 업로드 필요")
