"use client";

import { useEffect, useState } from "react";

/**
 * Chart.js는 CSS를 안 읽으므로, 다크모드 여부를 JS에서 직접 판정해서
 * lib/chart-colors.ts의 light/dark 세트 중 하나를 골라 써야 한다.
 * globals.css의 다크모드 판정(prefers-color-scheme, .dark 클래스)과
 * 동일한 우선순위로 맞춘다.
 */
export function useColorMode(): "light" | "dark" {
  const [mode, setMode] = useState<"light" | "dark">("light");

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");

    function resolve() {
      const explicitLight = document.documentElement.classList.contains("light");
      const explicitDark = document.documentElement.classList.contains("dark");
      if (explicitDark) return "dark";
      if (explicitLight) return "light";
      return query.matches ? "dark" : "light";
    }

    setMode(resolve());
    const listener = () => setMode(resolve());
    query.addEventListener("change", listener);

    const observer = new MutationObserver(listener);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    return () => {
      query.removeEventListener("change", listener);
      observer.disconnect();
    };
  }, []);

  return mode;
}
