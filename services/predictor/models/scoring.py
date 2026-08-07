"""예측 로직: 종목별 Ridge 회귀 계수 기반 선형 스코어링.

과거엔 손으로 찍은 가중합(weighted average)을 썼으나, 백테스트 결과 나이브
기준선("어제와 동일")보다도 오차가 컸다. 과거 데이터로 ridge 회귀를 적합해
LOOCV 기준 out-of-sample MAE가 naive보다 낮은 걸 확인한 계수로 교체함
(models/fitted_weights.py 참고, docs/PRD.md 4.2).

인터페이스(compute_prediction 반환 형태)는 유지해서 web 쪽 코드를 건드리지
않고 계산 로직만 교체할 수 있게 한다. 데이터가 더 쌓이면 이 모듈을
LightGBM/XGBoost로 다시 교체한다.
"""

from __future__ import annotations

import math

from collectors.tokenized import BYBIT_SYMBOLS
from models.fitted_weights import FACTOR_LABELS, FITTED_MODELS
from models.schema import InfluenceFactor, Prediction


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# 2026-08-06 실측 검증(scripts/verify_live.py)으로 확인한 사실: 정규장 중
# 급락/급등처럼 국내 수급성 이벤트가 터지면, 토큰가(Bybit)는 실제 KRX 가격
# 변동과 거의 1:1로 움직이는데(그날 삼성 토큰 -6.24% vs 실제가 -6.40%,
# SK하이닉스 토큰 -9.64% vs 실제가 -9.65%) 해외 프록시(NVDA/SOXX 등)는
# 평범한 범위(그날 평균 |변동률| 1.4%)라 이런 이벤트를 아예 못 잡는다.
# ridge 계수(token coef 0.08~0.11)는 "평범한 날" 기준으로 다소 작게 축소돼
# 있어서, 이런 날엔 점추정치가 낙폭/급등폭을 과소평가하게 된다.
#
# 그날 하루만 보고 계수(intercept)를 다시 맞추면 2026-07-31 극단치 때와
# 같은 실수(표본 40일에 극단치 하나 넣었다가 계수가 왜곡된 것)를 반복하게
# 되므로, 점추정치는 건드리지 않고 대신 "토큰가가 평소보다 많이 튀면
# 예측구간을 그만큼 넓히고 신뢰도를 낮추는" 방식으로 보정한다 — 방향은
# 맞히되(5회 검증에서 5/5), 크기에 대한 불확실성을 솔직하게 넓혀서 보여줌.
_NORMAL_TOKEN_MOVE_PERCENT = 2.0  # "평범한 날" 기준 토큰가 변동폭(%) 근사치
_MAX_VOLATILITY_MULTIPLIER = 4.0


def _volatility_multiplier(token_change_percent: float | None) -> float:
    if token_change_percent is None:
        return 1.0
    return min(_MAX_VOLATILITY_MULTIPLIER, max(1.0, abs(token_change_percent) / _NORMAL_TOKEN_MOVE_PERCENT))


def compute_prediction(
    symbol: str,
    current_price: float,
    token_change_percent: float | None,
    equity_changes: dict[str, float | None],
    macro_changes: dict[str, float | None],
) -> Prediction:
    model = FITTED_MODELS.get(symbol)
    if model is None:
        raise ValueError(f"'{symbol}'에 대한 적합된 계수가 없습니다 (models/fitted_weights.py 확인)")

    coefficients: dict[str, float] = model["coefficients"]
    intercept: float = model["intercept"]
    resid_std: float = model["resid_std"]

    inputs: dict[str, float | None] = {
        "token": token_change_percent,
        **equity_changes,
        **macro_changes,
    }

    # 결측치는 회귀 기여도를 0으로 취급한다 (해당 소스가 "평균적인 날"과
    # 같다고 가정하는 것과 동일 — 가중평균 정규화 방식과 달리 회귀 계수는
    # 존재하는 항목끼리 재분배하면 안 되므로 이렇게 처리).
    contributions = {
        k: coefficients[k] * v
        for k, v in inputs.items()
        if v is not None and k in coefficients
    }

    score_percent = intercept + sum(contributions.values())
    predicted_price = current_price * (1 + score_percent / 100)

    # "token" 라벨은 종목마다 실제로 다른 값(SAMSUNGUSDT vs SKHYNIXUSDT)을
    # 가리키는데 두 카드에 똑같은 문구가 뜨면 같은 값처럼 보여 헷갈리므로,
    # 실제 참조하는 Bybit 심볼을 라벨에 명시한다.
    labels = dict(FACTOR_LABELS)
    if symbol in BYBIT_SYMBOLS:
        labels["token"] = f"토큰화 주식/선물({BYBIT_SYMBOLS[symbol]})"

    factors = [
        InfluenceFactor(label=labels.get(k, k), contribution=round(c, 3))
        for k, c in sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
    ]

    # 토큰가가 평소보다 많이 튀면(=국내 수급성 이벤트로 실제 변동폭이 클
    # 가능성이 큼) 예측구간을 넓히고 확률/신뢰도의 불확실성을 키운다.
    vol_mult = _volatility_multiplier(token_change_percent)
    effective_std = resid_std * vol_mult

    # 확률/구간은 잔차가 정규분포를 따른다는 가정 하에 산출한다 (1차 근사치).
    probability_up = _normal_cdf(score_percent / effective_std) * 100
    # 표본(n=41 내외)이 작을수록 신뢰도를 낮게 표시 — resid_std가 클수록,
    # 표본이 적을수록 confidence가 낮아지는 단순 휴리스틱. 변동성 배율이
    # 1보다 크면(토큰가 급변) 추가로 깎는다.
    confidence = max(30.0, min(90.0, 100 - resid_std * 2 - max(0, 60 - model["n"]) * 0.5))
    confidence = max(20.0, confidence - (vol_mult - 1) * 15)
    range_low = predicted_price * (1 - effective_std / 100)
    range_high = predicted_price * (1 + effective_std / 100)

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
        sample_size_days=model["n"],
        is_low_sample=model["n"] < 200,
    )
