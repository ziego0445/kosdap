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
  /** true면 실제 기록(accuracy-history.json)으로 계산된 값, false면 아직
   * 실기록이 부족해서 초기 백테스트 추정치를 대신 보여주는 것. */
  isRealAccuracy: boolean;
  asOf: string; // ISO timestamp
  isWeekend: boolean;
  /** 백테스트 표본이 작아 정확도가 아직 검증 중인 단계인지 (docs/PRD.md 4.2) */
  isLowSample: boolean;
  sampleSizeDays: number;
  /**
   * false면 currentPrice가 실제 체결가(정규장 운영 중)라 예측이 필요 없는
   * 상태 — predictedPrice/range/factors는 참고용이 아니라 currentPrice와
   * 동일하게 채워져 있음. true면 장외/휴장이라 진짜 추정치.
   */
  isEstimate: boolean;
}

export interface PredictionHistoryRow {
  date: string;
  symbol: StockSymbol;
  predicted: number;
  actual: number | null;
  errorPercent: number | null;
}
