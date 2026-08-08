import { CheckCircle2, Clock, Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const sources = [
  { name: "삼성전자 · SK하이닉스 토큰화 선물 (Bybit)", status: "ok", note: "24/7" },
  { name: "장전 · 장후 시간외 단일가", status: "ok", note: "해당 시간대" },
  { name: "Micron · Nvidia · TSMC · SOXX · SMH", status: "ok", note: "미국장 시간" },
  { name: "USD/KRW, DXY, VIX, 미국 10년물, BTC/ETH", status: "ok", note: "10~15분" },
  { name: "외국인 · 기관 순매수", status: "ok", note: "일 1회" },
  { name: "공매도비율", status: "ok", note: "일 1회" },
] as const;

export default function AdminPage() {
  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          <span className="bg-gradient-to-r from-[#3987e5] to-[#d55181] bg-clip-text text-transparent">
            데이터 소스
          </span>
        </h1>
        <p className="text-xs text-muted-foreground">
          오늘 얼마니!?가 추정가 계산에 실제로 사용하는 데이터 출처와 갱신 주기입니다.
        </p>
      </div>

      <Card size="sm">
        <CardContent>
          <ul className="divide-y divide-white/5">
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
                    className={
                      s.status === "ok"
                        ? "gap-1 rounded-full bg-emerald-600/15 text-[10px] text-emerald-400 hover:bg-emerald-600/15"
                        : "gap-1 rounded-full text-[10px]"
                    }
                  >
                    {s.status === "ok" && <CheckCircle2 className="h-3 w-3" />}
                    {s.status === "ok" ? "연동됨" : "준비 중"}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card size="sm" className="border-white/5 bg-white/[0.02]">
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Bell className="h-3.5 w-3.5" />
            장애 알림
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            데이터 수집이나 계산에 문제가 생기면 운영자에게 즉시 알림이 갑니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
