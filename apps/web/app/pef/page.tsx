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
import { KakaoAdFit } from "@/components/kakao-adfit";
import { readLivePefActivity } from "@/lib/live-pef";
import { readLivePefFlowActivity } from "@/lib/live-pef-flow";

/** 억원 단위가 감이 잘 오니 그걸 우선으로, 너무 작으면 만원 단위로. */
function formatKrw(value: number, { approx = false }: { approx?: boolean } = {}) {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  const prefix = approx ? "약 " : "";
  if (abs >= 1_0000_0000) {
    return `${sign}${prefix}${(abs / 1_0000_0000).toFixed(1)}억원`;
  }
  if (abs >= 1_0000) {
    return `${sign}${prefix}${(abs / 1_0000).toFixed(0)}만원`;
  }
  if (abs === 0) return "0원";
  return `${sign}${prefix}${abs.toLocaleString("ko-KR")}원`;
}

function formatKrwApprox(value: number, isPartial: boolean): string {
  if (value === 0) return isPartial ? "가격 조회 실패" : "0원";
  const body = formatKrw(value, { approx: true });
  return isPartial ? `${body}+` : body;
}

export default function PefActivityPage() {
  const dartData = readLivePefActivity();
  const dartRows = dartData?.rows ?? [];

  const flowData = readLivePefFlowActivity();
  const flowRows = flowData?.rows ?? [];

  const header = (
    <div className="space-y-1">
      <h1 className="text-2xl font-bold tracking-tight">
        <span className="bg-gradient-to-r from-[#3987e5] to-[#d55181] bg-clip-text text-transparent">
          사모펀드 뭐샀니?
        </span>
      </h1>
      <p className="text-xs text-muted-foreground">
        KRX·DART 공개 데이터로 사모펀드 관련 수급을 두 가지 시각으로
        보여줍니다.
      </p>
    </div>
  );

  const ad = (
    <div className="space-y-1.5">
      <p className="text-center text-[10px] text-muted-foreground/60">광고</p>
      <KakaoAdFit adUnit="DAN-tVZV5lnlMQBExDP1" width={300} height={250} />
    </div>
  );

  const disclaimer = (
    <Card size="sm" className="border-white/5 bg-white/[0.02]">
      <CardContent className="flex gap-2 py-3 text-[11px] leading-relaxed text-muted-foreground">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <div className="space-y-2">
          <p>
            <span className="font-semibold text-foreground">수급 이례치</span>
            {": "}
            KRX 공식 투자자 분류 &quot;사모&quot; 카테고리(경영참여형
            PEF + 헤지펀드성 사모펀드 합산 집계치)의 종목별 순매수를 써서,
            &quot;오늘 수급이 이 종목 자체 최근 1년 역사 중 몇 번째로
            강했는지&quot;를 봅니다. 집계 데이터라 개별 펀드명은 알 수
            없고, 종목 간 비교가 아니라 그 종목 스스로의 평소 대비
            이례적인 정도라는 점에 유의하세요. 전 종목을 다 검사하면
            너무 오래 걸려 그날 순매수 상위 후보만 정밀 계산합니다.
          </p>
          <p>
            <span className="font-semibold text-foreground">공시 기반 랭킹</span>
            {": "}
            DART 대량보유상황보고서(5%룰)에서 사모펀드/SPC로 추정되는
            보고자가 지분을 늘린 상장사입니다. 보고자가 사모펀드인지는
            이름 패턴으로 추정한 것이라 완벽하지 않을 수 있고, 실제
            취득단가 정보가 없어 표시된 금액은 공시일 종가 기준
            근사치입니다.
          </p>
          <p>
            둘 다 매수/매도 추천이 아니라 공개 데이터 사실 나열입니다.
          </p>
        </div>
      </CardContent>
    </Card>
  );

  const hasAnyData = flowRows.length > 0 || dartRows.length > 0;

  if (!hasAnyData) {
    return (
      <div className="space-y-5">
        {header}
        {ad}
        <Card size="sm">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <Hourglass className="h-8 w-8 text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-sm font-medium">아직 데이터가 없습니다</p>
              <p className="text-xs text-muted-foreground">
                데이터 수집이 아직 안 됐거나, 조건에 맞는 종목이 없었습니다.
              </p>
            </div>
          </CardContent>
        </Card>
        {disclaimer}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {header}
      {ad}

      {flowRows.length > 0 && (
        <Card size="sm">
          <CardHeader>
            <CardTitle className="text-sm">
              사모 수급 이례치
              {flowData?.tradeDate && (
                <span className="ml-1.5 font-normal text-muted-foreground">
                  ({flowData.tradeDate} 기준, {flowRows.length}개 종목)
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-2 sm:px-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>종목</TableHead>
                  <TableHead className="text-right">순매수금액</TableHead>
                  <TableHead className="text-right">시총 대비</TableHead>
                  <TableHead className="text-right">최근 1년 순위</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {flowRows.map((r) => (
                  <TableRow key={r.ticker}>
                    <TableCell className="whitespace-normal">
                      <div className="font-medium">{r.corpName}</div>
                      <div className="text-[10px] text-muted-foreground">
                        {r.ticker}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-[#e66767]">
                      {formatKrw(r.netBuyValueKrw)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {r.netBuyPercentOfCap !== null ? `${r.netBuyPercentOfCap}%` : "-"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <span className="font-semibold">{r.rank}위</span>
                      <span className="text-[10px] text-muted-foreground">
                        {" "}
                        /{r.sampleDays}일
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {dartRows.length > 0 && (
        <Card size="sm">
          <CardHeader>
            <CardTitle className="text-sm">
              공시 기반 랭킹 ({dartRows.length}개사)
            </CardTitle>
          </CardHeader>
          <CardContent className="px-2 sm:px-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>회사</TableHead>
                  <TableHead className="text-right">규모(추정)</TableHead>
                  <TableHead>보고일</TableHead>
                  <TableHead>보고자</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dartRows.map((r) => (
                  <TableRow key={r.corpCode}>
                    <TableCell className="whitespace-normal">
                      <div className="font-medium">{r.corpName}</div>
                      {r.stockCode && (
                        <div className="text-[10px] text-muted-foreground">
                          {r.stockCode}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div
                        className={
                          r.pefNetBuyRatioPercent >= 0
                            ? "font-semibold text-[#e66767]"
                            : "font-semibold text-[#3987e5]"
                        }
                      >
                        {r.pefNetBuyRatioPercent >= 0 ? "+" : ""}
                        {r.pefNetBuyRatioPercent}%p
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {formatKrwApprox(r.pefNetBuyValueKrw, r.pefNetBuyValueIsPartial)}
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {r.pefNetBuyShares >= 0 ? "+" : ""}
                        {r.pefNetBuyShares.toLocaleString("ko-KR")}주
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal tabular-nums">
                      {r.latestReportDate ?? "-"}
                      {r.latestReportReason && (
                        <div className="mt-0.5 text-[10px] text-muted-foreground">
                          {r.latestReportReason}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="max-w-[160px] whitespace-normal text-xs text-muted-foreground">
                      {r.pefReporters.join(", ")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {disclaimer}
    </div>
  );
}
