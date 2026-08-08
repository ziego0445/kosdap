export function SiteFooter() {
  return (
    <footer className="border-t border-white/5">
      <div className="mx-auto max-w-4xl space-y-2 px-4 py-4">
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          본 정보는 투자 참고용으로 제공되며, 특정 종목의 매매를 권유하거나
          투자자문을 제공하지 않습니다. 추정가격은 공개된 시장 데이터를
          바탕으로 자동 계산되며 실제 가격과 다를 수 있습니다. 투자 판단과
          책임은 이용자 본인에게 있습니다.
        </p>
        <p className="text-[10px] text-muted-foreground/60">
          © {new Date().getFullYear()} 오늘 얼마니?. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
