/**
 * dataviz 스킬 절차대로 고른 색상. 손으로 고른 값이 아니라
 * scripts/validate_palette.js로 검증된 조합만 사용한다.
 *
 * - 상승/하락(diverging): 국내 증시 관례대로 상승=빨강/하락=파랑을 유지하되,
 *   실제 hex는 카테고리 팔레트의 slot 1(blue)·slot 8(red)을 그대로 씀
 *   (validate_palette.js "#2a78d6,#e34948" light / "#3987e5,#e66767" dark — PASS)
 * - 예측 vs 실제(categorical, 2 series): slot 1(blue)·slot 2(orange)
 *   (validate_palette.js "#2a78d6,#eb6834" light / "#3987e5,#d95926" dark — PASS)
 */
export const chartColors = {
  light: {
    up: "#e34948",
    down: "#2a78d6",
    predicted: "#2a78d6",
    actual: "#eb6834",
    neutralGrid: "#e1e0d9",
    axisText: "#898781",
  },
  dark: {
    up: "#e66767",
    down: "#3987e5",
    predicted: "#3987e5",
    actual: "#d95926",
    neutralGrid: "#2c2c2a",
    axisText: "#898781",
  },
} as const;

export type ChartColorMode = keyof typeof chartColors;
