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

/**
 * DART 대량보유상황보고서(5%룰) 기반 — 최근 사모펀드/SPC로 추정되는
 * 보고자가 지분을 늘린 상장사 랭킹. services/predictor/pef_tracker.py 참고.
 * 취득단가 정보는 DART API에 없어서 포함하지 않음 — "얼마나 샀는지"만.
 */
export interface PefActivityRow {
  corpCode: string;
  corpName: string;
  stockCode: string | null;
  pefNetBuyShares: number;
  pefReporters: string[];
  latestReportDate: string | null;
  latestReportReason: string | null;
}
