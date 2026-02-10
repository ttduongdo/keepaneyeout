import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Research Radar",
  description: "Simple RAG tracker for AI papers"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
