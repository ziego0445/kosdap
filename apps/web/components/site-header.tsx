import Link from "next/link";
import { LineChart } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "추정가" },
  { href: "/history", label: "예측 기록" },
  { href: "/admin", label: "관리자" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-[#2a78d6] to-[#e34948] text-white dark:from-[#3987e5] dark:to-[#e66767]">
            <LineChart className="h-4 w-4" />
          </span>
          kosdap
        </Link>
        <nav className="flex gap-1 text-sm">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
