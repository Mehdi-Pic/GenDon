"use client"

import { useEffect } from "react"
import { useAuth } from "@clerk/nextjs"

// Compte une vue à l'affichage réel de la page — exclut bots, prefetch et fetch des metadata.
// Le token (si connecté) permet au backend de ne pas compter le propriétaire.
export default function VueTracker({ annonceId }: { annonceId: number }) {
  const { isLoaded, getToken } = useAuth()

  useEffect(() => {
    if (!isLoaded) return
    let annule = false
    ;(async () => {
      try {
        const token = await getToken()
        if (annule) return
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${annonceId}/vue`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        })
      } catch {
        // une vue non comptée n'est pas grave
      }
    })()
    return () => { annule = true }
  }, [isLoaded, annonceId, getToken])

  return null
}
