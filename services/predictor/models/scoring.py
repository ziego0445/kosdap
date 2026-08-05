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

from models.fitted_weights import FACTOR_LABELS, FITTED_MODELS
from models.schema import InfluenceFactor, Prediction


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


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

    factors = [
        InfluenceFactor(label=FACTOR_LABELS.get(k, k), contribution=round(c, 3))
        for k, c in sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
    ]

    # 확률/구간은 잔차가 정규분포를 따른다는 가정 하에 산출한다 (1차 근사치).
    probability_up = _normal_cdf(score_percent / resid_std) * 100
    # 표본(n=41 내외)이 작을수록 신뢰도를 낮게 표시 — resid_std가 클수록,
    # 표본이 적을수록 confidence가 낮아지는 단순 휴리스틱.
    confidence = max(30.0, min(90.0, 100 - resid_std * 2 - max(0, 60 - model["n"]) * 0.5))
    range_low = predicted_price * (1 - resid_std / 100)
    range_high = predicted_price * (1 + resid_std / 100)

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
