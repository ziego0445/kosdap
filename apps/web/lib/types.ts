export type StockSymbol = "SAMSUNG" | "SKHYNIX";

export interface InfluenceFactor {
  label: string;
  /** signed contribution, e.g. +4.2 or -0.6 (percent) */
  contribution: number;
}

export interface StockPrediction {
  symbol: StockSymbol;
  name: string;
  ticker: string;
  currentPrice: number;
  predictedPrice: number;
  changePercent: number;
  confidence: number; // 0-100
  probabilityUp: number; // 0-100
  rangeLow: number;
  rangeHigh: number;
  factors: InfluenceFactor[];
  recentAccuracy: number; // 0-100, trailing accuracy
  asOf: string; // ISO timestamp
  isWeekend: boolean;
  /** 백테스트 표본이 작아 정확도가 아직 검증 중인 단계인지 (docs/PRD.md 4.2) */
  isLowSample: boolean;
  sampleSizeDays: number;
}

export interface PredictionHistoryRow {
  date: string;
  symbol: StockSymbol;
  predicted: number;
  actual: number | null;
  errorPercent: number | null;
}
