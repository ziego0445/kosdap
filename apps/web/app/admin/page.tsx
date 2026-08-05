import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const sources = [
  { name: "SKHYB/USDT (Binance)", status: "ok", lastRun: "-" },
  { name: "SMSN/USD (Hyperliquid)", status: "ok", lastRun: "-" },
  { name: "Micron / Nvidia / SOXX (Yahoo Finance)", status: "ok", lastRun: "-" },
  { name: "USD/KRW, DXY, VIX", status: "ok", lastRun: "-" },
  { name: "KOSPI200 야간선물 (Eurex)", status: "ok", lastRun: "-" },
  { name: "공매도비율 / 수급 (일 1회)", status: "idle", lastRun: "-" },
];

export default function AdminPage() {
  // TODO: 버튼 액션을 Python predictor 서비스 트리거(API route -> HTTP/Job insert)로 연결
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">관리자</h1>
        <p className="text-sm text-muted-foreground">
          데이터 수집 상태 확인 및 수동 재계산. (초기 스캐폴딩 — 실제 트리거
          미연결)
        </p>
      </div>

      <div className="flex gap-2">
        <button className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted">
          데이터 새로고침
        </button>
        <button className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted">
          예측 다시계산
        </button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">데이터 소스 상태</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {sources.map((s) => (
              <li
                key={s.name}
                className="flex items-center justify-between py-2 text-sm"
              >
                <span>{s.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground">{s.lastRun}</span>
                  <Badge variant={s.status === "ok" ? "default" : "secondary"}>
                    {s.status === "ok" ? "정상" : "대기"}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">로그</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            아직 로그가 없습니다. predictor 서비스가 admin_logs 테이블에
            기록을 남기면 여기 표시됩니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
