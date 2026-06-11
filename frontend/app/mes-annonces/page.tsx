"use client"

import { useUser, useAuth } from "@clerk/nextjs"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { MapPin, Pencil, Trash2 } from "lucide-react"
import Link from "next/link"
import { vignette, type Annonce } from "../lib/annonces"

export default function MesAnnonces() {
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  const [annonces, setAnnonces] = useState<Annonce[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace("/")
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif) setAnnonces(Array.isArray(data) ? data : [])
      } catch {
        if (actif) setAnnonces([])
      } finally {
        if (actif) setLoading(false)
      }
    })()
    return () => { actif = false }
  }, [isLoaded, isSignedIn, getToken])

  async function supprimerAnnonce(id: number) {
    if (!confirm("Supprimer cette annonce ?")) return
    const token = await getToken()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      alert("La suppression a échoué. Réessayez.")
      return
    }
    setAnnonces((prev) => prev.filter((a) => a.id !== id))
  }

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <main>
        <div className="max-w-4xl mx-auto px-6 py-12">
          <p className="text-gray-400">Chargement...</p>
        </div>
      </main>
    )
  }

  return (
    <main>
      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-black text-gray-900 mb-2">Mes annonces</h1>
        <p className="text-gray-500 text-sm mb-8">{annonces.length} annonce{annonces.length > 1 ? "s" : ""} déposée{annonces.length > 1 ? "s" : ""}</p>
        {annonces.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-gray-400 mb-4">Vous n'avez pas encore déposé d'annonce.</p>
            <Link href="/annonces/new" className="bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white px-6 py-3 rounded-full font-semibold transition-all">
              Déposer un don
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {annonces.map((annonce) => (
              <div key={annonce.id} className="flex items-center gap-4 bg-white ring-1 ring-gray-100 rounded-3xl p-4 hover:ring-gray-200 hover:shadow-md transition-all">
                {annonce.images && annonce.images.length > 0 ? (
                  <img src={vignette(annonce.images[0], 200)} alt={annonce.titre} className="w-20 h-20 object-cover rounded-xl shrink-0" />
                ) : (
                  <div className="w-20 h-20 bg-gray-100 rounded-xl shrink-0 flex items-center justify-center">
                    <span className="text-gray-400 text-xs">Pas de photo</span>
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h2 className="text-gray-900 font-bold truncate">{annonce.titre}</h2>
                  <p className="text-gray-500 text-sm line-clamp-1 mt-0.5">{annonce.description}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{annonce.categorie}</span>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <MapPin className="w-3 h-3" />
                      {annonce.quartier}
                    </div>
                    <span className="text-xs text-gray-400">{new Date(annonce.created_at).toLocaleDateString("fr-FR")}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link href={`/mes-annonces/${annonce.id}/modifier`} className="flex items-center gap-1.5 border border-gray-200 hover:border-gray-400 text-gray-600 px-3 py-2 rounded-full text-sm font-medium transition-colors">
                    <Pencil className="w-4 h-4" />
                    Modifier
                  </Link>
                  <button onClick={() => supprimerAnnonce(annonce.id)} className="flex items-center gap-1.5 border border-red-100 hover:border-red-300 text-red-500 px-3 py-2 rounded-full text-sm font-medium transition-colors">
                    <Trash2 className="w-4 h-4" />
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}