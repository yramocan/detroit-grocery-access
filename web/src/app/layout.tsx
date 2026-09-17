import type { Metadata } from "next";
import { Fraunces, Figtree } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const sans = Figtree({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Detroit 15 — Grocery Walk Access",
  description:
    "What percentage of Detroit residents can walk to a qualifying grocery store within 15 minutes?",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} antialiased`}>
        <div className="min-h-screen">
          <header className="relative z-20 border-b border-ink/10 bg-white/55 backdrop-blur-md">
            <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
              <Link href="/" className="group flex items-baseline gap-2">
                <span className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
                  Detroit 15
                </span>
                <span className="hidden text-sm text-ink/55 sm:inline">
                  Grocery walk access
                </span>
              </Link>
              <nav className="flex items-center gap-4 text-sm font-medium text-ink/70">
                <Link href="/" className="transition hover:text-canopy">
                  Map
                </Link>
                <Link href="/methodology" className="transition hover:text-canopy">
                  Methodology
                </Link>
              </nav>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
