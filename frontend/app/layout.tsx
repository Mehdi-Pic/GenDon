import type { Metadata } from "next";
import { Inter, Sora } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { frFR } from "@clerk/localizations";

import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import Header from "./components/Header";
import Footer from "./components/Footer";

// Le pack français ne traduit pas le message affiché à un compte suspendu (code d'erreur Clerk
// « user_banned », absent du type officiel d'où la conversion de type)
const localisation = {
  ...frFR,
  unstable__errors: {
    ...frFR.unstable__errors,
    user_banned:
      "Votre compte a été suspendu par l'équipe de GenDon. Si vous pensez qu'il s'agit d'une erreur, écrivez-nous via la page Contact.",
  } as typeof frFR.unstable__errors,
};

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
    default: "GenDon · Dons gratuits entre habitants de Gennevilliers",
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
    <ClerkProvider localization={localisation}>
      <html lang="fr" className={`${inter.variable} ${sora.variable}`}>
        <body className="bg-white text-gray-900 min-h-screen font-sans antialiased flex flex-col">
          <Header />
          <div className="flex-1">{children}</div>
          <Footer />
          <Analytics />
        </body>
      </html>
    </ClerkProvider>
  );
}