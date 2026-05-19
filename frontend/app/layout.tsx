import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MEV-Watch",
  description: "Real-time MEV detection on Ethereum — sandwich + JIT.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface text-zinc-100 antialiased">{children}</body>
    </html>
  );
}
