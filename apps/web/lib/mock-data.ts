import { StockPrediction } from "./types";

/**
 * predictor(Python)가 predictions.json을 아직 못 만들었을 때(최초 빌드 등)
 * 쓰는 폴백. 2026-08-06 실제 파이프라인 실행 결과를 그대로 옮긴 것 —
 * 허구의 숫자는 아니지만 최신 데이터는 아니므로 fallback 용도로만 사용.
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
    isRealAccuracy: false,
    isWeekend: false,
    isLowSample: true,
    sampleSizeDays: 40,
    isEstimate: true,
    asOf: new Date().toISOString(),
    factors: [
      { label: "VIX", contribution: 0.234 },
      { label: "토큰화 주식/선물(SAMSUNGUSDT)", contribution: -0.141 },
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
    isRealAccuracy: false,
    isWeekend: false,
    isLowSample: true,
    sampleSizeDays: 40,
    isEstimate: true,
    asOf: new Date().toISOString(),
    factors: [
      { label: "토큰화 주식/선물(SKHYNIXUSDT)", contribution: -0.407 },
      { label: "VIX", contribution: 0.174 },
      { label: "SOXX", contribution: -0.155 },
      { label: "SMH", contribution: -0.06 },
      { label: "Nvidia", contribution: 0.057 },
    ],
  },
];
