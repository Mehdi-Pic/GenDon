"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Check, ExternalLink, Trash2 } from "lucide-react"

type Signalement = {
  id: number
  annonce_id: number
  annonce_titre: string | null
  raison: string
  traite: boolean
  created_at: string
}

export default function AdminSignalements() {
  const { getToken } = useAuth()
  const [signalements, setSignalements] = useState<Signalement[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/signalements`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif && res.ok) setSignalements(data)
      } catch {} finally {
        if (actif) setLoading(false)
      }
    })()
    return () => { actif = false }
  }, [getToken])

  async function marquerTraite(id: number) {
    const token = await getToken()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/signalements/${id}/traiter`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) setSignalements((prev) => prev.map((s) => (s.id === id ? { ...s, traite: true } : s)))
  }

  async function supprimerAnnonce(s: Signalement) {
    if (!confirm(`Supprimer l'annonce « ${s.annonce_titre} » ? Cette action est définitive.`)) return
    const token = await getToken()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/annonces/${s.annonce_id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      alert("La suppression a échoué.")
      return
    }
    // La suppression en cascade retire aussi les signalements liés
    setSignalements((prev) => prev.filter((x) => x.annonce_id !== s.annonce_id))
  }

  const enAttente = signalements.filter((s) => !s.traite).length

  return (
    <div>
      <h1 className="text-2xl font-black text-gray-900 mb-1">Signalements</h1>
      <p className="text-sm text-gray-400 mb-6">{enAttente} en attente de traitement</p>

      {loading ? (
        <p className="text-gray-400">Chargement...</p>
      ) : signalements.length === 0 ? (
        <p className="text-gray-400 py-12 text-center">Aucun signalement. Tout va bien !</p>
      ) : (
        <div className="flex flex-col gap-3">
          {signalements.map((s) => (
            <div key={s.id} className={`rounded-2xl p-4 ring-1 ${s.traite ? "bg-gray-50 ring-gray-100 opacity-60" : "bg-white ring-red-100"}`}>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                {s.traite ? (
                  <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">Traité</span>
                ) : (
                  <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-semibold">À traiter</span>
                )}
                {s.annonce_titre ? (
                  <Link href={`/annonces/${s.annonce_id}`} target="_blank" className="font-bold text-sm text-gray-900 hover:underline inline-flex items-center gap-1">
                    {s.annonce_titre}
                    <ExternalLink className="w-3 h-3 text-gray-400" />
                  </Link>
                ) : (
                  <span className="text-sm text-gray-400 italic">Annonce supprimée</span>
                )}
                <span className="text-xs text-gray-400 ml-auto">{new Date(s.created_at).toLocaleDateString("fr-FR")}</span>
              </div>
              <p className="text-sm text-gray-600 bg-gray-50 rounded-xl px-3 py-2 mb-3">{s.raison}</p>
              {!s.traite && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => marquerTraite(s.id)}
                    className="flex items-center gap-1.5 border border-gray-200 hover:border-gray-400 text-gray-600 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Marquer traité
                  </button>
                  {s.annonce_titre && (
                    <button
                      onClick={() => supprimerAnnonce(s)}
                      className="flex items-center gap-1.5 border border-red-100 hover:border-red-300 text-red-500 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Supprimer l&apos;annonce
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
