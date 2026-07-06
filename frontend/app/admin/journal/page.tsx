"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"

type Action = {
  id: number
  par: string
  action: string
  details: string | null
  created_at: string
}

const LIBELLES: Record<string, string> = {
  suppression_annonce: "Suppression d'annonce",
  changement_role: "Changement de rôle",
  signalement_traite: "Signalement traité",
}

export default function AdminJournal() {
  const { getToken } = useAuth()
  const [actions, setActions] = useState<Action[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/journal`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif && res.ok) setActions(data)
      } catch {} finally {
        if (actif) setLoading(false)
      }
    })()
    return () => { actif = false }
  }, [getToken])

  return (
    <div>
      <h1 className="text-2xl font-black text-gray-900 mb-1">Journal de modération</h1>
      <p className="text-sm text-gray-400 mb-6">Les 200 dernières actions</p>

      {loading ? (
        <p className="text-gray-400">Chargement...</p>
      ) : actions.length === 0 ? (
        <p className="text-gray-400 py-12 text-center">Aucune action enregistrée pour le moment.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {actions.map((a) => (
            <div key={a.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 bg-white ring-1 ring-gray-100 rounded-2xl px-4 py-3 text-sm">
              <span className="text-xs text-gray-400 whitespace-nowrap">
                {new Date(a.created_at).toLocaleDateString("fr-FR")} {new Date(a.created_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
              </span>
              <span className="font-semibold text-gray-900">{LIBELLES[a.action] ?? a.action}</span>
              {a.details && <span className="text-gray-500">{a.details}</span>}
              <span className="text-xs text-gray-300 ml-auto truncate max-w-[180px]" title={a.par}>par {a.par}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
