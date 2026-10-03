"use client"

import { use, useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { ArrowLeft, Ban, RotateCcw } from "lucide-react"
import { libelleJour, memeJour } from "../../../lib/annonces"
import { changerSuspension } from "../../suspension"

type Participant = { id: string; pseudo: string; suspendu: boolean }
type Message = { id: number; auteur: "donneur" | "demandeur" | "systeme"; contenu: string; created_at: string }
type Fil = {
  id: number
  annonce_id: number | null
  annonce_titre: string
  donneur: Participant
  demandeur: Participant
  messages: Message[]
}

// Lecture d'une conversation signalée (accès journalisé côté serveur)
export default function AdminConversation({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { getToken } = useAuth()
  const [fil, setFil] = useState<Fil | null>(null)
  const [etat, setEtat] = useState<"chargement" | "ok" | "introuvable">("chargement")

  useEffect(() => {
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/conversations/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!actif) return
        if (!res.ok) {
          setEtat("introuvable")
          return
        }
        setFil(await res.json())
        setEtat("ok")
      } catch {
        if (actif) setEtat("introuvable")
      }
    })()
    return () => { actif = false }
  }, [id, getToken])

  // L'état vient du serveur : il reste juste quand on revient sur la page plus tard
  async function basculer(p: Participant) {
    if (!fil || !(await changerSuspension(getToken, p.id, p.pseudo, !p.suspendu))) return
    const maj = (x: Participant) => (x.id === p.id ? { ...x, suspendu: !p.suspendu } : x)
    setFil({ ...fil, donneur: maj(fil.donneur), demandeur: maj(fil.demandeur) })
  }

  if (etat === "chargement") return <p className="text-gray-400">Chargement...</p>
  if (etat === "introuvable" || !fil) {
    return (
      <div>
        <p className="text-gray-500 mb-4">Conversation introuvable, supprimée ou non signalée.</p>
        <Link href="/admin/signalements" className="text-sm text-green-600 hover:underline">Retour aux signalements</Link>
      </div>
    )
  }

  const participants = [
    { role: "Donneur", ...fil.donneur },
    { role: "Demandeur", ...fil.demandeur },
  ]

  return (
    <div>
      <Link href="/admin/signalements" className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-900 text-sm mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Signalements
      </Link>
      <h1 className="text-xl sm:text-2xl font-black text-gray-900 mb-1">Conversation signalée</h1>
      <p className="text-sm text-gray-400 mb-5">
        À propos de{" "}
        {fil.annonce_id ? (
          <Link href={`/annonces/${fil.annonce_id}`} target="_blank" className="text-gray-600 hover:underline">{fil.annonce_titre}</Link>
        ) : (
          <span className="text-gray-600">{fil.annonce_titre || "une annonce retirée"}</span>
        )}
        . Votre consultation est inscrite au journal de modération.
      </p>

      <div className="flex flex-wrap gap-2 mb-6">
        {participants.map((p) => (
          <div key={p.id} className="flex items-center gap-3 bg-gray-50 rounded-2xl px-4 py-2.5">
            <div>
              <p className="text-xs text-gray-400">{p.role}</p>
              <p className="text-sm font-semibold text-gray-900">{p.pseudo}</p>
            </div>
            {p.suspendu && (
              <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">Suspendu</span>
            )}
            <button
              onClick={() => basculer(p)}
              className={`flex items-center gap-1.5 border px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                p.suspendu ? "border-gray-200 hover:border-gray-400 text-gray-600" : "border-red-100 hover:border-red-300 text-red-500"
              }`}
            >
              {p.suspendu ? <RotateCcw className="w-3.5 h-3.5" /> : <Ban className="w-3.5 h-3.5" />}
              {p.suspendu ? "Réactiver" : "Suspendre"}
            </button>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2 bg-white ring-1 ring-gray-100 rounded-2xl p-4">
        {fil.messages.length === 0 && <p className="text-sm text-gray-400 text-center py-6">Aucun message.</p>}
        {fil.messages.map((m, i) => (
          <div key={m.id} className="flex flex-col gap-2">
            {(i === 0 || !memeJour(fil.messages[i - 1].created_at, m.created_at)) && (
              <p className="text-center text-[11px] font-medium text-gray-400 first-letter:uppercase my-1">{libelleJour(m.created_at)}</p>
            )}
            {m.auteur === "systeme" ? (
              <p className="text-center text-xs text-gray-400">{m.contenu}</p>
            ) : (
              <div className={`flex ${m.auteur === "donneur" ? "justify-start" : "justify-end"}`}>
                <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm break-words ${m.auteur === "donneur" ? "bg-gray-100 text-gray-900" : "bg-green-50 text-gray-900"}`}>
                  <span className="block text-[11px] font-semibold text-gray-500 mb-0.5">
                    {m.auteur === "donneur" ? fil.donneur.pseudo : fil.demandeur.pseudo}
                    {" · "}
                    {new Date(m.created_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span className="whitespace-pre-wrap">{m.contenu}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
