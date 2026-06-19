import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

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
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        `}</style>
      </head>
      <body className="min-h-full flex flex-col bg-[#050505] text-white">
        {children}
      </body>
    </html>
  );
}