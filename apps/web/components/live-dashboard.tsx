"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { StockCard } from "@/components/stock-card";
import { StockPrediction } from "@/lib/types";
import { BASE_PATH } from "@/lib/site-config";

/**
 * GitHub Pages는 정적 파일만 서빙해서 서버 쪽 fs 읽기(router.refresh())로는
 * 새 데이터를 못 받는다. 그래서 predictions.json을 브라우저가 직접
 * 주기적으로 fetch한다 — GitHub Actions가 몇 분마다 이 파일을 갱신·재배포
 * 하므로, 열려있는 탭도 폴링만 하면 새로고침 없이 최신값을 반영한다.
 * 캐시를 우회하기 위해 매번 쿼리스트링에 타임스탬프를 붙인다.
 */
export function LiveDashboard({
  initial,
  intervalMs = 30_000,
}: {
  initial: StockPrediction[];
  intervalMs?: number;
}) {
  const [predictions, setPredictions] = useState(initial);
  const [lastFetchFailed, setLastFetchFailed] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(`${BASE_PATH}/predictions.json?t=${Date.now()}`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = (await res.json()) as StockPrediction[];
        if (!cancelled && data.length > 0) {
          setPredictions(data);
          setLastFetchFailed(false);
          setLastUpdated(new Date());
        }
      } catch {
        if (!cancelled) setLastFetchFailed(true);
      }
    }

    const id = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <div className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-1.5">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/5">
            <RefreshCw className="h-3 w-3 text-muted-foreground" />
          </span>
          <div className="text-[11px] leading-tight">
            <p className="text-muted-foreground">마지막 업데이트</p>
            <p className="font-medium tabular-nums">
              {lastUpdated
                ? lastUpdated.toLocaleString("ko-KR", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false,
                  })
                : "대기 중"}
            </p>
          </div>
        </div>
      </div>

      {lastFetchFailed && (
        <p className="text-xs text-amber-400">
          최신 데이터를 가져오지 못했습니다 — 마지막으로 받은 값을 계속
          보여줍니다.
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {predictions.map((p) => (
          <StockCard key={p.symbol} data={p} />
        ))}
      </div>
    </div>
  );
}
