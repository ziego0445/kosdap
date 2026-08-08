import fs from "node:fs";
import path from "node:path";
import { PefCombinedSignalRow } from "./types";

interface RawPefCombinedSignal {
  generatedAt: string;
  tradeDate: string | null;
  historyTradingDaysApprox: number;
  rows: PefCombinedSignalRow[];
}

export interface LivePefCombinedSignal {
  generatedAt: string;
  tradeDate: string | null;
  historyTradingDaysApprox: number;
  rows: PefCombinedSignalRow[];
}

/**
 * services/predictor/pef_flow_tracker.py의 export_combined_signal_activity가
 * 하루 1회 만드는 사모+기관 복합 신호를 읽는다. predictions.json 등과 같은
 * 빌드타임 브리지 방식.
 */
export function readLivePefCombinedSignal(): LivePefCombinedSignal | null {
  try {
    const filePath = path.join(process.cwd(), "public", "pef-combined-signal.json");
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as RawPefCombinedSignal;
  } catch {
    return null;
  }
}
