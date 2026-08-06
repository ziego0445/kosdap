import { Lightbulb, ShieldCheck, Calculator, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: ShieldCheck,
    color: "#3987e5",
    title: "신뢰할 수 있는 데이터",
    desc: "Bybit·Yahoo Finance 등 실시간 시장 데이터 분석",
  },
  {
    icon: Calculator,
    color: "#9085e9",
    title: "계산 기반 예측",
    desc: "LLM이 지어내지 않고, 회귀 모델로 요인별 기여도를 계산",
  },
  {
    icon: Target,
    color: "#d55181",
    title: "정확도 공개",
    desc: "예측 vs 실제 오차를 숨기지 않고 그대로 기록",
  },
];

export function FeatureBand() {
  return (
    <Card size="sm" className="border-white/5 bg-white/[0.02]">
      <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex items-start gap-2.5 sm:max-w-[15rem]">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <div>
            <p className="text-sm font-semibold">추정가란?</p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              과거·실시간 시장 데이터를 계산식에 넣어 산출한 예상 가격입니다.
            </p>
          </div>
        </div>

        <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex items-center gap-2.5">
              <span
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                style={{ backgroundColor: `${f.color}26` }}
              >
                <f.icon className="h-4 w-4" style={{ color: f.color }} />
              </span>
              <div>
                <p className="text-xs font-semibold">{f.title}</p>
                <p className="text-[11px] text-muted-foreground">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
