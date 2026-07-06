"use client"

import { useEffect, useState, useCallback } from "react"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Search, Trash2, ExternalLink, Eye } from "lucide-react"
import { vignette, type Annonce } from "../../lib/annonces"

export default function AdminAnnonces() {
  const { getToken } = useAuth()
  const [annonces, setAnnonces] = useState<Annonce[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [page, setPage] = useState(1)
  const [recherche, setRecherche] = useState("")
  const [loading, setLoading] = useState(true)

  const charger = useCallback(async (p: number, q: string) => {
    setLoading(true)
    try {
      const token = await getToken()
      const params = new URLSearchParams()
      if (q) params.set("recherche", q)
      if (p > 1) params.set("page", String(p))
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/annonces?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      if (res.ok) {
        setAnnonces(data.annonces)
        setTotal(data.total)
        setPages(data.pages)
      }
    } catch {} finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => { charger(page, recherche) }, [charger, page])

  async function supprimer(annonce: Annonce) {
    if (!confirm(`Supprimer « ${annonce.titre} » de ${annonce.pseudo} ? Cette action est définitive.`)) return
    const token = await getToken()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/annonces/${annonce.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      alert("La suppression a échoué.")
      return
    }
    setAnnonces((prev) => prev.filter((a) => a.id !== annonce.id))
    setTotal((t) => t - 1)
  }

  return (
    <div>
      <h1 className="text-2xl font-black text-gray-900 mb-1">Annonces</h1>
      <p className="text-sm text-gray-400 mb-6">{total} annonce{total > 1 ? "s" : ""} en ligne</p>

      <form
        onSubmit={(e) => { e.preventDefault(); setPage(1); charger(1, recherche) }}
        className="relative mb-6 max-w-md"
      >
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input
          type="text"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          placeholder="Rechercher titre, description, pseudo..."
          className="w-full pl-10 pr-4 py-2.5 bg-gray-100 border border-transparent rounded-full text-sm focus:outline-none focus:border-green-500 focus:bg-white transition-all"
        />
      </form>

      {loading ? (
        <p className="text-gray-400">Chargement...</p>
      ) : annonces.length === 0 ? (
        <p className="text-gray-400 py-12 text-center">Aucune annonce trouvée.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {annonces.map((a) => (
            <div key={a.id} className="flex flex-wrap items-center gap-3 bg-white ring-1 ring-gray-100 rounded-2xl p-3">
              {a.images && a.images.length > 0 ? (
                <img src={vignette(a.images[0], 200)} alt="" className="w-14 h-14 object-cover rounded-xl shrink-0" />
              ) : (
                <div className="w-14 h-14 bg-gray-100 rounded-xl shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="font-bold text-gray-900 truncate text-sm">{a.titre}</p>
                <p className="text-xs text-gray-400 truncate">
                  @{a.pseudo} · {a.quartier} · {new Date(a.created_at).toLocaleDateString("fr-FR")} ·{" "}
                  <Eye className="w-3 h-3 inline -mt-0.5" /> {a.vues ?? 0}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-auto">
                <Link href={`/annonces/${a.id}`} target="_blank" className="p-2 text-gray-400 hover:text-gray-900 transition-colors" aria-label="Voir l'annonce">
                  <ExternalLink className="w-4 h-4" />
                </Link>
                <button
                  onClick={() => supprimer(a)}
                  className="flex items-center gap-1.5 border border-red-100 hover:border-red-300 text-red-500 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Supprimer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-8">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-4 py-2 rounded-full text-sm border border-gray-200 disabled:opacity-40 hover:border-gray-400 transition-colors"
          >
            Précédent
          </button>
          <span className="text-sm text-gray-500">{page} / {pages}</span>
          <button
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-4 py-2 rounded-full text-sm border border-gray-200 disabled:opacity-40 hover:border-gray-400 transition-colors"
          >
            Suivant
          </button>
        </div>
      )}
    </div>
  )
}
