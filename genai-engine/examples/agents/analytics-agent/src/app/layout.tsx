import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TelemetryProvider } from "@/providers/TelemetryProvider";
import { CopilotKitWithHeaders } from "@/components/CopilotKitWithHeaders";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Data Analyst Agent",
  description: "Data Analyst Agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <TelemetryProvider>
          <CopilotKitWithHeaders>
            {children}
          </CopilotKitWithHeaders>
        </TelemetryProvider>
      </body>
    </html>
  );
}
