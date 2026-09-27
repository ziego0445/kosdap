import fs from "node:fs";
import path from "node:path";
import { PefFlowActivityRow } from "./types";

interface RawPefFlowActivity {
  generatedAt: string;
  tradeDate: string | null;
  historyTradingDaysApprox: number;
  rows: (Omit<
    PefFlowActivityRow,
    | "consecutiveBuyDays"
    | "streakTotalValueKrw"
    | "market"
    | "closePrice"
    | "volumeRatio"
    | "streakPriceChangePercent"
    | "pefBuySharePercent"
  > & {
    // 필드 추가 전에 커밋된 데이터엔 없을 수 있어 optional로 —
    // 다음 수집 사이클에 자동으로 채워짐.
    consecutiveBuyDays?: number;
    streakTotalValueKrw?: number;
    market?: string | null;
    closePrice?: number | null;
    volumeRatio?: number | null;
    streakPriceChangePercent?: number | null;
    pefBuySharePercent?: number | null;
  })[];
}

export interface LivePefFlowActivity {
  generatedAt: string;
  tradeDate: string | null;
  historyTradingDaysApprox: number;
  rows: PefFlowActivityRow[];
}

/**
 * services/predictor/pef_flow_tracker.py가 하루 1회 만드는 이례치 랭킹을
 * 읽는다. predictions.json 등과 같은 빌드타임 브리지 방식.
 */
export function readLivePefFlowActivity(): LivePefFlowActivity | null {
  try {
    const filePath = path.join(process.cwd(), "public", "pef-flow-activity.json");
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw) as RawPefFlowActivity;
    return {
      ...parsed,
      rows: parsed.rows.map((r) => ({
        ...r,
        market: r.market ?? null,
        consecutiveBuyDays: r.consecutiveBuyDays ?? 0,
        streakTotalValueKrw: r.streakTotalValueKrw ?? 0,
        closePrice: r.closePrice ?? null,
        volumeRatio: r.volumeRatio ?? null,
        streakPriceChangePercent: r.streakPriceChangePercent ?? null,
        pefBuySharePercent: r.pefBuySharePercent ?? null,
      })),
    };
  } catch {
    return null;
  }
}
