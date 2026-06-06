import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EduAgent",
  applicationName: "EduAgent",
  description: "AI-powered personalized student study assistant",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg"
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
