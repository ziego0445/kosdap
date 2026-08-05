import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="text-lg font-bold">
          kosdap
        </Link>
        <nav className="flex gap-4 text-sm text-muted-foreground">
          <Link href="/" className="hover:text-foreground">
            추정가
          </Link>
          <Link href="/history" className="hover:text-foreground">
            예측 기록
          </Link>
          <Link href="/admin" className="hover:text-foreground">
            관리자
          </Link>
        </nav>
      </div>
    </header>
  );
}
