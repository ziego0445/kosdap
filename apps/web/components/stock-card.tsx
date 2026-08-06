import { Radio, FlaskConical, TrendingDown, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StockPrediction } from "@/lib/types";
import { cn } from "@/lib/utils";
import { FactorChart } from "@/components/factor-chart";

function formatKrw(value: number) {
  return `${value.toLocaleString("ko-KR")}원`;
}

// dataviz 스킬로 검증된 diverging 색(#e34948 상승 / #2a78d6 하락, 다크모드
// #e66767 / #3987e5). kosdap은 다크 톤 고정이라 다크 값만 쓴다.
const UP = "text-[#e66767]";
const DOWN = "text-[#3987e5]";

export function StockCard({ data }: { data: StockPrediction }) {
  const isUp = data.changePercent >= 0;
  const directionClass = isUp ? UP : DOWN;

  return (
    <Card
      size="sm"
      className={cn(
        "w-full overflow-hidden border-t-2",
        isUp ? "border-t-[#e66767]" : "border-t-[#3987e5]"
      )}
    >
      <CardHeader className="flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-lg">{data.name}</CardTitle>
          <p className="text-xs text-muted-foreground">{data.ticker}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {!data.isEstimate && (
            <Badge className="gap-1 rounded-full bg-emerald-600 text-[10px] hover:bg-emerald-600">
              <Radio className="h-3 w-3" />
              실시간
            </Badge>
          )}
          {data.isWeekend && (
            <Badge variant="secondary" className="rounded-full text-[10px]">
              주말
            </Badge>
          )}
          {data.isEstimate && data.isLowSample && (
            <Badge
              variant="outline"
              className="gap-1 rounded-full border-amber-500 text-[10px] text-amber-400"
            >
              <FlaskConical className="h-3 w-3" />
              검증 중 · {data.sampleSizeDays}일
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs text-muted-foreground">
              {data.isEstimate ? "현재가" : "실시간가"}
            </p>
            <p className="text-xl font-semibold tabular-nums">
              {formatKrw(data.currentPrice)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">
              {data.isEstimate ? "추정가" : "전일 대비"}
            </p>
            {data.isEstimate && (
              <p className={cn("text-xl font-bold tabular-nums", directionClass)}>
                {formatKrw(data.predictedPrice)}
              </p>
            )}
            <p
              className={cn(
                "flex items-center justify-end gap-1 text-xs font-medium tabular-nums",
                directionClass,
                !data.isEstimate && "text-xl font-bold"
              )}
            >
              {isUp ? (
                <TrendingUp className="h-3.5 w-3.5" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5" />
              )}
              {Math.abs(data.changePercent)}%
            </p>
          </div>
        </div>

        {!data.isEstimate && (
          <p className="text-[11px] leading-snug text-muted-foreground">
            정규장 운영 중 — 실제 체결가입니다. 예측은 장외/주말에만
            계산돼요.
          </p>
        )}

        {data.isEstimate && (
          <>
            <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
              <div className="rounded-lg bg-muted/70 p-1.5">
                <p className="text-muted-foreground">상승확률</p>
                <p className="font-semibold tabular-nums">{data.probabilityUp}%</p>
              </div>
              <div className="rounded-lg bg-muted/70 p-1.5">
                <p className="text-muted-foreground">신뢰도</p>
                <p className="font-semibold tabular-nums">{data.confidence}%</p>
              </div>
              <div className="rounded-lg bg-muted/70 p-1.5">
                <p className="text-muted-foreground">예상 범위</p>
                <p className="font-semibold tabular-nums">
                  {(data.rangeLow / 1000).toFixed(1)}k~
                  {(data.rangeHigh / 1000).toFixed(1)}k
                </p>
              </div>
            </div>

            <Separator />

            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">
                영향요인
              </p>
              <FactorChart factors={data.factors} />
            </div>
          </>
        )}

        <Separator />

        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">최근 예측 정확도</span>
          <span className="font-semibold tabular-nums">{data.recentAccuracy}%</span>
        </div>
      </CardContent>
    </Card>
  );
}
