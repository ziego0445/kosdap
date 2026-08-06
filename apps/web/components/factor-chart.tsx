"use client";

import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import { InfluenceFactor } from "@/lib/types";
import { chartColors, tooltipStyle } from "@/lib/chart-colors";
import { useColorMode } from "@/lib/use-color-mode";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

/**
 * 영향요인을 0 기준 diverging bar로 보여준다 (dataviz 스킬: polarity는
 * diverging, 두 색 + 중립 기준선). 값 큰 순서로 정렬해서 가장 영향력 있는
 * 요인이 위로 오게 한다.
 */
export function FactorChart({ factors }: { factors: InfluenceFactor[] }) {
  const mode = useColorMode();
  const colors = chartColors[mode];

  const sorted = [...factors].sort(
    (a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)
  );

  const data = {
    labels: sorted.map((f) => f.label),
    datasets: [
      {
        data: sorted.map((f) => f.contribution),
        backgroundColor: sorted.map((f) =>
          f.contribution >= 0 ? colors.up : colors.down
        ),
        borderRadius: 4,
        barPercentage: 0.7,
        categoryPercentage: 0.85,
      },
    ],
  };

  return (
    <div style={{ height: Math.max(110, sorted.length * 22) }}>
      <Bar
        data={data}
        options={{
          indexAxis: "y",
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...tooltipStyle,
              displayColors: false,
              callbacks: {
                label: (ctx) => `${(ctx.raw as number) >= 0 ? "+" : ""}${ctx.raw}%`,
              },
            },
          },
          scales: {
            x: {
              grid: { color: colors.neutralGrid },
              border: { display: false },
              ticks: { color: colors.axisText, font: { size: 10 }, callback: (v) => `${v}%` },
            },
            y: {
              grid: { display: false },
              border: { display: false },
              ticks: { color: colors.axisText, font: { size: 10 } },
            },
          },
        }}
      />
    </div>
  );
}
