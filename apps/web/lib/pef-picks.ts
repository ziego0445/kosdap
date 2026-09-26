import { PefActivityRow, PefCombinedSignalRow, PefFlowActivityRow } from "./types";

export interface PefPick {
  rank: number;
  ticker: string;
  name: string;
  market: string | null;
  /** 짧은 한 줄 배지 문구 — 왜 뽑혔는지. */
  reason: string;
  /** 보조 설명(작은 글씨). */
  detail: string;
}

function fmtKrw(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_0000_0000) return `${sign}${(abs / 1_0000_0000).toFixed(1)}억`;
  if (abs >= 1_0000) return `${sign}${(abs / 1_0000).toFixed(0)}만`;
  return `${sign}${abs.toLocaleString("ko-KR")}원`;
}

/**
 * 사모펀드 단독 수급(flowRows) / 사모+기관 복합 신호(combinedRows) / DART
 * 5%룰 공시(dartRows) — 세 데이터 소스를 하나로 합쳐서, 그중 가장 눈에
 * 띄는 종목 최대 5개를 근거와 함께 골라낸다. 페이지 최상단 "종합 추천"
 * 카드용. services/predictor/pef_blog_post.py의 select_highlights()와
 * 같은 선정 방식(동일 로직 유지 목적)을 웹 쪽에도 그대로 옮겨왔다 —
 * 1) 사모펀드 단독 연속매수 최장 스트릭
 * 2) 오늘 하루 유입액 최대
 * 3) 사모+기관 동시 진입 중 점수 최고
 * 4) 기관 단독 연속매수 최장(사모 신호 없이 기관만 강하게 들어온 경우)
 * 5) 가장 최근 DART 5%룰 신규/변경 공시
 * 매수/매도 추천이 아니라 공개 데이터에서 흐름이 두드러진 종목을 정리한
 * 것 — 페이지 하단 안내문과 같은 톤 유지.
 */
export function buildTopPicks(
  flowRows: PefFlowActivityRow[],
  combinedRows: PefCombinedSignalRow[],
  dartRows: PefActivityRow[],
): PefPick[] {
  const picks: PefPick[] = [];
  const used = new Set<string>();

  // 1) 사모펀드 단독 연속매수 최장 스트릭
  if (flowRows.length > 0) {
    const top = [...flowRows].sort(
      (a, b) => b.consecutiveBuyDays - a.consecutiveBuyDays,
    )[0];
    if (top.consecutiveBuyDays > 0) {
      used.add(top.ticker);
      picks.push({
        rank: 0,
        ticker: top.ticker,
        name: top.corpName,
        market: top.market,
        reason: `사모펀드 연속매수 ${top.consecutiveBuyDays}일째`,
        detail: `오늘 ${fmtKrw(top.netBuyValueKrw)} · 누적 ${fmtKrw(top.streakTotalValueKrw)}`,
      });
    }
  }

  // 2) 오늘 하루 유입액 최대 (겹치면 다음 순위로)
  const byToday = [...flowRows].sort(
    (a, b) => b.netBuyValueKrw - a.netBuyValueKrw,
  );
  for (const r of byToday) {
    if (used.has(r.ticker)) continue;
    used.add(r.ticker);
    picks.push({
      rank: 0,
      ticker: r.ticker,
      name: r.corpName,
      market: r.market,
      reason: `오늘 하루 ${fmtKrw(r.netBuyValueKrw)} 유입`,
      detail: `연속 ${r.consecutiveBuyDays}일${
        r.netBuyPercentOfCap !== null ? ` · 시총대비 ${r.netBuyPercentOfCap}%` : ""
      }`,
    });
    break;
  }

  // 3) 사모+기관 동시 진입 중 점수 최고
  for (const c of combinedRows) {
    if (used.has(c.ticker)) continue;
    if (c.pefConsecutiveBuyDays > 0 && c.institutionConsecutiveBuyDays > 0) {
      used.add(c.ticker);
      picks.push({
        rank: 0,
        ticker: c.ticker,
        name: c.corpName,
        market: c.market,
        reason: "사모+기관 동시 진입",
        detail: `사모 ${c.pefConsecutiveBuyDays}일 · 기관 ${c.institutionConsecutiveBuyDays}일 (점수 ${c.combinedScore})`,
      });
      break;
    }
  }

  // 4) 기관 단독 연속매수 최장 (사모 신호 없이 기관만 강한 경우)
  const instOnly = [...combinedRows]
    .filter((c) => !used.has(c.ticker) && c.institutionConsecutiveBuyDays > 0)
    .sort((a, b) => b.institutionConsecutiveBuyDays - a.institutionConsecutiveBuyDays);
  if (instOnly.length > 0) {
    const r = instOnly[0];
    used.add(r.ticker);
    picks.push({
      rank: 0,
      ticker: r.ticker,
      name: r.corpName,
      market: r.market,
      reason: `기관 연속매수 ${r.institutionConsecutiveBuyDays}일째`,
      detail: `누적 ${fmtKrw(r.institutionStreakTotalValueKrw)}`,
    });
  }

  // 5) 가장 최근 DART 5%룰 신규/변경 공시
  const sortedDart = [...dartRows]
    .filter((d) => !used.has(d.stockCode ?? d.corpCode))
    .sort((a, b) => (b.latestReportDate ?? "").localeCompare(a.latestReportDate ?? ""));
  if (sortedDart.length > 0) {
    const d = sortedDart[0];
    used.add(d.stockCode ?? d.corpCode);
    picks.push({
      rank: 0,
      ticker: d.stockCode ?? d.corpCode,
      name: d.corpName,
      market: d.market,
      reason: `${d.latestReportReason ?? "대량보유"}로 지분 ${d.pefNetBuyRatioPercent}% 확보`,
      detail: `${d.latestReportDate ?? ""} 공시 · ${d.pefReporters.slice(0, 2).join(", ")}`,
    });
  }

  return picks.slice(0, 5).map((p, i) => ({ ...p, rank: i + 1 }));
}
