export type Annonce = {
  id: number
  titre: string
  description: string
  categorie: string
  quartier: string
  pseudo: string
  date: string
  image: string
}

export const annonces: Annonce[] = [
  {
    id: 1,
    titre: "Canapé 3 places",
    description: "Bon état général, quelques traces d'usure sur les accoudoirs. À venir chercher.",
    categorie: "Meubles",
    quartier: "Les Grésillons",
    pseudo: "Marie92",
    date: "18 mai 2025",
    image: "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400",
  },
  {
    id: 2,
    titre: "Lot de livres jeunesse",
    description: "15 livres pour enfants de 3 à 8 ans, très bon état.",
    categorie: "Livres",
    quartier: "Centre-ville",
    pseudo: "Thomas_GNV",
    date: "17 mai 2025",
    image: "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
  },
  {
    id: 3,
    titre: "Vélo enfant 16 pouces",
    description: "Vélo rose avec stabilisateurs, pour enfant de 4-6 ans.",
    categorie: "Sport",
    quartier: "Lochères",
    pseudo: "Fatima_GNV",
    date: "16 mai 2025",
    image: "https://images.unsplash.com/photo-1591768793355-74d04bb6608f?w=400",
  },
]