import { Hourglass, Info } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { readLivePefActivity } from "@/lib/live-pef";

export default function PefActivityPage() {
  const data = readLivePefActivity();
  const rows = data?.rows ?? [];

  const header = (
    <div className="space-y-1">
      <h1 className="text-2xl font-bold tracking-tight">
        <span className="bg-gradient-to-r from-[#3987e5] to-[#d55181] bg-clip-text text-transparent">
          사모펀드 뭐샀니?
        </span>
      </h1>
      <p className="text-xs text-muted-foreground">
        DART 대량보유상황보고서(5%룰)에서 사모펀드/SPC로 추정되는 보고자가
        최근 {data?.lookbackDays ?? 30}일간 지분을 늘린 상장사입니다.
      </p>
    </div>
  );

  const disclaimer = (
    <Card size="sm" className="border-white/5 bg-white/[0.02]">
      <CardContent className="flex gap-2 py-3 text-[11px] leading-relaxed text-muted-foreground">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <p>
          이 목록은 매수/매도 추천이 아니라 공시 사실 나열입니다. 보고자가
          사모펀드인지는 이름 패턴(&quot;사모투자합자회사&quot; 등)으로
          추정한 것이라 완벽하지 않을 수 있습니다. DART API에 취득단가
          정보가 없어 &quot;평단가 대비 현재가&quot; 같은 가격 비교는
          제공하지 않습니다 — 정확히 계산할 수 없는 값은 추정해서 보여주지
          않는다는 원칙을 여기서도 지킵니다.
        </p>
      </CardContent>
    </Card>
  );

  if (rows.length === 0) {
    return (
      <div className="space-y-5">
        {header}
        {disclaimer}
        <Card size="sm">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <Hourglass className="h-8 w-8 text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-sm font-medium">아직 데이터가 없습니다</p>
              <p className="text-xs text-muted-foreground">
                최근 {data?.lookbackDays ?? 30}일간 사모펀드로 추정되는
                보고자의 지분 변동 공시가 없었거나, 데이터 수집이 아직
                안 됐습니다.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {header}
      {disclaimer}

      <Card size="sm">
        <CardHeader>
          <CardTitle className="text-sm">
            최근 순매수 상위 ({rows.length}개사)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>회사</TableHead>
                <TableHead>보고자(사모펀드 추정)</TableHead>
                <TableHead className="text-right">최근 순매수(주)</TableHead>
                <TableHead>최근 보고일</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.corpCode}>
                  <TableCell>
                    <div className="font-medium">{r.corpName}</div>
                    {r.stockCode && (
                      <div className="text-[10px] text-muted-foreground">
                        {r.stockCode}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="max-w-[220px] text-xs text-muted-foreground">
                    {r.pefReporters.join(", ")}
                  </TableCell>
                  <TableCell
                    className={`text-right tabular-nums ${
                      r.pefNetBuyShares >= 0 ? "text-[#e66767]" : "text-[#3987e5]"
                    }`}
                  >
                    {r.pefNetBuyShares >= 0 ? "+" : ""}
                    {r.pefNetBuyShares.toLocaleString("ko-KR")}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.latestReportDate ?? "-"}
                    {r.latestReportReason && (
                      <span className="ml-1 text-[10px] text-muted-foreground">
                        ({r.latestReportReason})
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
