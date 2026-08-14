"""Central config: env vars, symbols, and per-source collection intervals.

Each data source updates at a different real-world frequency (see docs/PRD.md
section 6), so the scheduler reads intervals from here instead of using one
blanket cron interval for everything.
"""

import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# 관리자 장애 알림용 (notify.py). 현재 코드에서 BINANCE_*는 미사용 —
# Bybit 공개 API만 쓰고 있어서 인증 키가 필요 없음. 필요해지면 연결할 것.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# 사모펀드(PEF) 지분공시 추적 탭용 — opendart.fss.or.kr에서 무료 발급받는
# DART Open API 인증키. KRX_ID/Open API 키와는 완전히 별개. 없으면
# pef_tracker.py가 조용히 건너뜀 (collectors/dart.py 참고).
DART_API_KEY = os.getenv("DART_API_KEY", "")

# Seconds between collection runs, per source category.
INTERVAL_TOKEN_SECONDS = int(os.getenv("INTERVAL_TOKEN_SECONDS", "300"))  # 24/7
INTERVAL_EQUITY_SECONDS = int(os.getenv("INTERVAL_EQUITY_SECONDS", "600"))  # US market hours only
INTERVAL_MACRO_SECONDS = int(os.getenv("INTERVAL_MACRO_SECONDS", "900"))
INTERVAL_FLOWS_SECONDS = int(os.getenv("INTERVAL_FLOWS_SECONDS", "86400"))  # once/day after KRX close

SYMBOLS = {
    "SAMSUNG": {
        "name": "삼성전자",
        "krx_ticker": "005930.KS",  # yfinance용
        "krx_code": "005930",  # 네이버 금융 등 국내 소스용 (접미사 없음)
    },
    "SKHYNIX": {
        "name": "SK하이닉스",
        "krx_ticker": "000660.KS",
        "krx_code": "000660",
    },
}
# 토큰화 주식/선물 심볼은 collectors/tokenized.BYBIT_SYMBOLS 참고 (Bybit로 통일,
# 2026-08-06 실측 검증 — Hyperliquid는 폐기, Binance SKHYB는 보조 소스)

# Secondary/explanatory proxies (yfinance tickers)
# ES=F/NQ=F(S&P500·나스닥 선물): 개별주(MU/NVDA 등)는 미국 정규장이 닫히면
# 다음 개장 전까지 전일 종가로 멈춰있지만(장외시간엔 무의미), 선물은 거의
# 24시간 계속 거래돼(실측 확인: 2026-08-14, 미 동부 19~21시대도 시간별
# 가격 갱신됨) KRX 장마감~다음 개장 사이 유일하게 "장외시간에도 살아있는"
# 해외 리스크 심리 신호가 된다. PRD 3.2엔 원래 있었는데 구현이 빠져있었음.
EQUITY_PROXIES = ["MU", "NVDA", "TSM", "SOXX", "SMH", "ES=F", "NQ=F"]
MACRO_PROXIES = ["KRW=X", "DX-Y.NYB", "^TNX", "^VIX", "BTC-USD", "ETH-USD"]
