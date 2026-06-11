import type { MetadataRoute } from "next"

const BASE = "https://www.gendon.fr"

type AnnonceSitemap = { id: number; created_at: string }
type PageAnnonces = { annonces: AnnonceSitemap[]; pages: number }

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const statiques: MetadataRoute.Sitemap = [
    { url: BASE, changeFrequency: "weekly", priority: 1 },
    { url: `${BASE}/annonces`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${BASE}/mentions-legales`, changeFrequency: "yearly", priority: 0.1 },
    { url: `${BASE}/confidentialite`, changeFrequency: "yearly", priority: 0.1 },
  ]

  try {
    const api = process.env.NEXT_PUBLIC_API_URL
    const premiere: PageAnnonces = await (await fetch(`${api}/annonces`, { cache: "no-store" })).json()
    let annonces = premiere.annonces
    // Annonces auto-supprimées à 30 jours : le volume reste petit, on plafonne par sécurité
    const pagesMax = Math.min(premiere.pages, 10)
    for (let page = 2; page <= pagesMax; page++) {
      const suite: PageAnnonces = await (await fetch(`${api}/annonces?page=${page}`, { cache: "no-store" })).json()
      annonces = annonces.concat(suite.annonces)
    }
    return [
      ...statiques,
      ...annonces.map((a) => ({
        url: `${BASE}/annonces/${a.id}`,
        lastModified: new Date(a.created_at),
        changeFrequency: "daily" as const,
        priority: 0.7,
      })),
    ]
  } catch {
    return statiques
  }
}
