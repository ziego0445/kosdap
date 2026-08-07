import { LiveDashboard } from "@/components/live-dashboard";
import { FeatureBand } from "@/components/feature-band";
import { KakaoAdFit } from "@/components/kakao-adfit";
import { mockPredictions } from "@/lib/mock-data";
import { readLivePredictions } from "@/lib/live-predictions";

export default function Home() {
  // predictor(Python)가 매 실행마다 써주는 predictions.json이 있으면 그걸
  // 초기값으로 쓰고, 없으면(최초 빌드 등) mock으로 대체. 이후 최신값 반영은
  // LiveDashboard(클라이언트)가 주기적으로 fetch해서 담당.
  const live = readLivePredictions();
  const initial = live ?? mockPredictions;

  return (
    <div className="space-y-8">
      <div className="space-y-1.5">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-0.5 text-[11px] text-muted-foreground">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
          </span>
          30초마다 자동 갱신
        </div>
        <h1 className="text-3xl font-bold tracking-tight">
          오늘의{" "}
          <span className="bg-gradient-to-r from-[#3987e5] to-[#d55181] bg-clip-text text-transparent">
            추정가
          </span>
        </h1>
        <p className="text-xs text-muted-foreground">
          실시간 데이터를 분석해 산출한 주식 예측가입니다.
        </p>
      </div>

      <LiveDashboard initial={initial} intervalMs={30_000} />

      <div className="space-y-1.5">
        <p className="text-center text-[10px] text-muted-foreground/60">광고</p>
        <KakaoAdFit adUnit="DAN-tVZV5lnlMQBExDP1" width={300} height={250} />
      </div>

      <FeatureBand />
    </div>
  );
}
