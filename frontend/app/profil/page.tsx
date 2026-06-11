"use client"

import { useUser, useAuth } from "@clerk/nextjs"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { MapPin, Pencil, Trash2, Eye, Heart } from "lucide-react"
import Link from "next/link"
import AnnonceCard from "../components/AnnonceCard"
import { vignette, type Annonce } from "../lib/annonces"

type Onglet = "annonces" | "favoris"

export default function Profil() {
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  const [onglet, setOnglet] = useState<Onglet>("annonces")
  const [annonces, setAnnonces] = useState<Annonce[]>([])
  const [favoris, setFavoris] = useState<Annonce[]>([])
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
        const headers = { Authorization: `Bearer ${token}` }
        const [resAnnonces, resFavoris] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/me`, { headers }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/favoris`, { headers }),
        ])
        const [dataAnnonces, dataFavoris] = await Promise.all([resAnnonces.json(), resFavoris.json()])
        if (actif) {
          setAnnonces(Array.isArray(dataAnnonces) ? dataAnnonces : [])
          setFavoris(Array.isArray(dataFavoris) ? dataFavoris : [])
        }
      } catch {
        if (actif) {
          setAnnonces([])
          setFavoris([])
        }
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
        <h1 className="text-2xl font-black text-gray-900 mb-6">Mon profil</h1>

        <div className="flex items-center gap-2 mb-8">
          <button
            onClick={() => setOnglet("annonces")}
            className={`px-5 py-2.5 rounded-full text-sm font-semibold transition-colors ${
              onglet === "annonces" ? "bg-gray-900 text-white" : "bg-gray-50 text-gray-600 hover:bg-gray-100"
            }`}
          >
            Mes annonces ({annonces.length})
          </button>
          <button
            onClick={() => setOnglet("favoris")}
            className={`px-5 py-2.5 rounded-full text-sm font-semibold transition-colors ${
              onglet === "favoris" ? "bg-gray-900 text-white" : "bg-gray-50 text-gray-600 hover:bg-gray-100"
            }`}
          >
            Mes favoris ({favoris.length})
          </button>
        </div>

        {onglet === "annonces" && (
          annonces.length === 0 ? (
            <div className="text-center py-24">
              <p className="text-gray-400 mb-4">Vous n&apos;avez pas encore déposé d&apos;annonce.</p>
              <Link href="/annonces/new" className="bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white px-6 py-3 rounded-full font-semibold transition-all">
                Déposer un don
              </Link>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {annonces.map((annonce) => (
                <div key={annonce.id} className="flex flex-wrap items-center gap-4 bg-white ring-1 ring-gray-100 rounded-3xl p-4 hover:ring-gray-200 hover:shadow-md transition-all">
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
                    <span className="inline-block text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full mt-2">{annonce.categorie}</span>
                  </div>
                  <div className="w-full flex flex-wrap items-center gap-x-3 gap-y-2">
                    <div className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
                      <MapPin className="w-3 h-3" />
                      {annonce.quartier}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
                      <Eye className="w-3 h-3" />
                      {annonce.vues ?? 0} vue{(annonce.vues ?? 0) > 1 ? "s" : ""}
                    </div>
                    <span className="text-xs text-gray-400 whitespace-nowrap">{new Date(annonce.created_at).toLocaleDateString("fr-FR")}</span>
                    <div className="flex items-center gap-2 ml-auto">
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
                </div>
              ))}
            </div>
          )
        )}

        {onglet === "favoris" && (
          favoris.length === 0 ? (
            <div className="text-center py-24">
              <Heart className="w-10 h-10 text-gray-200 mx-auto mb-4" />
              <p className="text-gray-400 mb-4">Aucun favori pour le moment. Touchez le cœur d&apos;une annonce pour la retrouver ici.</p>
              <Link href="/annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
                Voir les annonces
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">
              {favoris.map((annonce) => (
                <AnnonceCard key={annonce.id} annonce={annonce} />
              ))}
            </div>
          )
        )}
      </div>
    </main>
  )
}
