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
  /** 이미 주가가 많이 오른 경우 등 주의 문구. */
  caution: string | null;
}

/** 거래량이 평소의 이 배수 이상이면 "급증"으로 본다. */
const VOLUME_SURGE_RATIO = 2;
/** 연속매수 기간 주가 상승이 이 % 이하면 "아직 조용한" 매집으로 본다. */
const QUIET_MAX_CHANGE = 5;
/** 연속매수 기간 주가가 이 % 이상 올랐으면 "이미 반영" 주의 표시. */
const CAUTION_CHANGE = 20;

function fmtKrw(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_0000_0000) return `${sign}${(abs / 1_0000_0000).toFixed(1)}억`;
  if (abs >= 1_0000) return `${sign}${(abs / 1_0000).toFixed(0)}만`;
  return `${sign}${abs.toLocaleString("ko-KR")}원`;
}

/** 받침 없거나 ㄹ받침이면 "로", 그 외 받침이면 "으로". */
function withRo(word: string): string {
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  if (code < 0 || code > 11171) return `${word}로`;
  const jong = code % 28;
  return `${word}${jong === 0 || jong === 8 ? "로" : "으로"}`;
}

function fmtPct(v: number): string {
  return `${v > 0 ? "+" : ""}${v}%`;
}

interface PriceVolume {
  volumeRatio: number | null;
  streakPriceChangePercent: number | null;
  pefBuySharePercent: number | null;
}

function pvParts(r: PriceVolume): string[] {
  const parts: string[] = [];
  if (r.streakPriceChangePercent !== null)
    parts.push(`매수 기간 주가 ${fmtPct(r.streakPriceChangePercent)}`);
  if (r.volumeRatio !== null) parts.push(`거래량 평소 ${r.volumeRatio}배`);
  if (r.pefBuySharePercent !== null)
    parts.push(`오늘 거래의 ${r.pefBuySharePercent}% 사모 매수`);
  return parts;
}

function caution(r: PriceVolume): string | null {
  const c = r.streakPriceChangePercent;
  return c !== null && c >= CAUTION_CHANGE ? `이미 ${fmtPct(c)} 올라 있음` : null;
}

function joinDetail(...parts: (string | null | undefined | false)[]): string {
  return parts.filter(Boolean).join(" · ");
}

/**
 * 사모펀드 단독 수급(flowRows) / 사모+기관 복합 신호(combinedRows) / DART
 * 5%룰 공시(dartRows) + 시세(종가·거래량) 지표를 합쳐 눈에 띄는 종목을
 * 우선순위대로 최대 5개 고른다. 한 종목은 한 번만.
 * 1) 사모펀드 연속매수 최장
 * 2) 거래량 급증 + 사모/기관 매수 동반
 * 3) 조용한 매집 — 며칠째 사는데 주가는 아직 거의 안 오름
 * 4) 사모+기관 동시 진입
 * 5) 최근 DART 5%룰 공시
 * (자리가 남으면) 오늘 최대 유입, 기관 단독 연속매수
 * 거래량·기간 주가 지표는 시세 스냅샷이 쌓여야 생겨서, 초기엔 2·3번이
 * 비고 나머지로 채워진다.
 */
export function buildTopPicks(
  flowRows: PefFlowActivityRow[],
  combinedRows: PefCombinedSignalRow[],
  dartRows: PefActivityRow[],
): PefPick[] {
  const picks: PefPick[] = [];
  const used = new Set<string>();
  const add = (p: Omit<PefPick, "rank">) => {
    if (used.has(p.ticker)) return false;
    used.add(p.ticker);
    picks.push({ ...p, rank: 0 });
    return true;
  };

  // 1) 사모펀드 연속매수 최장
  const byStreak = [...flowRows].sort((a, b) => b.consecutiveBuyDays - a.consecutiveBuyDays);
  const top = byStreak[0];
  if (top && top.consecutiveBuyDays > 0) {
    add({
      ticker: top.ticker,
      name: top.corpName,
      market: top.market,
      reason: `사모펀드 연속매수 ${top.consecutiveBuyDays}일째`,
      detail: joinDetail(
        `누적 ${fmtKrw(top.streakTotalValueKrw)}`,
        ...pvParts(top),
      ),
      caution: caution(top),
    });
  }

  // 2) 거래량 급증 + 매수 동반 (사모 단독 표 + 복합 표 통틀어 배수 최대)
  type Surge = { ticker: string; name: string; market: string | null; ratio: number; buyDays: number; who: string; pv: PriceVolume };
  const surges: Surge[] = [
    ...flowRows
      .filter((r) => r.volumeRatio !== null && r.volumeRatio >= VOLUME_SURGE_RATIO && r.consecutiveBuyDays > 0)
      .map((r) => ({ ticker: r.ticker, name: r.corpName, market: r.market, ratio: r.volumeRatio!, buyDays: r.consecutiveBuyDays, who: "사모", pv: r })),
    ...combinedRows
      .filter((c) => c.volumeRatio !== null && c.volumeRatio >= VOLUME_SURGE_RATIO && (c.pefConsecutiveBuyDays > 0 || c.institutionConsecutiveBuyDays > 0))
      .map((c) => {
        const pefLead = c.pefConsecutiveBuyDays >= c.institutionConsecutiveBuyDays;
        return {
          ticker: c.ticker, name: c.corpName, market: c.market, ratio: c.volumeRatio!,
          buyDays: pefLead ? c.pefConsecutiveBuyDays : c.institutionConsecutiveBuyDays,
          who: pefLead ? "사모" : "기관", pv: c,
        };
      }),
  ].sort((a, b) => b.ratio - a.ratio);
  for (const s of surges) {
    if (add({
      ticker: s.ticker,
      name: s.name,
      market: s.market,
      reason: `거래량 평소 ${s.ratio}배 급증 + ${s.who} ${s.buyDays}일 연속매수`,
      detail: joinDetail(...pvParts({ ...s.pv, volumeRatio: null })),
      caution: caution(s.pv),
    })) break;
  }

  // 3) 조용한 매집 — 3일 이상 연속매수인데 그 기간 주가는 거의 제자리
  const quiet = flowRows
    .filter(
      (r) =>
        r.consecutiveBuyDays >= 3 &&
        r.streakPriceChangePercent !== null &&
        r.streakPriceChangePercent <= QUIET_MAX_CHANGE,
    )
    .sort((a, b) => b.streakTotalValueKrw - a.streakTotalValueKrw);
  for (const r of quiet) {
    if (add({
      ticker: r.ticker,
      name: r.corpName,
      market: r.market,
      reason: `조용한 매집 — ${r.consecutiveBuyDays}일째 사는데 주가 ${fmtPct(r.streakPriceChangePercent!)}`,
      detail: joinDetail(`누적 ${fmtKrw(r.streakTotalValueKrw)}`, ...pvParts({ ...r, streakPriceChangePercent: null })),
      caution: null,
    })) break;
  }

  // 4) 사모+기관 동시 진입 (combinedRows는 점수순 정렬돼 있음)
  for (const c of combinedRows) {
    if (c.pefConsecutiveBuyDays > 0 && c.institutionConsecutiveBuyDays > 0) {
      if (add({
        ticker: c.ticker,
        name: c.corpName,
        market: c.market,
        reason: "사모+기관 동시 진입",
        detail: joinDetail(
          `사모 ${c.pefConsecutiveBuyDays}일 · 기관 ${c.institutionConsecutiveBuyDays}일 (점수 ${c.combinedScore})`,
          ...pvParts(c),
        ),
        caution: caution(c),
      })) break;
    }
  }

  // 5) 가장 최근 DART 5%룰 신규/변경 공시
  const sortedDart = [...dartRows].sort((a, b) =>
    (b.latestReportDate ?? "").localeCompare(a.latestReportDate ?? ""),
  );
  for (const d of sortedDart) {
    if (add({
      ticker: d.stockCode ?? d.corpCode,
      name: d.corpName,
      market: d.market,
      reason: `${withRo(d.latestReportReason ?? "대량보유")} 지분 ${d.pefNetBuyRatioPercent}% 확보`,
      detail: `${d.latestReportDate ?? ""} 공시 · ${d.pefReporters.slice(0, 2).join(", ")}`,
      caution: null,
    })) break;
  }

  // 자리가 남으면: 오늘 최대 유입 → 기관 단독 연속매수
  if (picks.length < 5) {
    const byToday = [...flowRows].sort((a, b) => b.netBuyValueKrw - a.netBuyValueKrw);
    for (const r of byToday) {
      if (add({
        ticker: r.ticker,
        name: r.corpName,
        market: r.market,
        reason: `오늘 하루 ${fmtKrw(r.netBuyValueKrw)} 유입`,
        detail: joinDetail(
          `연속 ${r.consecutiveBuyDays}일`,
          r.netBuyPercentOfCap !== null && `시총대비 ${r.netBuyPercentOfCap}%`,
          ...pvParts(r),
        ),
        caution: caution(r),
      })) break;
    }
  }
  if (picks.length < 5) {
    const instOnly = [...combinedRows]
      .filter((c) => c.institutionConsecutiveBuyDays > 0)
      .sort((a, b) => b.institutionConsecutiveBuyDays - a.institutionConsecutiveBuyDays);
    for (const r of instOnly) {
      if (add({
        ticker: r.ticker,
        name: r.corpName,
        market: r.market,
        reason: `기관 연속매수 ${r.institutionConsecutiveBuyDays}일째`,
        detail: joinDetail(`누적 ${fmtKrw(r.institutionStreakTotalValueKrw)}`, ...pvParts(r)),
        caution: caution(r),
      })) break;
    }
  }

  return picks.slice(0, 5).map((p, i) => ({ ...p, rank: i + 1 }));
}
