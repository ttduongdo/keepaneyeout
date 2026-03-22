import "./globals.css";
import type { Metadata } from "next";
import AuthGate from "./components/AuthGate";
import { TopicsProvider } from "./hooks/useTopics";
import { ThemeProvider } from "./hooks/useTheme";

export const metadata: Metadata = {
  title: "Pinsight",
  description: "Simple RAG tracker for AI papers"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ThemeProvider>
          <TopicsProvider>
            <AuthGate>{children}</AuthGate>
          </TopicsProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
