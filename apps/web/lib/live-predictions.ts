import fs from "node:fs";
import path from "node:path";
import { StockPrediction } from "./types";

/**
 * services/predictor/main.py가 매 실행마다 public/predictions.json에 써주는
 * 실제 계산 결과를 읽는다. Supabase 연동 전 임시 브리지 — Supabase가 붙으면
 * 이 함수 내부만 predictions 테이블 조회로 바꾸면 된다.
 */
export function readLivePredictions(): StockPrediction[] | null {
  try {
    const filePath = path.join(process.cwd(), "public", "predictions.json");
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf-8");
    const parsed = JSON.parse(raw) as StockPrediction[];
    return parsed.length > 0 ? parsed : null;
  } catch {
    return null;
  }
}
