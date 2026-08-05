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
        }
