import fs from "node:fs";
import path from "node:path";
import { PredictionHistoryRow, StockSymbol } from "./types";

interface RawAccuracyRecord {
  symbol: StockSymbol;
  date: string;
  predicted_price: number;
  actual_price: number;
  error_percent: number;
}

/**
 * services/predictor/accuracy_log.py가 실제 예측 -> 실제 종가 확정 사이클마다
 * 쌓아주는 기록을 읽는다. predictions.json과 같은 브리지 방식 — Supabase
 * 연동 전까지는 이 파일이 유일한 실데이터 소스.
 */
export function readLiveAccuracyHistory(): PredictionHistoryRow[] | null {
  try {
    const filePath = path.join(process.cwd(), "public", "accuracy-history.json");
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw) as RawAccuracyRecord[];
    return parsed.map((r) => ({
      date: r.date,
      symbol: r.symbol,
      predicted: r.predicted_price,
      actual: r.actual_price,
      errorPercent: r.error_percent,
    }));
  } catch {
    return null;
  }
}
