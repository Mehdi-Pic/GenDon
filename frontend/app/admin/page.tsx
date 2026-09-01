"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { ClipboardList, Eye, Heart, Flag, TrendingUp, HandHeart } from "lucide-react"

type Stats = {
  annonces: number
  annonces_semaine: number
  vues_totales: number
  favoris: number
  dons_realises: number
  signalements_en_attente: number
}

export default function AdminDashboard() {
  const { getToken } = useAuth()
  const [stats, setStats] = useState<Stats | null>(null)
  const [erreur, setErreur] = useState(false)

  useEffect(() => {
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (!actif) return
        if (res.ok) setStats(data)
        else setErreur(true)
      } catch {
        if (actif) setErreur(true)
      }
    })()
    return () => { actif = false }
  }, [getToken])

  const tuiles = stats
    ? [
        { label: "Annonces en ligne", valeur: stats.annonces, Icon: ClipboardList, href: "/admin/annonces" },
        { label: "Publiées cette semaine", valeur: stats.annonces_semaine, Icon: TrendingUp },
        { label: "Dons réalisés", valeur: stats.dons_realises, Icon: HandHeart },
        { label: "Vues cumulées", valeur: stats.vues_totales, Icon: Eye },
        { label: "Favoris", valeur: stats.favoris, Icon: Heart },
        {
          label: "Signalements à traiter",
          valeur: stats.signalements_en_attente,
          Icon: Flag,
          href: "/admin/signalements",
          alerte: stats.signalements_en_attente > 0,
        },
      ]
    : []

  return (
    <div>
      <h1 className="text-xl sm:text-2xl font-black text-gray-900 mb-4 sm:mb-6">Tableau de bord</h1>

      {erreur ? (
        <p className="text-red-500 text-sm">Les statistiques n&apos;ont pas pu être chargées.</p>
      ) : !stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-3xl p-4 sm:p-5 bg-gray-50 ring-1 ring-gray-100 animate-pulse">
              <div className="w-5 h-5 bg-gray-200 rounded mb-3" />
              <div className="w-12 h-7 bg-gray-200 rounded mb-2" />
              <div className="w-20 h-3 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {tuiles.map(({ label, valeur, Icon, alerte, href }) => {
            const contenu = (
              <>
                <Icon className={`w-5 h-5 mb-2 sm:mb-3 ${alerte ? "text-red-500" : "text-green-600"}`} />
                <p className={`text-2xl sm:text-3xl font-black ${alerte ? "text-red-600" : "text-gray-900"}`}>{valeur}</p>
                <p className="text-xs sm:text-sm text-gray-500 mt-1 leading-tight">{label}</p>
              </>
            )
            const style = `block rounded-3xl p-4 sm:p-5 ring-1 transition-all ${
              alerte ? "bg-red-50 ring-red-100" : "bg-gray-50 ring-gray-100"
            } ${href ? "hover:ring-gray-300 hover:shadow-sm" : ""}`
            return href ? (
              <Link key={label} href={href} className={style}>{contenu}</Link>
            ) : (
              <div key={label} className={style}>{contenu}</div>
            )
          })}
        </div>
      )}
    </div>
  )
}
