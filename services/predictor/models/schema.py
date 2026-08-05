from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InfluenceFactor:
    label: str
    contribution: float  # signed, percent


@dataclass
class Prediction:
    symbol: str
    current_price: float
    predicted_price: float
    change_percent: float
    confidence: float
    probability_up: float
    range_low: float
    range_high: float
    factors: list[InfluenceFactor] = field(default_factory=list)
    # 백테스트 표본이 작아 검증 중인 단계인지 (docs/PRD.md 4.2) — 임계값은
    # 임의 기준: 200일(약 1년치 거래일) 미만이면 "낮은 표본"으로 취급.
    sample_size_days: int = 0
    is_low_sample: bool = True

    def to_row(self) -> dict:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "predicted_price": self.predicted_price,
            "change_percent": self.change_percent,
            "confidence": self.confidence,
            "probability_up": self.probability_up,
            "range_low": self.range_low,
            "range_high": self.range_high,
            "factors": [f.__dict__ for f in self.factors],
            "sample_size_days": self.sample_size_days,
            "is_low_sample": self.is_low_sample,
        }
