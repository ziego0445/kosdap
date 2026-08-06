import { Activity, Percent, Database, FlaskConical } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mockHistory } from "@/lib/mock-data";
import { HistoryChart } from "@/components/history-chart";

function symbolLabel(symbol: string) {
  return symbol === "SAMSUNG" ? "삼성전자" : "SK하이닉스";
}

export default function HistoryPage() {
  // TODO: Supabase의 prediction_accuracy 테이블(최근 100일)로 교체.
  const rows = mockHistory;

  const withError = rows.filter((r) => r.errorPercent !== null);
  const mape =
    withError.reduce((sum, r) => sum + Math.abs(r.errorPercent ?? 0), 0) /
    (withError.length || 1);
  const accuracy30 =
    100 -
    withError
      .slice(0, 30)
      .reduce((sum, r) => sum + Math.abs(r.errorPercent ?? 0), 0) /
      (Math.min(30, withError.length) || 1);

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">예측 기록 📒</h1>
        <p className="text-xs text-muted-foreground">
          예측가 대비 실제가, 오차를 투명하게 공개합니다.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBox
          icon={<Percent className="h-3.5 w-3.5" />}
          label="최근 30일 정확도"
          value={`${accuracy30.toFixed(1)}%`}
        />
        <StatBox
          icon={<Activity className="h-3.5 w-3.5" />}
          label="평균 오차(MAPE)"
          value={`${mape.toFixed(2)}%`}
        />
        <StatBox
          icon={<Database className="h-3.5 w-3.5" />}
          label="표본 수"
          value={`${rows.length}일`}
        />
        <StatBox
          icon={<FlaskConical className="h-3.5 w-3.5" />}
          label="상태"
          value="예시 데이터"
        />
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
          {rows.map((r) => (
            <TableRow key={`${r.date}-${r.symbol}`}>
              <TableCell className="tabular-nums">{r.date}</TableCell>
              <TableCell>{symbolLabel(r.symbol)}</TableCell>
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
    <div className="rounded-xl border p-3">
      <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 text-base font-semibold tabular-nums">{value}</p>
    </div>
  );
}
