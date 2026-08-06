"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * services/predictor/scheduler.py가 백그라운드에서 몇 분마다 predictions.json을
 * 새로 써주므로, 열려있는 페이지도 새로고침 없이 최신값을 반영하도록 주기적으로
 * router.refresh()(서버 컴포넌트만 재요청, 클라이언트 상태는 유지)를 호출한다.
 */
export function AutoRefresh({ intervalMs = 30_000 }: { intervalMs?: number }) {
  const router = useRouter();

  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);

  return null;
}
