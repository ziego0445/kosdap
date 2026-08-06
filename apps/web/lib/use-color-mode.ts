/**
 * kosdap은 라이트/다크 자동전환 대신 약간 어두운 톤 하나로 고정했다
 * (app/globals.css 참고). Chart.js는 CSS를 못 읽으므로 lib/chart-colors.ts의
 * dark 세트를 그대로 쓰면 된다 — 이 함수는 나중에 테마 토글이 생기면 다시
 * 동적으로 바꿀 수 있도록 인터페이스만 유지.
 */
export function useColorMode(): "light" | "dark" {
  return "dark";
}
