import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { mockHistory } from "@/lib/mock-data";

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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">예측 기록</h1>
        <p className="text-sm text-muted-foreground">
          예측가 대비 실제가, 오차를 투명하게 공개합니다.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatBox label="최근 30일 정확도" value={`${accuracy30.toFixed(1)}%`} />
        <StatBox label="평균 오차(MAPE)" value={`${mape.toFixed(2)}%`} />
        <StatBox label="표본 수" value={`${rows.length}일`} />
        <StatBox label="상태" value="예시 데이터" />
      </div>

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
              <TableCell>{r.date}</TableCell>
              <TableCell>{symbolLabel(r.symbol)}</TableCell>
              <TableCell className="text-right">
                {r.predicted.toLocaleString("ko-KR")}
              </TableCell>
              <TableCell className="text-right">
                {r.actual?.toLocaleString("ko-KR") ?? "-"}
              </TableCell>
              <TableCell className="text-right">
                {r.errorPercent !== null ? `${r.errorPercent}%` : "-"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
