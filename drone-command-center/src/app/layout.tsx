import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MJN Command Center — Autonomous Drone Navigation System",
  description:
    "World-class premium 3D Command Center dashboard for autonomous drone navigation. Aerospace-grade monitoring with real-time telemetry, 3D mission visualization, and AI-powered prediction.",
  keywords: [
    "drone", "autonomous", "navigation", "command center",
    "telemetry", "3D map", "UAV", "mission control",
  ],
  authors: [{ name: "MJN Aerospace" }],
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#050505",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#050505] text-white">
        {children}
      </body>
    </html>
  );
}
