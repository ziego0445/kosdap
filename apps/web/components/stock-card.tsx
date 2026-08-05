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

function formatKrw(value: number) {
  return `${value.toLocaleString("ko-KR")}원`;
}

export function StockCard({ data }: { data: StockPrediction }) {
  const isUp = data.changePercent >= 0;

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-xl">{data.name}</CardTitle>
          <p className="text-sm text-muted-foreground">{data.ticker}</p>
        </div>
        {data.isWeekend && (
          <Badge variant="secondary">주말 · 신규 데이터 제한</Badge>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm text-muted-foreground">현재가</p>
            <p className="text-2xl font-semibold">
              {formatKrw(data.currentPrice)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">추정가</p>
            <p
              className={cn(
                "text-2xl font-bold",
                isUp ? "text-red-500" : "text-blue-500"
              )}
            >
              {formatKrw(data.predictedPrice)}
            </p>
            <p
              className={cn(
                "text-sm font-medium",
                isUp ? "text-red-500" : "text-blue-500"
              )}
            >
              {isUp ? "▲" : "▼"} {Math.abs(data.changePercent)}%
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-sm">
          <div className="rounded-md bg-muted p-2">
            <p className="text-muted-foreground">상승확률</p>
            <p className="font-semibold">{data.probabilityUp}%</p>
          </div>
          <div className="rounded-md bg-muted p-2">
            <p className="text-muted-foreground">신뢰도</p>
            <p className="font-semibold">{data.confidence}%</p>
          </div>
          <div className="rounded-md bg-muted p-2">
            <p className="text-muted-foreground">예상 범위</p>
            <p className="font-semibold">
              {(data.rangeLow / 1000).toFixed(1)}k~
              {(data.rangeHigh / 1000).toFixed(1)}k
            </p>
          </div>
        </div>

        <Separator />

        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">
            영향요인
          </p>
          <ul className="space-y-1 text-sm">
            {data.factors.map((f) => (
              <li key={f.label} className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span
                    className={cn(
                      "inline-block h-2 w-2 rounded-full",
                      f.contribution >= 0 ? "bg-red-500" : "bg-blue-500"
                    )}
                  />
                  {f.label}
                </span>
                <span
                  className={cn(
                    "font-medium",
                    f.contribution >= 0 ? "text-red-500" : "text-blue-500"
                  )}
                >
                  {f.contribution >= 0 ? "+" : ""}
                  {f.contribution}%
                </span>
              </li>
            ))}
          </ul>
        </div>

        <Separator />

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">최근 예측 정확도</span>
          <span className="font-semibold">{data.recentAccuracy}%</span>
        </div>
      </CardContent>
    </Card>
  );
}
