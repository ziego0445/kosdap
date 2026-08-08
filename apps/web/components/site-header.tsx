"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LineChart } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "오늘 얼마니?" },
  { href: "/pef", label: "사모펀드 뭐샀니?" },
];

/** trailingSlash:true라 /pef가 /pef/로 올 수 있어 끝 슬래시를 정규화해서 비교. */
function normalize(path: string) {
  return path.length > 1 && path.endsWith("/") ? path.slice(0, -1) : path;
}

export function SiteHeader() {
  const pathname = usePathname();
  const current = normalize(pathname ?? "/");

  return (
    <header className="sticky top-0 z-10 border-b border-white/5 bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-y-1.5 px-3 py-3 sm:px-4">
        <Link href="/" className="flex shrink-0 items-center gap-1.5 text-sm font-bold sm:gap-2 sm:text-base">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#3987e5] to-[#d55181] text-white">
            <LineChart className="h-3.5 w-3.5" />
          </span>
          오늘 얼마니?
        </Link>
        <nav className="flex flex-wrap justify-end gap-1 text-[11px] sm:text-xs">
          {NAV_ITEMS.map((item) => {
            const isActive = normalize(item.href) === current;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={
                  isActive
                    ? "shrink-0 rounded-full bg-white/10 px-2 py-1 font-semibold text-foreground transition-colors sm:px-2.5"
                    : "shrink-0 rounded-full px-2 py-1 text-muted-foreground transition-colors hover:text-foreground sm:px-2.5"
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
