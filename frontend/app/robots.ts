import type { MetadataRoute } from "next"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/profil", "/mes-annonces"],
    },
    sitemap: "https://www.gendon.fr/sitemap.xml",
  }
}
