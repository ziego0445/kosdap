import { StockSymbol } from "./types";

/**
 * 종목별 브랜드 액센트. 값 방향(상승/하락)과는 무관한 카드 아이덴티티
 * 색상이라 dataviz 스킬의 categorical 룰 적용 — 문서화된 팔레트 slot만
 * 사용하고 실제로 validate_palette.js를 돌려 통과 확인함:
 *   "#3987e5,#d55181" --mode dark --surface "#211e26" -> ALL CHECKS PASS
 * (참고: blue+violet 조합은 시각적으로 너무 가까워서 FAIL — magenta로 교체)
 *
 * rgb는 컬러 다이나믹 인라인 스타일(glow 등)에 쓰려고 미리 풀어둔 값 —
 * Tailwind의 `text-[var]` 같은 임의값 클래스는 빌드 시점에 문자열을
 * 스캔하는 방식이라 런타임 JS 변수로는 안 먹힘, 그래서 style 속성을 씀.
 */
export const SYMBOL_ACCENT: Record<
  StockSymbol,
  { color: string; rgb: string; label: string }
> = {
  SAMSUNG: { color: "#3987e5", rgb: "57, 135, 229", label: "SS" },
  SKHYNIX: { color: "#d55181", rgb: "213, 81, 129", label: "SK" },
};
