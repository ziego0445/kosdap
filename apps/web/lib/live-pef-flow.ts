import fs from "node:fs";
import path from "node:path";
import { PefFlowActivityRow } from "./types";

interface RawPefFlowActivity {
  generatedAt: string;
  tradeDate: string | null;
  historyTradingDaysApprox: number;
  rows: PefFlowActivityRow[];
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
    return JSON.parse(raw) as RawPefFlowActivity;
  } catch {
    return null;
  }
}
