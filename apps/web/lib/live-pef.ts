import fs from "node:fs";
import path from "node:path";
import { PefActivityRow } from "./types";

interface RawPefActivity {
  generatedAt: string;
  lookbackDays: number;
  rows: {
    corpCode: string;
    corpName: string;
    stockCode: string | null;
    pefNetBuyShares: number;
    pefReporters: string[];
    latestReportDate: string | null;
    latestReportReason: string | null;
  }[];
}

export interface LivePefActivity {
  generatedAt: string;
  lookbackDays: number;
  rows: PefActivityRow[];
}

/**
 * services/predictor/pef_tracker.py가 하루 1회 만드는 랭킹을 읽는다.
 * accuracy-history.json과 같은 브리지 방식(빌드 시점에 파일을 읽어 정적
 * HTML에 굽는다) — output: "export"라 클라이언트 fetch가 아니라
 * node:fs로 빌드 타임에 읽어야 한다.
 */
export function readLivePefActivity(): LivePefActivity | null {
  try {
    const filePath = path.join(process.cwd(), "public", "pef-activity.json");
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw) as RawPefActivity;
    return {
      generatedAt: parsed.generatedAt,
      lookbackDays: parsed.lookbackDays,
      rows: parsed.rows,
    };
  } catch {
    return null;
  }
}
