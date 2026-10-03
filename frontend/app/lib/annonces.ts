export const CATEGORIES = [
  "Mobilier", "Vêtements", "Maison & Jardin",
  "Électronique", "Loisirs", "Sport", "Autres",
]

export const QUARTIERS = [
  "Les Grésillons", "Les Chevrins", "Les Agnettes", "Le Village",
  "Le Luth", "Le Fossé de l'Aumône", "Chandon - Brénu - Sévines","République","Cité Jardin",
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
  // Renseigne quand le proprietaire a declare l'objet donne : l'annonce est en cours de retrait
  donne_at?: string | null
  est_proprietaire?: boolean
  est_favori?: boolean
  vues?: number
  // "publiee" ou "reservee" (le donneur a promis l'objet à quelqu'un)
  statut?: string
  // Réservés au propriétaire (Mes annonces)
  nb_interesses?: number | null
  reserve_pour_pseudo?: string | null
}

const UN_JOUR = 86400000

function debutDuJour(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

// « 14:32 » aujourd'hui, « Hier », « lun. » cette semaine, sinon « 12/09 »
export function dateCourte(iso: string, maintenant = Date.now()): string {
  const d = new Date(iso)
  const ecart = Math.round((debutDuJour(new Date(maintenant)) - debutDuJour(d)) / UN_JOUR)
  if (ecart <= 0) return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
  if (ecart === 1) return "Hier"
  if (ecart < 7) return d.toLocaleDateString("fr-FR", { weekday: "short" })
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })
}

// Séparateur de jour dans une conversation : « Aujourd'hui », « Hier », « mardi 12 septembre »
export function libelleJour(iso: string, maintenant = Date.now()): string {
  const d = new Date(iso)
  const ecart = Math.round((debutDuJour(new Date(maintenant)) - debutDuJour(d)) / UN_JOUR)
  if (ecart <= 0) return "Aujourd'hui"
  if (ecart === 1) return "Hier"
  const options: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long" }
  if (d.getFullYear() !== new Date(maintenant).getFullYear()) options.year = "numeric"
  return d.toLocaleDateString("fr-FR", options)
}

export function memeJour(a: string, b: string): boolean {
  return debutDuJour(new Date(a)) === debutDuJour(new Date(b))
}

// Version réduite d'une image Cloudinary pour les listes (vignettes).
export function vignette(url: string, largeur = 600): string {
  return url.includes("/upload/")
    ? url.replace("/upload/", `/upload/w_${largeur},q_auto,f_auto/`)
    : url
}
