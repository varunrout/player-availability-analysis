import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Player Availability Analysis — Review",
  description: "Practitioner decision-support review interface. Not a live system.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <header className="app-header">
          <span className="app-title">Player Availability Analysis</span>
          <span className="app-subtitle">Review interface — retrospective data, not live</span>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
