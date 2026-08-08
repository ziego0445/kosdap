import Link from "next/link";
import { LineChart } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "추정가" },
  { href: "/history", label: "예측 기록" },
  { href: "/pef", label: "사모펀드" },
  { href: "/admin", label: "데이터 소스" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-white/5 bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-base font-bold">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-[#3987e5] to-[#d55181] text-white">
            <LineChart className="h-3.5 w-3.5" />
          </span>
          오늘 얼마니!?
        </Link>
        <nav className="flex gap-4 text-xs text-muted-foreground">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="transition-colors hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
