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


# --- 글 구성 원칙 (2026-11-12, 사용자 요청: 책 『스틱!』의 SUCCESs 원칙) ---
# 초보자도 첫 화면에서 "무슨 얘기인지" 바로 알게 하는 게 목표다.
# - Simple: 맨 위 "30초 요약"에서 종목당 한 줄로 핵심만.
# - Unexpected: 제목/도입을 궁금증으로 연다("큰손 장바구니는 매일 공개된다").
#   종목마다 "근데 주의할 점"을 둬서 뻔한 결론(=오른다)을 스스로 깬다.
# - Concrete: 숫자를 체감 단위로 바꾼다(16거래일→약 3주, 비중 14.5%→
#   오간 돈 100원 중 15원어치).
# - Credible: 출처(KRX/DART)와 비교 기준(최근 1년 중 n번째)을 밝힌다.
# - Emotional: "큰손 vs 나" 관점, 끝에 독자 질문.
# - Stories: 종목마다 "한 줄 훅 → 숫자로 보면 → 왜 볼 만한가 → 주의할 점".
# kosdap 원칙(계산된 사실은 보여주되 매수/매도 판단은 안 함)은 그대로다 —
# 해석은 "그렇게 보는 시각이 많다" 수준까지만, 사라/팔라는 말은 쓰지 않는다.

_CIRCLED = ["①", "②", "③", "④"]
_TOP_RANK_HIGHLIGHT = 20  # "최근 1년 중 n번째로 큰 매수"는 이 순위 안일 때만 언급


def _weeks_phrase(trading_days: int) -> str:
    """거래일 수를 달력 감각으로: 16 → '약 3주', 3 → '3일'."""
    if trading_days < 5:
        return f"{trading_days}일"
    weeks = round(trading_days / 5)
    if weeks >= 8:
        return f"약 {round(trading_days / 21)}개월"
    return f"약 {weeks}주"


def _won_of_100(percent: float) -> str:
    return f"오간 돈 100원 중 약 {int(percent + 0.5)}원어치를 사모펀드가 샀어요"


def _price_fact(pct: float | None) -> str | None:
    if pct is None:
        return None
    sign = "+" if pct > 0 else ""
    return f"매수가 이어진 동안 주가: {sign}{pct}%"


def _volume_fact(ratio: float | None) -> str | None:
    if ratio is None or ratio < 1.5:
        return None
    return f"오늘 거래량: 평소(최근 20일 평균)의 {ratio}배 — 유난히 북적인 날"


def _caution(price_pct: float | None) -> str:
    """'큰손이 샀다 = 오른다'는 뻔한 결론을 스스로 깨는 한 줄 (Unexpected)."""
    if price_pct is not None and price_pct >= 15:
        return (
            f"주의할 점: 매수가 이어지는 동안 주가가 이미 {price_pct}% 올랐어요. "
            "지금 들어가면 큰손보다 꽤 비싼 값에 사는 셈이라는 것도 같이 봐야 합니다."
        )
    if price_pct is not None and price_pct < 0:
        return (
            f"반전 포인트: 이렇게 사는데도 주가는 오히려 {price_pct}%예요. "
            "큰손도 지금은 손실 구간일 수 있다는 뜻 — 큰손이라고 늘 맞는 건 아닙니다."
        )
    return "주의할 점: 연속 기록은 언젠가 끊겨요. 언제, 어떻게 끊기는지도 같이 지켜볼 포인트입니다."


def _rank_phrase(rank: int | None, sample_days: int | None) -> str | None:
    if not rank or rank > _TOP_RANK_HIGHLIGHT:
        return None
    if rank == 1:
        return f"최근 1년({sample_days}거래일) 중 가장 큰 하루 매수"
    return f"최근 1년({sample_days}거래일) 중 {rank}번째로 큰 하루 매수"


def _flow_common_facts(r: dict) -> list[str]:
    facts = []
    if r.get("pefBuySharePercent"):
        facts.append(f"오늘 사모 비중: {r['pefBuySharePercent']}% ({_won_of_100(r['pefBuySharePercent'])})")
    for f in (_volume_fact(r.get("volumeRatio")), _price_fact(r.get("streakPriceChangePercent"))):
        if f:
            facts.append(f)
    return facts


def select_highlights() -> tuple[str | None, list[dict]]:
    """오늘자 PEF 데이터에서 블로그에 짚을 종목 최대 4개를 고른다.

    각 항목: name, ticker, headline(훅 한 줄), summary(30초 요약용),
    facts(숫자 bullet), body(왜 볼 만한가), caution(주의할 점),
    card_big/card_label(요약 카드용), card_stat(하위호환용 한 줄).
    blog_post_draft.json을 읽는 쪽(쇼츠 내레이션)은 headline/body만 쓴다.
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

    # 1) 사모펀드 단독 연속매수 최장 스트릭 — "꾸준함" 이야기
    if flow_rows:
        top = max(flow_rows, key=lambda r: r.get("consecutiveBuyDays", 0))
        used_tickers.add(top["ticker"])
        n = top["consecutiveBuyDays"]
        total = top["streakTotalValueKrw"]
        facts = [
            f"연속 순매수: {n}거래일 (달력으로 {_weeks_phrase(n)})",
            f"쌓인 금액: {_fmt_eok(total)} (하루 평균 약 {_fmt_eok(total / max(n, 1))})",
        ]
        rank_p = _rank_phrase(top.get("rank"), top.get("sampleDays"))
        facts.append(f"오늘 순매수: {_fmt_eok(top['netBuyValueKrw'])}" + (f" — {rank_p}" if rank_p else ""))
        facts += _flow_common_facts(top)
        highlights.append({
            "kind": "streak",
            "name": top["corpName"],
            "ticker": top["ticker"],
            "headline": f"{top['corpName']} — {_weeks_phrase(n)} 동안 하루도 안 쉬고 샀다",
            "summary": f"사모펀드가 {n}거래일({_weeks_phrase(n)}) 내리 순매수",
            "facts": facts,
            "body": (
                "하루에 크게 한 번 사는 건 단발성 거래(블록딜 등)일 수도 있어요. 그런데 "
                f"{_weeks_phrase(n)} 동안 매일 샀다는 건 이야기가 달라요. 한 번에 사면 가격이 "
                "튀니까 조금씩 나눠서 모으는 모습으로 보는 시각이 많습니다."
            ),
            "caution": _caution(top.get("streakPriceChangePercent")),
            "card_big": f"{n}일 연속",
            "card_label": "하루도 안 쉬고 매수",
            "card_stat": f"사모펀드 연속매수 {n}일째",
        })

    # 2) 오늘 하루 유입액이 가장 큰 종목 (1번과 겹치면 다음으로) — "규모" 이야기
    if flow_rows:
        by_today = sorted(flow_rows, key=lambda r: r.get("netBuyValueKrw", 0), reverse=True)
        for r in by_today:
            if r["ticker"] in used_tickers:
                continue
            used_tickers.add(r["ticker"])
            inst_days = 0
            for c in combined_rows:
                if c.get("ticker") == r["ticker"]:
                    inst_days = c.get("institutionConsecutiveBuyDays", 0)
                    break
            amount = _fmt_eok(r["netBuyValueKrw"])
            rank_p = _rank_phrase(r.get("rank"), r.get("sampleDays"))
            facts = [f"오늘 순매수: {amount} — 오늘 사모펀드 매수 명단 1위"]
            if rank_p:
                facts.append(f"이 종목 기준으로 보면: {rank_p}")
            facts.append(f"사모 연속 순매수: {r['consecutiveBuyDays']}거래일째")
            if inst_days > 0:
                facts.append(f"기관(사모 제외)도: {inst_days}거래일 연속 순매수 중")
            facts += _flow_common_facts(r)
            body = "오늘 사모펀드 돈이 가장 많이 들어간 종목이에요."
            if inst_days > 0:
                body += (
                    " 게다가 기관도 같이 사고 있어요. 돈의 성격도, 판단하는 팀도 다른 두 큰손이 "
                    "같은 방향을 보고 있다는 점이 눈에 띕니다."
                )
            else:
                body += " 하루 규모가 크다는 건 그만큼 확신을 갖고 움직였다는 뜻으로 읽히기도 합니다."
            highlights.append({
                "kind": "today",
                "name": r["corpName"],
                "ticker": r["ticker"],
                "headline": f"{r['corpName']} — 오늘 하루에만 {amount}, 사모펀드 매수 1위",
                "summary": f"오늘 하루 {amount}, 사모펀드가 가장 많이 산 종목",
                "facts": facts,
                "body": body,
                "caution": _caution(r.get("streakPriceChangePercent")),
                "card_big": amount,
                "card_label": "오늘 하루 사모 매수 1위",
                "card_stat": f"오늘 하루 {amount} 유입",
            })
            break

    # 3) 사모+기관 동시 진입 중 가장 점수 높은 것 (겹치지 않는 종목) — "연합" 이야기
    for c in combined_rows:
        if c["ticker"] in used_tickers:
            continue
        pd_, idays = c.get("pefConsecutiveBuyDays", 0), c.get("institutionConsecutiveBuyDays", 0)
        if pd_ > 0 and idays > 0:
            used_tickers.add(c["ticker"])
            total = c.get("pefStreakTotalValueKrw", 0) + c.get("institutionStreakTotalValueKrw", 0)
            facts = [
                f"사모펀드: {pd_}거래일 연속 순매수 (누적 {_fmt_eok(c.get('pefStreakTotalValueKrw', 0))})",
                f"기관(사모 제외): {idays}거래일 연속 순매수 (누적 {_fmt_eok(c.get('institutionStreakTotalValueKrw', 0))})",
                f"두 큰손 합계: 약 {_fmt_eok(total)}",
            ]
            facts += _flow_common_facts(c)
            highlights.append({
                "kind": "combined",
                "name": c["corpName"],
                "ticker": c["ticker"],
                "headline": f"{c['corpName']} — 사모펀드와 기관, 두 큰손이 같이 산다",
                "summary": f"사모 {pd_}일 + 기관 {idays}일, 두 큰손이 동시에 순매수",
                "facts": facts,
                "body": (
                    "기관(연기금·보험·투신 등)과 사모펀드는 돈의 주인도, 판단하는 팀도 달라요. "
                    "서로 다른 두 곳이 같은 종목을 같은 시기에 사고 있다는 건, 한쪽만 살 때보다 "
                    "눈여겨볼 만한 장면입니다."
                ),
                "caution": _caution(c.get("streakPriceChangePercent")),
                "card_big": "사모+기관",
                "card_label": f"두 큰손 동시 매수 (사모 {pd_}일·기관 {idays}일)",
                "card_stat": "사모+기관 동시 진입",
            })
            break

    # 4) 최근 DART 5%룰 신규/변경 공시 중 가장 최신 것 — "지분을 늘린"
    # 것만 다룬다(pefNetBuyRatioPercent > 0). 이 값은 음수도 나올 수 있는데
    # (지분 처분/계약 해제 등), 그런 경우까지 "신규 확보"라고 쓰면 실제로는
    # 지분을 줄인 걸 늘렸다고 거꾸로 설명하는 오류가 난다(2026-09-29,
    # 가비아 -24.37%를 "신규 확보"로 잘못 쓴 사고로 발견).
    increase_rows = [r for r in activity_rows if (r.get("pefNetBuyRatioPercent") or 0) > 0]
    if increase_rows:
        recent = sorted(increase_rows, key=lambda r: r.get("latestReportDate", ""), reverse=True)[0]
        reporters = ", ".join(recent.get("pefReporters", []))
        reason = recent.get("latestReportReason", "대량보유")
        ratio = recent["pefNetBuyRatioPercent"]
        value_krw = recent.get("pefNetBuyValueKrw") or 0
        is_partial = recent.get("pefNetBuyValueIsPartial")
        facts = [
            f"신고한 곳: {reporters}",
            f"신고일: {recent.get('latestReportDate', '')}",
            f"지분: {ratio}%" + (f" (약 {_fmt_eok(value_krw)} 규모)" if value_krw and not is_partial else ""),
            f"신고 사유: {reason}",
        ]
        highlights.append({
            "kind": "dart",
            "name": recent["corpName"],
            "ticker": recent["stockCode"],
            "headline": f"{recent['corpName']} — 투자사가 지분 {ratio}%를 '공식 신고'했다",
            "summary": f"투자사가 지분 {ratio}% 보유를 금감원에 공식 신고",
            "facts": facts,
            "body": (
                "주식을 5% 넘게 가진 투자자는 5영업일 안에 금융감독원에 신고해야 해요(일명 '5%룰'). "
                "매일 사고파는 수급과 달리, '우리가 이만큼 갖고 있다'고 공식 문서로 밝힌 거라 "
                "무게가 다릅니다."
            ),
            "caution": (
                "주의할 점: 신고 사유를 꼭 같이 보세요. 상장·합병처럼 '원래 갖고 있던 지분'을 "
                "형식상 신고한 경우도 있어서, 새로 사들였다는 뜻이 아닐 수 있어요."
            ),
            "card_big": f"지분 {ratio}%",
            "card_label": "5%룰 대량보유 공식 신고",
            "card_stat": f"지분 {ratio}% 보유 신고",
        })

    return trade_date, highlights[:4]


def _title_hook(h: dict, date_md: str) -> str:
    kind = h.get("kind")
    if kind == "streak":
        n = h["card_big"].replace("일 연속", "")
        return f"사모펀드가 {n}일 동안 하루도 안 쉬고 산 종목, {h['name']} | {date_md} 큰손 수급"
    if kind == "today":
        return f"오늘 사모펀드가 가장 많이 산 종목은 {h['name']}({h['card_big']}) | {date_md} 큰손 수급"
    if kind == "combined":
        return f"사모펀드와 기관이 동시에 사는 종목, {h['name']} | {date_md} 큰손 수급"
    return f"{h['headline']} | {date_md} 큰손 수급"


def generate_post(trade_date: str, highlights: list[dict]) -> tuple[str, list[str], str, str]:
    """(제목, 본문 줄 리스트('' = 빈 줄), 태그문자열, 한글날짜) 반환.
    '▶'/'■'로 시작하는 줄은 굵게 넣는다(_lines_to_html)."""
    date_kr = trade_date
    date_md = trade_date
    try:
        d = dt.date.fromisoformat(trade_date)
        date_kr = f"{d.year}년 {d.month}월 {d.day}일"
        date_md = f"{d.month}/{d.day}"
    except (ValueError, TypeError):
        pass

    title = _title_hook(highlights[0], date_md) if highlights else f"{date_md} 사모펀드 큰손 수급"

    lines: list[str] = [
        "주식시장엔 '큰손'이 있어요. 하루에 수십억, 수백억을 움직이는 사모펀드 같은 곳이죠.",
        "그런데 이 큰손들의 장바구니가 매일 공개된다는 거, 알고 계셨나요?",
        "한국거래소는 장이 끝나면 누가 어떤 종목을 얼마나 사고팔았는지 발표해요. "
        f"오늘도 그 장바구니를 열어봤습니다. ({date_kr} 거래일 기준)",
        "",
        "■ 30초 요약",
    ]
    for i, h in enumerate(highlights):
        lines.append(f"{_CIRCLED[i]} {h['name']} — {h['summary']}")
    lines += [
        "",
        "■ 처음 오셨다면, 용어 3개만",
        "· 사모펀드: 소수의 큰 투자자 돈을 모아 굴리는 펀드 (이 글의 '큰손')",
        "· 순매수: 산 금액 − 판 금액. 플러스면 '판 것보다 더 많이 샀다'",
        "· 연속 순매수: '더 많이 산 날'이 하루도 안 끊기고 며칠째 이어졌는지",
        "",
    ]

    for i, h in enumerate(highlights):
        lines.append(f"▶ {_CIRCLED[i]} {h['headline']}")
        lines.append("[숫자로 보면]")
        lines += [f"· {f}" for f in h.get("facts", [])]
        lines.append("[왜 볼 만한가]")
        lines.append(h["body"])
        if h.get("caution"):
            lines.append(h["caution"])
        lines.append("")

    lines += [
        "■ 오늘의 한 줄",
        "하루 크게 사는 것보다 '매일 꾸준히 사는 것'이 더 많은 걸 말해줄 때가 있어요. "
        "다만 큰손도 틀릴 수 있다는 것, 그게 오늘의 두 번째 한 줄입니다.",
        "",
        "■ 꼭 알아두세요",
        "'큰손이 샀다 = 주가가 오른다'는 뜻이 아니에요. 이 글은 공개된 수급 데이터에서 흐름이 "
        "두드러진 사실을 정리한 것이고, 투자 권유가 아닌 정보 공유 목적입니다. 투자 판단은 각자의 몫이에요.",
        "출처: 한국거래소(KRX) 투자자별 매매동향, 금융감독원 DART 대량보유 공시",
        "",
        "전체 랭킹과 종목별 수급 흐름은 제가 직접 만든 사이트에서 매일 자동으로 업데이트돼요.",
        _SITE_URL,
        "",
        "여러분은 '3주 동안 매일 조금씩 사는 큰손'과 '하루에 크게 사는 큰손' 중 "
        "어느 쪽이 더 믿음이 가세요? 댓글로 알려주세요. 다음 거래일 장바구니도 열어볼게요!",
    ]

    tickers = [h["ticker"] for h in highlights]
    names = [h["name"] for h in highlights]
    tags = ",".join(["사모펀드", "큰손수급", "기관수급", "주식초보", "DART공시", *names[:4], *tickers[:4]])
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
        elif ln.startswith(("▶", "■")):
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
                    sidebar_close = frame.locator(".se-sidebar-close-button")
                    if sidebar_close.count() > 0 and sidebar_close.first.is_visible():
                        _click_center(page, sidebar_close.first)  # 업로드 후 열리는 라이브러리 패널
                        page.wait_for_timeout(400)
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
_DRAFT_JSON_PATH = _DATA_DIR / "blog_post_draft.json"


def save_draft_json(
    title: str, tags: str, card_path: Path | None, trade_date: str, date_kr: str, highlights: list[dict]
) -> Path:
    """save_draft()의 사람이 읽는 .txt와 별개로, 다른 프로세스(예: news 프로젝트의
    쇼츠 파이프라인)가 파싱 없이 바로 읽을 수 있는 구조화된 버전을 남긴다. 종목별
    headline/body는 이미 자연스러운 구어체 문장이라 내레이션에 그대로 재사용 가능."""
    payload = {
        "tradeDate": trade_date,
        "dateKr": date_kr,
        "title": title,
        "tags": tags,
        "cardImagePath": str(card_path) if card_path else None,
        "highlights": [
            {"name": h["name"], "ticker": h["ticker"], "headline": h["headline"], "body": h["body"]}
            for h in highlights
        ],
    }
    _DRAFT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DRAFT_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _DRAFT_JSON_PATH


def save_draft(title: str, lines: list[str], tags: str, card_path: Path | None, trade_date: str) -> Path:
    """발행은 안 하고(2026-09-24부터: 실제 업로드는 사람이 ChatGPT 등을 통해
    직접 한다 — 네이버 에디터 자동화가 발행 직전에 제목/본문 첫 줄이 서로
    섞이는 문제가 반복돼서, 브라우저 자동 발행은 당분간 포기하고 준비만
    한다) 그냥 사람이 바로 복사해서 쓸 수 있는 텍스트 파일로 저장한다."""
    body = "\n".join(lines)
    content = (
        f"# {title}\n\n"
        f"(기준 거래일: {trade_date} / 카테고리: {_CATEGORY} / 태그: {tags})\n"
        f"(▶ / ■ 로 시작하는 줄은 굵게 넣으면 좋습니다. 요약 카드 이미지는 "
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
    save_draft_json(title, tags, card_path, trade_date, date_kr, highlights)
    logger.info("네이버 블로그용 글 준비 완료 (%s 기준): %s", trade_date, draft_path)
    # 2026-09-29부터: 자동 발행(publish_to_naver)은 다시 호출하지 않는다 —
    # 사용자가 draft를 직접 확인 후 Codex(ChatGPT CLI)에게 올리게 하는 쪽을
    # 선택함. publish_to_naver()는 정상 동작 확인됐고 코드도 남아있으니
    # 필요해지면 여기서 다시 호출하면 된다.
