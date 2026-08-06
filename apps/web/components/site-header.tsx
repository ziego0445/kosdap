import Link from "next/link";
import { LineChart } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "추정가" },
  { href: "/history", label: "기록" },
  { href: "/admin", label: "관리자" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-base font-bold">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-[#3987e5] to-[#e66767] text-white">
            <LineChart className="h-3.5 w-3.5" />
          </span>
          kosdap
        </Link>
        <nav className="flex gap-1 text-sm">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
