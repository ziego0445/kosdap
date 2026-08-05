import { PredictionHistoryRow, StockPrediction } from "./types";

/**
 * Placeholder data shown until the Python predictor service is wired up to
 * Supabase. Replace calls to these with real Supabase queries once
 * `predictions` / `prediction_accuracy` tables have live rows.
 */
export const mockPredictions: StockPrediction[] = [
  {
    symbol: "SAMSUNG",
    name: "삼성전자",
    ticker: "005930",
    currentPrice: 82000,
    predictedPrice: 83763,
    changePercent: 2.15,
    confidence: 87,
    probabilityUp: 78,
    rangeLow: 82900,
    rangeHigh: 84500,
    recentAccuracy: 83,
    isWeekend: false,
    asOf: new Date().toISOString(),
    factors: [
      { label: "SMSN 토큰(Hyperliquid)", contribution: 1.6 },
      { label: "Nvidia", contribution: 4.2 },
      { label: "SOXX", contribution: 1.8 },
      { label: "DXY", contribution: -0.6 },
    ],
  },
  {
    symbol: "SKHYNIX",
    name: "SK하이닉스",
    ticker: "000660",
    currentPrice: 215000,
    predictedPrice: 219200,
    changePercent: 1.95,
    confidence: 90,
    probabilityUp: 81,
    rangeLow: 217500,
    rangeHigh: 221000,
    recentAccuracy: 85,
    isWeekend: false,
    asOf: new Date().toISOString(),
    factors: [
      { label: "SKHYB 토큰(Binance)", contribution: 2.3 },
      { label: "Nvidia", contribution: 4.2 },
      { label: "Micron", contribution: 1.1 },
      { label: "USD/KRW", contribution: -0.3 },
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
