export const CATEGORIES = [
  "Immobilier", "Vêtements", "Maison & Jardin",
  "Électronique", "Loisirs", "Sport", "Autres",
]

export const QUARTIERS = [
  "Les Grésillons", "Les Chevrins", "Les Agnettes", "Le Village",
  "Le Luth", "Le Fossé de l'Aumône", "Chandon - Brénu - Sévines",
]

export type Annonce = {
  id: number
  titre: string
  description: string
  categorie: string
  quartier: string
  pseudo: string
  images: string[]
  created_at: string
  est_proprietaire?: boolean
}

// Version réduite d'une image Cloudinary pour les listes (vignettes).
export function vignette(url: string, largeur = 600): string {
  return url.includes("/upload/")
    ? url.replace("/upload/", `/upload/w_${largeur},q_auto,f_auto/`)
    : url
}
