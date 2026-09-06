import type { Metadata } from "next";
import Link from "next/link";
import { IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexSerif = IBM_Plex_Serif({
  variable: "--font-plex-serif",
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Decision Cockpit",
  description: "Claims, evidence, thesis fit, and what changed for early-stage deals.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexSerif.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="border-b border-border bg-paper">
          <div className="mx-auto flex h-12 max-w-[1280px] items-center justify-between px-6">
            <Link href="/" className="text-[15px] font-semibold tracking-tight">
              Decision Cockpit
            </Link>
            <nav className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="/" className="hover:text-foreground">Pipeline</Link>
              <Link href="/thesis" className="hover:text-foreground">Thesis</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1280px] flex-1 px-6 py-8">{children}</main>
        <footer className="mx-auto w-full max-w-[1280px] px-6 pb-6 text-xs text-muted-foreground">
          AI recommends. The human decision is only ever changed by hand.
        </footer>
      </body>
    </html>
  );
}
