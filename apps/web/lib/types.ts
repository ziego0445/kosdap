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
  /** "코스피"/"코스닥"/"코넥스"/"기타". DART corp_cls 기반. */
  market: string | null;
  pefNetBuyShares: number;
  /** 보유비율 증감(%). 주식수는 주가가 싼 회사일수록 커 보이는 착시가
   * 있어 회사 간 비교엔 이 값(주가 무관, DART가 직접 주는 필드)이 더
   * 정직한 기준 — 랭킹 정렬도 이 값 기준. */
  pefNetBuyRatioPercent: number;
  /** 공시일 종가 × 주식수 증감의 근사치(원) — 실제 매수단가가 아니라
   * 추정치. DART API에 실제 취득단가가 없어서 이렇게 근사한다. */
  pefNetBuyValueKrw: number;
  /** true면 일부 날짜의 종가를 못 구해 위 금액이 과소산정됐을 수 있음. */
  pefNetBuyValueIsPartial: boolean;
  pefReporters: string[];
  latestReportDate: string | null;
  latestReportReason: string | null;
}

/**
 * KRX 투자자별(사모) 종목별 매매동향 기반 — DART 공시와 달리 개별 펀드명은
 * 안 나오지만(KRX 공식 "사모" 카테고리 집계치, 경영참여형 PEF+헤지펀드성
 * 사모펀드 합산) 전종목을 커버한다. services/predictor/pef_flow_tracker.py
 * 참고. "오늘 사모 순매수가 이 종목 자체 최근 1년 역사 중 몇 번째로
 * 강했는지" 순위 — 종목 간 비교가 아니라 그 종목 스스로의 평소 대비
 * 이례적인 정도.
 */
export interface PefFlowActivityRow {
  ticker: string;
  corpName: string;
  /** "코스피"/"코스닥". */
  market: string | null;
  netBuyValueKrw: number;
  /** 1이 최근 1년(대략 250거래일) 중 가장 강했던 날. */
  rank: number;
  sampleDays: number;
  /** 오늘까지 순매수가 끊기지 않고 이어진 날 수. 하루짜리 스파이크(노이즈
   * 가능성)와 며칠에 걸친 진짜 매집을 구분하는 데 씀 — 랭킹 1순위 기준. */
  consecutiveBuyDays: number;
  /** 위 연속 매수 기간 동안의 누적 순매수 금액(원). */
  streakTotalValueKrw: number;
  marketCapKrw: number | null;
  netBuyPercentOfCap: number | null;
}

/**
 * 사모 + 기관(사모 제외) 복합 수급 신호. "같은 날 동시에" 조건 없이 각자
 * 독립적으로 계산한 연속매수일을 단순 합산한 점수로 정렬한다 — 사모는
 * 어제, 기관은 오늘처럼 날짜가 어긋나도 잡힘. services/predictor/
 * pef_flow_tracker.py의 collect_combined_signal_activity 참고. 여러
 * 신호를 하나의 "매수의견"으로 바꾸지 않고 각 지표를 그대로 나란히
 * 보여준다 — 정렬에만 점수를 쓴다.
 */
export interface PefCombinedSignalRow {
  ticker: string;
  corpName: string;
  /** "코스피"/"코스닥". */
  market: string | null;
  pefNetBuyValueKrw: number;
  pefConsecutiveBuyDays: number;
  pefStreakTotalValueKrw: number;
  /** 오늘 사모가 순매도/보합이면(연속매수일=0) null. */
  pefRank: number | null;
  institutionNetBuyValueKrw: number;
  institutionConsecutiveBuyDays: number;
  institutionStreakTotalValueKrw: number;
  institutionRank: number | null;
  /** pefConsecutiveBuyDays + institutionConsecutiveBuyDays, 정렬 기준. */
  combinedScore: number;
  sampleDays: number;
}
