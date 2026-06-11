import type { Metadata } from "next";
import { Inter, Sora } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { frFR } from "@clerk/localizations";
import "./globals.css";
import Header from "./components/Header";
import Footer from "./components/Footer";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.gendon.fr"),
  title: {
    default: "GenDon — Dons gratuits entre habitants de Gennevilliers",
    template: "%s · GenDon",
  },
  description: "Donnez une seconde vie à vos objets à Gennevilliers. Plateforme de dons 100% gratuite et locale entre habitants.",
  openGraph: {
    siteName: "GenDon",
    locale: "fr_FR",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider localization={frFR}>
      <html lang="fr" className={`${inter.variable} ${sora.variable}`}>
        <body className="bg-white text-gray-900 min-h-screen font-sans antialiased flex flex-col">
          <Header />
          <div className="flex-1">{children}</div>
          <Footer />
        </body>
      </html>
    </ClerkProvider>
  );
}