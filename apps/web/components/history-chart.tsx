"use client";

import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { PredictionHistoryRow } from "@/lib/types";
import { chartColors, tooltipStyle } from "@/lib/chart-colors";
import { useColorMode } from "@/lib/use-color-mode";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

/**
 * 예측가 vs 실제가를 시계열로 비교. 두 시리즈(정체성 비교)라서 categorical
 * 배정: slot1(파랑)=예측, slot2(주황)=실제 — dataviz 스킬의 고정 순서 규칙.
 * 2개 이상 시리즈라 범례는 항상 노출.
 */
export function HistoryChart({ rows }: { rows: PredictionHistoryRow[] }) {
  const mode = useColorMode();
  const colors = chartColors[mode];

  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));

  const data = {
    labels: sorted.map((r) => r.date.slice(5)), // MM-DD
    datasets: [
      {
        label: "예측가",
        data: sorted.map((r) => r.predicted),
        borderColor: colors.predicted,
        backgroundColor: colors.predicted,
        pointRadius: 3,
        borderWidth: 2,
        tension: 0.15,
      },
      {
        label: "실제가",
        data: sorted.map((r) => r.actual),
        borderColor: colors.actual,
        backgroundColor: colors.actual,
        pointRadius: 3,
        borderWidth: 2,
        tension: 0.15,
      },
    ],
  };

  return (
    <div style={{ height: 220 }}>
      <Line
        data={data}
        options={{
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: {
              position: "top",
              align: "end",
              labels: { color: colors.axisText, boxWidth: 12, boxHeight: 12 },
            },
            tooltip: {
              ...tooltipStyle,
              callbacks: {
                label: (ctx) =>
                  `${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString("ko-KR")}원`,
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              border: { display: false },
              ticks: { color: colors.axisText },
            },
            y: {
              grid: { color: colors.neutralGrid },
              border: { display: false },
              ticks: {
                color: colors.axisText,
                callback: (v) => `${(Number(v) / 1000).toFixed(0)}k`,
              },
            },
          },
        }}
      />
    </div>
  );
}
