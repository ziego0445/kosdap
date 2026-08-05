"""초기 예측 로직: 수동 가중합(weighted score).

데이터가 충분히 쌓이면 이 모듈을 LightGBM/XGBoost 기반 모델로 교체한다
(docs/PRD.md 4.2). 인터페이스(compute_prediction 반환 형태)는 유지해서
web 쪽 코드를 건드리지 않고 계산 로직만 교체할 수 있게 한다.
"""

from __future__ import annotations

from models.schema import InfluenceFactor, Prediction

# 종목별 1차 신호(토큰가) + 2차 신호(해외 상관종목) 가중치.
# 정확한 값은 백테스트로 조정할 것 — 지금은 PRD 초안 값을 그대로 사용.
DEFAULT_WEIGHTS: dict[str, float] = {
    "token": 0.45,
    "NVDA": 0.15,
    "MU": 0.08,
    "SOXX": 0.08,
    "TSM": 0.04,
    "SMH": 0.04,
    "BTC-USD": 0.03,
    "ETH-USD": 0.03,
    "DX-Y.NYB": 0.03,
    "KRW=X": 0.03,
    "^TNX": 0.02,
    "^VIX": 0.02,
}

FACTOR_LABELS: dict[str, str] = {
    "token": "토큰화 주식/선물",
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


def compute_prediction(
    symbol: str,
    current_price: float,
    token_change_percent: float | None,
    equity_changes: dict[str, float | None],
    macro_changes: dict[str, float | None],
    weights: dict[str, float] | None = None,
) -> Prediction:
    weights = weights or DEFAULT_WEIGHTS
    inputs: dict[str, float | None] = {
        "token": token_change_percent,
        **equity_changes,
        **macro_changes,
    }

    # 결측치는 제외하고, 실제로 존재하는 항목의 가중치 합으로 정규화한다.
    available = {k: v for k, v in inputs.items() if v is not None and k in weights}
    weight_sum = sum(weights[k] for k in available) or 1.0

    factors = [
        InfluenceFactor(label=FACTOR_LABELS.get(k, k), contribution=round(v, 3))
        for k, v in sorted(
            available.items(), key=lambda kv: abs(weights[kv[0]] * kv[1]), reverse=True
        )
    ]

    score_percent = sum(weights[k] * v for k, v in available.items()) / weight_sum
    predicted_price = current_price * (1 + score_percent / 100)

    # 신뢰도/확률/구간은 1차 근사치. 데이터가 쌓이면 잔차 분포 기반으로 교체.
    confidence = min(95.0, 50 + len(available) * 4)
    probability_up = min(95.0, max(5.0, 50 + score_percent * 8))
    spread = abs(predicted_price) * 0.006  # ±0.6% 근사 구간
    range_low = predicted_price - spread
    range_high = predicted_price + spread

    return Prediction(
        symbol=symbol,
        current_price=current_price,
        predicted_price=round(predicted_price),
        change_percent=round(score_percent, 2),
        confidence=round(confidence, 1),
        probability_up=round(probability_up, 1),
        range_low=round(range_low),
        range_high=round(range_high),
        factors=factors,
    )
