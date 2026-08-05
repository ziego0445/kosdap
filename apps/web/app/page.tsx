import { StockCard } from "@/components/stock-card";
import { isSupabaseConfigured } from "@/lib/supabase";
import { mockPredictions } from "@/lib/mock-data";

export default function Home() {
  // TODO: Supabase의 predictions 테이블(최신 row)로 교체.
  // predictor(Python) 서비스가 아직 데이터를 채우기 전까지는 mock 데이터 표시.
  const predictions = mockPredictions;

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
            Supabase 환경변수가 설정되지 않아 예시(mock) 데이터를 보여주고
            있습니다. .env.local을 설정하면 실데이터로 전환됩니다.
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
