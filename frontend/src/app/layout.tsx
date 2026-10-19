import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SessaoProvider } from "@/contexts/sessao";
import { SCRIPT_DO_TEMA } from "@/lib/tema";

export const metadata: Metadata = {
  title: "Basiléia Encontros",
  description: "Para solteiros da igreja se conhecerem por afinidade",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg", apple: "/apple-touch-icon.png" },
  appleWebApp: { capable: true, title: "Encontros", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f4ff" },
    { media: "(prefers-color-scheme: dark)", color: "#110a30" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_DO_TEMA }} />
      </head>
      <body className="min-h-full font-sans">
        <SessaoProvider>{children}</SessaoProvider>
      </body>
    </html>
  );
}
