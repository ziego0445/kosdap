import { Activity, Percent, Database, Hourglass } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HistoryChart } from "@/components/history-chart";
import { SYMBOL_ACCENT } from "@/lib/brand";
import { StockSymbol } from "@/lib/types";
import { readLiveAccuracyHistory } from "@/lib/live-accuracy";

function symbolLabel(symbol: StockSymbol) {
  return symbol === "SAMSUNG" ? "삼성전자" : "SK하이닉스";
}

const STAT_ACCENTS = ["#3987e5", "#9085e9", "#d55181"];

export default function HistoryPage() {
  const rows = readLiveAccuracyHistory() ?? [];

  const header = (
    <div className="space-y-1">
      <h1 className="text-2xl font-bold tracking-tight">
        예측{" "}
        <span className="bg-gradient-to-r from-[#3987e5] to-[#d55181] bg-clip-text text-transparent">
          기록
        </span>
      </h1>
      <p className="text-xs text-muted-foreground">
        예측가 대비 실제가, 오차를 투명하게 공개합니다.
      </p>
    </div>
  );

  if (rows.length === 0) {
    return (
      <div className="space-y-5">
        {header}
        <Card size="sm">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <Hourglass className="h-8 w-8 text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-sm font-medium">아직 확정된 예측 기록이 없습니다</p>
              <p className="text-xs text-muted-foreground">
                장이 열려있을 때 낸 추정가가 다음 장마감 실제가와 대조되면
                여기에 자동으로 쌓입니다. 서비스를 막 시작해서 하루 이상의
                주기가 아직 안 지났어요 — 곧 채워집니다.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const errors = rows.map((r) => r.errorPercent).filter((e): e is number => e !== null);
  const mape = errors.reduce((sum, e) => sum + Math.abs(e), 0) / (errors.length || 1);
  const recent30 = errors.slice(-30);
  const accuracy30 =
    100 - recent30.reduce((sum, e) => sum + Math.abs(e), 0) / (recent30.length || 1);

  const stats = [
    { icon: Percent, label: "최근 정확도", value: `${accuracy30.toFixed(1)}%` },
    { icon: Activity, label: "평균 오차(MAPE)", value: `${mape.toFixed(2)}%` },
    { icon: Database, label: "표본 수", value: `${rows.length}건` },
  ];

  return (
    <div className="space-y-5">
      {header}

      <div className="grid grid-cols-3 gap-3">
        {stats.map((s, i) => (
          <StatBox
            key={s.label}
            icon={<s.icon className="h-3.5 w-3.5" style={{ color: STAT_ACCENTS[i] }} />}
            label={s.label}
            value={s.value}
          />
        ))}
      </div>

      <Card size="sm">
        <CardHeader>
          <CardTitle className="text-sm">예측가 vs 실제가</CardTitle>
        </CardHeader>
        <CardContent>
          <HistoryChart rows={rows} />
        </CardContent>
      </Card>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>날짜</TableHead>
            <TableHead>종목</TableHead>
            <TableHead className="text-right">예측가</TableHead>
            <TableHead className="text-right">실제가</TableHead>
            <TableHead className="text-right">오차</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...rows].reverse().map((r) => (
            <TableRow key={`${r.date}-${r.symbol}`}>
              <TableCell className="tabular-nums">{r.date}</TableCell>
              <TableCell>
                <span className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: SYMBOL_ACCENT[r.symbol].color }}
                  />
                  {symbolLabel(r.symbol)}
                </span>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {r.predicted.toLocaleString("ko-KR")}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {r.actual?.toLocaleString("ko-KR") ?? "-"}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {r.errorPercent !== null ? `${r.errorPercent}%` : "-"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function StatBox({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
      <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 text-base font-semibold tabular-nums">{value}</p>
    </div>
  );
}
