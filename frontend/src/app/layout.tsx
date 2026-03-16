import "./globals.css";
import { ReactNode } from "react";
import { PageMotion } from "@/components/PageMotion";
import { TopNav } from "@/components/TopNav";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ro">
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-slate-900 focus:shadow-lg"
        >
          Sare la conținut
        </a>
        <TopNav />
        <PageMotion>{children}</PageMotion>
      </body>
    </html>
  );
}
