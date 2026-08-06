import { RefreshCw, Calculator, CheckCircle2, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// docs/PRD.md 3절 데이터 소스 (2026-08-06 실측 기준)
const sources = [
  { name: "SAMSUNGUSDT / SKHYNIXUSDT (Bybit 무기한선물)", status: "ok", note: "24/7" },
  { name: "SKHYB/USDT (Binance, 교차검증용)", status: "ok", note: "24/7" },
  { name: "Micron / Nvidia / TSMC / SOXX / SMH (Yahoo Finance)", status: "ok", note: "미국장 시간" },
  { name: "USD/KRW, DXY, VIX, 미국10년물, BTC/ETH", status: "ok", note: "10~15분" },
  { name: "외국인/기관 순매수 (네이버페이 증권)", status: "ok", note: "일 1회" },
  { name: "공매도비율", status: "idle", note: "미연동" },
  { name: "KRX 시간외 단일가", status: "idle", note: "미연동" },
] as const;

export default function AdminPage() {
  // TODO: 버튼 액션을 Python predictor 서비스 트리거(API route -> HTTP/Job insert)로 연결
  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">관리자 🛠️</h1>
        <p className="text-xs text-muted-foreground">
          데이터 수집 상태 확인 및 수동 재계산. (초기 스캐폴딩 — 실제 트리거
          미연결)
        </p>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="gap-1.5 rounded-full">
          <RefreshCw className="h-3.5 w-3.5" />
          데이터 새로고침
        </Button>
        <Button variant="outline" size="sm" className="gap-1.5 rounded-full">
          <Calculator className="h-3.5 w-3.5" />
          예측 다시계산
        </Button>
      </div>

      <Card size="sm">
        <CardHeader>
          <CardTitle className="text-sm">데이터 소스 상태</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-border/60">
            {sources.map((s) => (
              <li
                key={s.name}
                className="flex items-center justify-between py-2 text-xs"
              >
                <span>{s.name}</span>
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {s.note}
                  </span>
                  <Badge
                    variant={s.status === "ok" ? "default" : "secondary"}
                    className="gap-1 rounded-full text-[10px]"
                  >
                    {s.status === "ok" && <CheckCircle2 className="h-3 w-3" />}
                    {s.status === "ok" ? "정상" : "대기"}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardHeader>
          <CardTitle className="text-sm">로그</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            아직 로그가 없습니다. predictor 서비스가 admin_logs 테이블에
            기록을 남기면 여기 표시됩니다. 파이프라인 에러는 텔레그램으로도
            바로 알림이 갑니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
