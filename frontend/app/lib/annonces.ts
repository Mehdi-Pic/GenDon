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
}
