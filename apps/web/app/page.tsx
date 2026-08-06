import { StockCard } from "@/components/stock-card";
import { isSupabaseConfigured } from "@/lib/supabase";
import { mockPredictions } from "@/lib/mock-data";
import { readLivePredictions } from "@/lib/live-predictions";

export default function Home() {
  // TODO: Supabase 연동 후에는 predictions 테이블(최신 row)로 교체.
  // 현재는 services/predictor/main.py가 실행마다 써주는
  // public/predictions.json이 있으면 그걸 우선 쓰고, 없으면 mock으로 대체.
  const live = readLivePredictions();
  const predictions = live ?? mockPredictions;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">오늘의 추정가</h1>
        <p className="text-sm text-muted-foreground">
          시장 데이터를 계산해 산출한 추정치이며, 실시간 시세와 다를 수
          있습니다.
        </p>
        {!isSupabaseConfigured && (
          <p className="mt-2 text-xs text-amber-600">
            Supabase 미연동 — {live ? "predictor가 계산한 실제 값(JSON 스냅샷)을" : "예시(mock) 데이터를"} 보여주고 있습니다.
          </p>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {predictions.map((p) => (
          <StockCard key={p.symbol} data={p} />
        ))}
      </div>
    </div>
  );
}
