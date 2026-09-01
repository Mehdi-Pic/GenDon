"use client"

import { useEffect, useMemo, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { ShieldCheck, Shield, Search, UserPlus, UserMinus } from "lucide-react"
import { useAdmin } from "../adminContext"

type Utilisateur = {
  id: string
  pseudo: string
  email: string | null
  image: string | null
  created_at: number
  nb_annonces: number
  role: string | null
  est_admin_principal: boolean
}

export default function AdminUtilisateurs() {
  const { getToken } = useAuth()
  const { role: monRole } = useAdmin()
  const [utilisateurs, setUtilisateurs] = useState<Utilisateur[]>([])
  const [loading, setLoading] = useState(true)
  const [enCours, setEnCours] = useState<string | null>(null)
  const [filtre, setFiltre] = useState("")

  useEffect(() => {
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/utilisateurs`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif && res.ok) setUtilisateurs(data)
      } catch {} finally {
        if (actif) setLoading(false)
      }
    })()
    return () => { actif = false }
  }, [getToken])

  async function changerRole(u: Utilisateur, nouveau: "moderateur" | "aucun") {
    const libelle = nouveau === "moderateur" ? `Promouvoir ${u.pseudo} modérateur ?` : `Retirer le rôle de modérateur à ${u.pseudo} ?`
    if (!confirm(libelle)) return
    setEnCours(u.id)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/utilisateurs/${u.id}/role`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ role: nouveau }),
      })
      if (!res.ok) {
        alert("La modification a échoué.")
        return
      }
      const data = await res.json()
      setUtilisateurs((prev) => prev.map((x) => (x.id === u.id ? { ...x, role: data.role } : x)))
    } finally {
      setEnCours(null)
    }
  }

  // Equipe d'abord (admins puis moderateurs), le reste par ordre alphabetique
  const visibles = useMemo(() => {
    const q = filtre.trim().toLowerCase()
    const rang = (u: Utilisateur) => (u.role === "admin" ? 0 : u.role === "moderateur" ? 1 : 2)
    return utilisateurs
      .filter((u) => !q || u.pseudo.toLowerCase().includes(q) || (u.email ?? "").toLowerCase().includes(q))
      .sort((a, b) => rang(a) - rang(b) || a.pseudo.localeCompare(b.pseudo, "fr"))
  }, [utilisateurs, filtre])

  const equipe = utilisateurs.filter((u) => u.role).length

  return (
    <div>
      <h1 className="text-xl sm:text-2xl font-black text-gray-900 mb-1">Utilisateurs</h1>
      <p className="text-sm text-gray-400 mb-5 sm:mb-6">
        {utilisateurs.length} compte{utilisateurs.length > 1 ? "s" : ""} · {equipe} dans l&apos;équipe
      </p>

      <div className="relative mb-5 sm:mb-6 sm:max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input
          type="text"
          value={filtre}
          onChange={(e) => setFiltre(e.target.value)}
          placeholder="Rechercher un pseudo ou un email..."
          aria-label="Rechercher un utilisateur"
          className="w-full pl-10 pr-4 py-2.5 bg-gray-100 border border-transparent rounded-full text-sm focus:outline-none focus:border-green-500 focus:bg-white transition-all"
        />
      </div>

      {loading ? (
        <p className="text-gray-400">Chargement...</p>
      ) : visibles.length === 0 ? (
        <p className="text-gray-400 py-12 text-center">Aucun compte ne correspond à « {filtre} ».</p>
      ) : (
        <div className="flex flex-col gap-3">
          {visibles.map((u) => (
            <div key={u.id} className="flex items-center gap-3 bg-white ring-1 ring-gray-100 rounded-2xl p-2.5 sm:p-3">
              {u.image ? (
                <img src={u.image} alt="" className="w-10 h-10 rounded-full object-cover shrink-0" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-gray-100 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-bold text-gray-900 text-sm truncate">{u.pseudo}</p>
                  {u.role === "admin" && (
                    <span className="inline-flex items-center gap-1 text-xs bg-gray-900 text-white px-2 py-0.5 rounded-full"><ShieldCheck className="w-3 h-3" />Admin</span>
                  )}
                  {u.role === "moderateur" && (
                    <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full"><Shield className="w-3 h-3" />Modérateur</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 truncate">{u.email ?? "email inconnu"}</p>
                <p className="text-xs text-gray-400">
                  inscrit le {new Date(u.created_at).toLocaleDateString("fr-FR")} · {u.nb_annonces} annonce{u.nb_annonces > 1 ? "s" : ""}
                </p>
              </div>
              {monRole === "admin" && !u.est_admin_principal && (
                <div className="shrink-0">
                  {u.role === "moderateur" ? (
                    <button
                      onClick={() => changerRole(u, "aucun")}
                      disabled={enCours === u.id}
                      aria-label={`Retirer le rôle de modérateur à ${u.pseudo}`}
                      className="flex items-center gap-1.5 border border-red-100 hover:border-red-300 text-red-500 p-2 sm:px-3 sm:py-1.5 rounded-full text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      <UserMinus className="w-4 h-4 sm:w-3.5 sm:h-3.5" />
                      <span className="hidden sm:inline">Retirer modérateur</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => changerRole(u, "moderateur")}
                      disabled={enCours === u.id}
                      aria-label={`Promouvoir ${u.pseudo} modérateur`}
                      className="flex items-center gap-1.5 border border-gray-200 hover:border-gray-400 text-gray-600 p-2 sm:px-3 sm:py-1.5 rounded-full text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      <UserPlus className="w-4 h-4 sm:w-3.5 sm:h-3.5" />
                      <span className="hidden sm:inline">Promouvoir modérateur</span>
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
