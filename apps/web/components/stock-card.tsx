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
import { FactorChart } from "@/components/factor-chart";
import { SYMBOL_ACCENT } from "@/lib/brand";

function formatKrw(value: number) {
  return `${value.toLocaleString("ko-KR")}원`;
}

export function StockCard({ data }: { data: StockPrediction }) {
  const isUp = data.changePercent >= 0;
  const accent = SYMBOL_ACCENT[data.symbol];

  return (
    <Card
      size="sm"
      className="relative w-full overflow-hidden"
      style={{ boxShadow: `0 0 0 1px rgba(${accent.rgb}, 0.18)` }}
    >
      {/* 브랜드 글로우 — 카드 우상단에 은은하게 깔리는 액센트 색 (종목 정체성,
          상승/하락 방향과는 무관 — 방향은 화살표 아이콘/부호로 전달) */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full blur-3xl"
        style={{ backgroundColor: `rgba(${accent.rgb}, 0.22)` }}
      />

      <CardHeader className="relative flex flex-row items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
            style={{ backgroundColor: accent.color }}
          >
            {accent.label}
          </div>
          <div>
            <CardTitle className="text-lg">{data.name}</CardTitle>
            <p className="text-xs text-muted-foreground">{data.ticker}</p>
          </div>
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

      <CardContent className="relative space-y-3">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs text-muted-foreground">
              {data.isEstimate ? "현재가" : "실시간가"}
            </p>
            <p className="text-2xl font-bold tabular-nums">
              {formatKrw(data.currentPrice)}
            </p>
          </div>
          <div className="text-right">
            {data.isEstimate && (
              <>
                <p className="text-xs text-muted-foreground">추정가</p>
                <p className="text-lg font-semibold tabular-nums" style={{ color: accent.color }}>
                  {formatKrw(data.predictedPrice)}
                </p>
              </>
            )}
            <span
              className="mt-0.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums"
              style={{ backgroundColor: `rgba(${accent.rgb}, 0.16)`, color: accent.color }}
            >
              {isUp ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {data.isEstimate ? "" : "전일比 "}
              {Math.abs(data.changePercent)}%
            </span>
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

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">최근 예측 정확도</span>
            <span className="font-semibold tabular-nums">{data.recentAccuracy}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(100, Math.max(0, data.recentAccuracy))}%`,
                backgroundColor: accent.color,
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
