"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { ClipboardList, Eye, Heart, Flag, TrendingUp } from "lucide-react"

type Stats = {
  annonces: number
  annonces_semaine: number
  vues_totales: number
  favoris: number
  signalements_en_attente: number
}

export default function AdminDashboard() {
  const { getToken } = useAuth()
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif && res.ok) setStats(data)
      } catch {}
    })()
    return () => { actif = false }
  }, [getToken])

  const tuiles = stats
    ? [
        { label: "Annonces en ligne", valeur: stats.annonces, Icon: ClipboardList },
        { label: "Publiées cette semaine", valeur: stats.annonces_semaine, Icon: TrendingUp },
        { label: "Vues cumulées", valeur: stats.vues_totales, Icon: Eye },
        { label: "Favoris", valeur: stats.favoris, Icon: Heart },
        { label: "Signalements à traiter", valeur: stats.signalements_en_attente, Icon: Flag, alerte: stats.signalements_en_attente > 0 },
      ]
    : []

  return (
    <div>
      <h1 className="text-2xl font-black text-gray-900 mb-6">Tableau de bord</h1>
      {!stats ? (
        <p className="text-gray-400">Chargement...</p>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {tuiles.map(({ label, valeur, Icon, alerte }) => (
            <div key={label} className={`rounded-3xl p-5 ring-1 ${alerte ? "bg-red-50 ring-red-100" : "bg-gray-50 ring-gray-100"}`}>
              <Icon className={`w-5 h-5 mb-3 ${alerte ? "text-red-500" : "text-green-600"}`} />
              <p className={`text-3xl font-black ${alerte ? "text-red-600" : "text-gray-900"}`}>{valeur}</p>
              <p className="text-sm text-gray-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
