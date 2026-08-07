"use client";

import { useEffect, useRef } from "react";

/**
 * 카카오 애드핏 광고 슬롯. next/script로 전역에 한 번만 로드하면 SPA
 * 클라이언트 네비게이션(Link로 페이지 이동) 시 새로 마운트된 <ins>를
 * 애드핏 스크립트가 다시 스캔하지 않아 광고가 안 뜨는 문제가 있어서,
 * 컴포넌트가 마운트될 때마다 스크립트 태그를 직접 새로 주입한다.
 */
export function KakaoAdFit({
  adUnit,
  width,
  height,
}: {
  adUnit: string;
  width: number;
  height: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "//t1.kakaocdn.net/kas/static/ba.min.js";
    script.async = true;
    containerRef.current?.appendChild(script);
    return () => {
      script.remove();
    };
  }, []);

  return (
    <div ref={containerRef} className="flex justify-center">
      <ins
        className="kakao_ad_area"
        style={{ display: "none", width: "100%" }}
        data-ad-unit={adUnit}
        data-ad-width={String(width)}
        data-ad-height={String(height)}
      />
    </div>
  );
}
