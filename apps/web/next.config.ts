import type { NextConfig } from "next";
import { BASE_PATH } from "./lib/site-config";

// GitHub Pages는 정적 파일만 서빙하고 프로젝트 사이트는
// https://<user>.github.io/<repo>/ 경로로 뜨기 때문에 output: "export" +
// basePath가 필요하다. 로컬 `npm run dev`는 output:"export"의 영향을 받지
// 않아 그대로 동작한다(Next가 dev 모드에서는 무시).
const nextConfig: NextConfig = {
  output: "export",
  basePath: BASE_PATH,
  trailingSlash: true,
  images: { unoptimized: true }, // export 모드는 이미지 최적화 서버가 없음
};

export default nextConfig;
