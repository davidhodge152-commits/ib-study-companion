import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "katex/dist/katex.min.css";
import { QueryProvider } from "@/providers/QueryProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { AuthProvider } from "@/providers/AuthProvider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "./app-shell";
import { Toaster } from "sonner";
import { ServiceWorkerRegistrar } from "@/components/shared/ServiceWorkerRegistrar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "IB Study Companion",
    template: "%s | IB Study Companion",
  },
  description:
    "AI-powered IB exam preparation platform with personalized study tools, flashcards, AI tutoring, and grade predictions.",
  manifest: "/manifest.json",
  metadataBase: new URL("https://ib-study-companion.vercel.app"),
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "IB Study Companion",
    title: "IB Study Companion — AI-Powered IB Exam Prep",
    description:
      "Personalized study tools, flashcards, AI tutoring, and grade predictions for IB Diploma students.",
  },
  twitter: {
    card: "summary_large_image",
    title: "IB Study Companion — AI-Powered IB Exam Prep",
    description:
      "Personalized study tools, flashcards, AI tutoring, and grade predictions for IB Diploma students.",
  },
  robots: {
    index: true,
    follow: true,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "IB Study",
  },
};

export const viewport: Viewport = {
  themeColor: "#4f46e5",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <QueryProvider>
          <ThemeProvider>
            <TooltipProvider>
              <AuthProvider>
                <AppShell>{children}</AppShell>
                <Toaster richColors position="bottom-right" />
                <ServiceWorkerRegistrar />
              </AuthProvider>
            </TooltipProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
