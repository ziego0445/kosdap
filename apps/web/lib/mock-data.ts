import { PredictionHistoryRow, StockPrediction } from "./types";

/**
 * Placeholder data shown until the Python predictor service is wired up to
 * Supabase. Replace calls to these with real Supabase queries once
 * `predictions` / `prediction_accuracy` tables have live rows.
 *
 * 아래 값은 2026-08-06 실제 predictor 파이프라인(services/predictor/main.py)을
 * 라이브로 돌려서 나온 실제 출력을 그대로 옮긴 것 (mock이지만 허구의 숫자는
 * 아님). 정확도(recentAccuracy)는 같은 날 백테스트의 방향 적중률(direction
 * accuracy, 극단치 제외) 값을 사용 — docs/PRD.md 4.2 참고.
 */
export const mockPredictions: StockPrediction[] = [
  {
    symbol: "SAMSUNG",
    name: "삼성전자",
    ticker: "005930",
    currentPrice: 246000,
    predictedPrice: 242423,
    changePercent: -1.45,
    confidence: 79,
    probabilityUp: 39.5,
    rangeLow: 229148,
    rangeHigh: 255698,
    recentAccuracy: 63,
    isWeekend: false,
    isLowSample: true,
    sampleSizeDays: 40,
    asOf: new Date().toISOString(),
    factors: [
      { label: "VIX", contribution: 0.234 },
      { label: "토큰화 주식/선물(Bybit)", contribution: -0.141 },
      { label: "SOXX", contribution: -0.12 },
      { label: "Nvidia", contribution: 0.048 },
      { label: "SMH", contribution: -0.047 },
    ],
  },
  {
    symbol: "SKHYNIX",
    name: "SK하이닉스",
    ticker: "000660",
    currentPrice: 1668000,
    predictedPrice: 1637251,
    changePercent: -1.84,
    confidence: 76.6,
    probabilityUp: 39.2,
    rangeLow: 1527407,
    rangeHigh: 1747094,
    recentAccuracy: 71,
    isWeekend: false,
    isLowSample: true,
    sampleSizeDays: 40,
    asOf: new Date().toISOString(),
    factors: [
      { label: "토큰화 주식/선물(Bybit)", contribution: -0.407 },
      { label: "VIX", contribution: 0.174 },
      { label: "SOXX", contribution: -0.155 },
      { label: "SMH", contribution: -0.06 },
      { label: "Nvidia", contribution: 0.057 },
    ],
  },
];

export const mockHistory: PredictionHistoryRow[] = Array.from(
  { length: 14 },
  (_, i) => {
    const predicted = 82000 + Math.round(Math.sin(i) * 800 + i * 40);
    const actual = predicted + Math.round((Math.random() - 0.5) * 600);
    return {
      date: new Date(Date.now() - i * 86_400_000).toISOString().slice(0, 10),
      symbol: i % 2 === 0 ? "SAMSUNG" : "SKHYNIX",
      predicted,
      actual,
      errorPercent: Number((((actual - predicted) / predicted) * 100).toFixed(2)),
    };
  }
);
