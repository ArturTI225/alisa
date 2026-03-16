"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Explore Requests" },
  { href: "/bookings/new/", label: "Create Request" },
  { href: "/bookings/", label: "My Requests" },
  { href: "/chat/", label: "Messages" },
  { href: "/accounts/profile/", label: "Profile" },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="mb-6 border-b border-slate-200 bg-white/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-lg font-semibold text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
          ALISA
        </Link>
        <nav aria-label="Primary">
          <ul className="flex flex-wrap items-center gap-3 text-sm font-semibold text-slate-700">
            {navItems.map((item) => {
              const active = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`rounded-lg px-3 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                      active ? "bg-primary/10 text-primary" : "hover:bg-slate-100"
                    }`}
                    aria-current={active ? "page" : undefined}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
