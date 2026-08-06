import { LiveDashboard } from "@/components/live-dashboard";
import { isSupabaseConfigured } from "@/lib/supabase";
import { mockPredictions } from "@/lib/mock-data";
import { readLivePredictions } from "@/lib/live-predictions";

export default function Home() {
  // 빌드 시점(로컬 dev 서버 요청 시점, 또는 GitHub Actions 빌드 시점)의
  // predictions.json이 있으면 그걸 초기값으로 쓰고, 없으면 mock으로 대체.
  // 이후 최신값 반영은 LiveDashboard(클라이언트)가 주기적으로 fetch해서 담당.
  const live = readLivePredictions();
  const initial = live ?? mockPredictions;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">오늘의 추정가</h1>
        <p className="text-sm text-muted-foreground">
          시장 데이터를 계산해 산출한 추정치이며, 실시간 시세와 다를 수
          있습니다. (30초마다 자동 갱신)
        </p>
        {!isSupabaseConfigured && (
          <p className="mt-2 text-xs text-amber-600">
            Supabase 미연동 — {live ? "predictor가 계산한 실제 값(JSON 스냅샷)을" : "예시(mock) 데이터를"} 초기값으로 보여주고, 이후엔 주기적으로 predictions.json을 다시 받아옵니다.
          </p>
        )}
      </div>

      <LiveDashboard initial={initial} intervalMs={30_000} />
    </div>
  );
}
