"""Ridge 회귀로 적합한 종목별 계수.

적합 방법: 과거 종가(KRX, yfinance) vs 같은 날짜 프록시 변동률(토큰가·해외
상관종목·매크로)로 회귀. 표본이 작고(토큰 상장 이후 겹치는 기간뿐) 반도체
프록시끼리 상관관계가 높아 OLS 대신 ridge(L2)를 쓰고, alpha는 LOOCV로
선택했다. 재적합할 땐 `python scripts/fit_weights.py`를 그대로 다시 돌리고
출력값을 아래 FITTED_MODELS에 수동으로 옮겨 적으면 된다 (docs/PRD.md 4.2 참고).

적합 시점: 2026-08-06
표본: 종목별 40일 (2026-06-05 ~ 2026-08-04, 토큰 상장 이후 KRX·Bybit 겹치는
거래일 중 2026-07-31 극단치 1건 제외 — 아래 "주의" 참고)

검증 결과 (동일 40일 표본·동일 naive 기준선으로 나란히 비교, 단위 MAE%):

| 방식                          | SAMSUNG | SKHYNIX |
|-------------------------------|---------|---------|
| naive("어제와 동일")           | 5.28%   | 6.50%   |
| 기존 손으로 찍은 가중치         | 4.76%   | 5.50%   |
| ridge in-sample                | 4.65%   | 5.52%   |
| ridge LOOCV(진짜 out-of-sample)| 4.93%   | 5.88%   |

**솔직한 결론**: 손으로 찍은 가중치·ridge 둘 다 naive는 확실히 이기지만,
ridge가 손으로 찍은 가중치보다 낫다고는 말할 수 없다 (표본 40일에서
차이가 노이즈 범위 안). 그래도 ridge를 채택한 이유는 (1) 사람이 임의로
정한 숫자가 아니라 데이터로 재현 가능한 절차라 데이터가 쌓일수록
계속 재적합/개선이 가능하고, (2) LightGBM/XGBoost로 넘어갈 때 같은
데이터 파이프라인을 그대로 확장할 수 있기 때문. 현재 시점에는 "정확도
낮음, 검증 중" 상태로 취급해야 한다.

주의:
- 표본 기간에 KOSPI 사상 최대 등락(2026-07-28~31, -17%대 하락 후 +18%
  반등, 최태원 회장 장내매수·숏스퀴즈)이 있었음 — 이 날은 계수 왜곡을
  막기 위해 학습 표본에서 제외했다. 국내 수급/공매도 신호(flows.py, 아직
  스텁)가 이런 이벤트를 잡을 유일한 방법이라 다음 작업으로 예정됨.
- 표본이 40일뿐이라 통계적으로 얇다. 데이터가 쌓이는 대로(최소 3~6개월)
  재적합하고, 궁극적으로는 LightGBM/XGBoost로 교체할 것.
"""

from __future__ import annotations

FEATURES = [
    "token",
    "NVDA",
    "MU",
    "SOXX",
    "TSM",
    "SMH",
    "KRW=X",
    "DX-Y.NYB",
    "^TNX",
    "^VIX",
    "BTC-USD",
    "ETH-USD",
]

FITTED_MODELS: dict[str, dict] = {
    "SAMSUNG": {
        "intercept": -1.3517,
        "coefficients": {
            "token": 0.0734,
            "NVDA": 0.0140,
            "MU": 0.0838,
            "SOXX": 0.0564,
            "TSM": 0.0452,
            "SMH": 0.0448,
            "KRW=X": -0.0194,
            "DX-Y.NYB": -0.0002,
            "^TNX": -0.0100,
            "^VIX": -0.0559,
            "BTC-USD": -0.0192,
            "ETH-USD": -0.0203,
        },
        "resid_std": 5.476,
        "alpha": 3000,
        "n": 40,
    },
    "SKHYNIX": {
        "intercept": -1.3926,
        "coefficients": {
            "token": 0.1021,
            "NVDA": 0.0165,
            "MU": 0.1233,
            "SOXX": 0.0731,
            "TSM": 0.0320,
            "SMH": 0.0577,
            "KRW=X": -0.0199,
            "DX-Y.NYB": 0.0012,
            "^TNX": -0.0140,
            "^VIX": -0.0415,
            "BTC-USD": -0.0186,
            "ETH-USD": -0.0179,
        },
        "resid_std": 6.709,
        "alpha": 3000,
        "n": 40,
    },
}

FACTOR_LABELS: dict[str, str] = {
    "token": "토큰화 주식/선물(Bybit)",
    "NVDA": "Nvidia",
    "MU": "Micron",
    "SOXX": "SOXX",
    "TSM": "TSMC",
    "SMH": "SMH",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "DX-Y.NYB": "DXY",
    "KRW=X": "USD/KRW",
    "^TNX": "미국 10년물",
    "^VIX": "VIX",
}
