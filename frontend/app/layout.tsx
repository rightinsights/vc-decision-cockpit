import type { Metadata } from "next";
import Link from "next/link";
import { IBM_Plex_Sans, Playfair_Display } from "next/font/google";
import { BrandMark } from "@/components/brand-mark";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const display = Playfair_Display({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "700", "800"],
});

export const metadata: Metadata = {
  title: "Right Insights Investments",
  description: "AI-assisted decision agent for early-stage investing. Make informed decisions quickly and accurately.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plexSans.variable} ${display.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="bg-forest text-paper" style={{ borderBottom: "3px solid var(--orange)" }}>
          <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between px-8">
            <Link href="/" className="flex items-center gap-3">
              <BrandMark size={38} />
              <span className="display text-[22px] font-bold">Right Insights Investments</span>
            </Link>
            <nav className="flex items-center gap-7 text-[12px] font-bold uppercase tracking-[0.14em] text-paper/80">
              <Link href="/" className="hover:text-paper">Pipeline</Link>
              <Link href="/thesis" className="hover:text-paper">Thesis</Link>
              <span className="inline-flex items-center gap-2 text-paper/90">
                <span className="size-2 rounded-full" style={{ background: "#4fd1a5" }} aria-hidden />
                AI-assisted decision agent
              </span>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1320px] flex-1 px-8 py-10">{children}</main>
        <footer className="mx-auto w-full max-w-[1320px] px-8 pb-8 text-xs text-muted-foreground">
          AI-assisted decision agent. Make informed decisions quickly and accurately.
        </footer>
      </body>
    </html>
  );
}
