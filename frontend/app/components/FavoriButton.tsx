"use client"

import { useState } from "react"
import { Heart } from "lucide-react"
import { useAuth, useClerk } from "@clerk/nextjs"

export default function FavoriButton({ annonceId, initial }: { annonceId: number; initial: boolean }) {
  const { isSignedIn, getToken } = useAuth()
  const clerk = useClerk()
  const [favori, setFavori] = useState(initial)
  const [enCours, setEnCours] = useState(false)

  async function toggle(e: React.MouseEvent) {
    // Le bouton vit souvent dans une carte cliquable : on bloque la navigation
    e.preventDefault()
    e.stopPropagation()
    if (!isSignedIn) {
      clerk.openSignIn()
      return
    }
    if (enCours) return
    setEnCours(true)
    const avant = favori
    setFavori(!avant)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${annonceId}/favori`, {
        method: avant ? "DELETE" : "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) setFavori(avant)
    } catch {
      setFavori(avant)
    } finally {
      setEnCours(false)
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label={favori ? "Retirer des favoris" : "Ajouter aux favoris"}
      className="bg-white/90 backdrop-blur-sm rounded-full p-2 shadow-sm hover:scale-110 transition-transform"
    >
      <Heart className={`w-4 h-4 transition-colors ${favori ? "fill-red-500 text-red-500" : "text-gray-600"}`} />
    </button>
  )
}
