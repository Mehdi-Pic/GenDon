"use client"

import { Suspense, useEffect, useState } from "react"
import { useAuth, useUser } from "@clerk/nextjs"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { MessageCircle, X } from "lucide-react"
import { dateCourte, vignette } from "../lib/annonces"
import ConversationMenu from "./ConversationMenu"
import ServiceIndisponible from "../components/ServiceIndisponible"

type Conversation = {
  id: number
  annonce_id: number | null
  annonce_titre: string
  annonce_image: string | null
  annonce_statut: "disponible" | "reservee" | "donnee" | "retiree"
  est_donneur: boolean
  interlocuteur: string
  dernier_message: string | null
  dernier_message_a_moi: boolean
  dernier_message_at: string
  created_at: string
  non_lus: number
}

const ETIQUETTES: Record<string, { texte: string; classe: string } | undefined> = {
  reservee: { texte: "Réservé", classe: "bg-amber-50 text-amber-700" },
  donnee: { texte: "Donné", classe: "bg-green-50 text-green-700" },
  retiree: { texte: "Annonce retirée", classe: "bg-gray-100 text-gray-500" },
}

function ListeMessages() {
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  // ?annonce=12 : seulement les conversations de cette annonce (lien depuis Mes annonces)
  const filtreAnnonce = Number(useSearchParams().get("annonce")) || null
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [indisponible, setIndisponible] = useState(false)
  const [maintenant, setMaintenant] = useState(() => Date.now())

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace("/")
  }, [isLoaded, isSignedIn, router])

  // Chargement puis rafraîchissement toutes les 15 s tant que l'onglet est visible
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    let actif = true
    let dejaCharge = false
    async function charger() {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error("serveur")
        const data = await res.json()
        if (actif) {
          setConversations(Array.isArray(data) ? data : [])
          setMaintenant(Date.now())
          setIndisponible(false)
          dejaCharge = true
        }
      } catch {
        // Liste déjà affichée : on la garde, le prochain rafraîchissement réessaiera
        if (actif && !dejaCharge) setIndisponible(true)
      } finally {
        if (actif) setLoading(false)
      }
    }
    const premier = setTimeout(charger, 0)
    const intervalle = setInterval(() => {
      if (document.visibilityState === "visible") charger()
    }, 15000)
    const auRetour = () => { if (document.visibilityState === "visible") charger() }
    document.addEventListener("visibilitychange", auRetour)
    return () => {
      actif = false
      clearTimeout(premier)
      clearInterval(intervalle)
      document.removeEventListener("visibilitychange", auRetour)
    }
  }, [isLoaded, isSignedIn, getToken])

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-12">
          <p className="text-gray-400">Chargement...</p>
        </div>
      </main>
    )
  }

  if (indisponible) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
          <ServiceIndisponible />
        </div>
      </main>
    )
  }

  const affichees = filtreAnnonce ? conversations.filter((c) => c.annonce_id === filtreAnnonce) : conversations

  return (
    <main>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="text-2xl font-black text-gray-900 mb-6">Messages</h1>
        {filtreAnnonce && (
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm text-gray-500 truncate">
              Personnes intéressées par «&nbsp;{affichees[0]?.annonce_titre ?? "cette annonce"}&nbsp;»
            </span>
            <Link
              href="/messages"
              className="ml-auto shrink-0 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 border border-gray-200 hover:border-gray-400 px-3 py-1.5 rounded-full transition-colors"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
              Tout afficher
            </Link>
          </div>
        )}
        {affichees.length === 0 ? (
          <div className="text-center py-24">
            <MessageCircle className="w-10 h-10 text-gray-200 mx-auto mb-4" />
            <p className="text-gray-400 mb-4">
              {filtreAnnonce ? "Personne n'a encore écrit à propos de cette annonce." : "Aucune conversation pour le moment."}
            </p>
            <Link href="/annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
              Parcourir les dons
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {affichees.map((c) => {
              const etiquette = ETIQUETTES[c.annonce_statut]
              return (
                <div
                  key={c.id}
                  className="flex items-center gap-2 bg-white ring-1 ring-gray-100 rounded-2xl p-3 hover:ring-gray-200 hover:shadow-sm transition-all"
                >
                  <Link href={`/messages/${c.id}`} className="flex items-center gap-3 flex-1 min-w-0">
                    {c.annonce_image ? (
                      <img src={vignette(c.annonce_image, 200)} alt="" className="w-14 h-14 object-cover rounded-xl shrink-0" />
                    ) : (
                      <div className="w-14 h-14 bg-gray-100 rounded-xl shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-gray-900 text-sm truncate">{c.interlocuteur}</p>
                        <span className="text-xs text-gray-300 shrink-0">·</span>
                        <p className="text-xs text-gray-400 truncate">{c.annonce_titre}</p>
                        <span className={`text-xs shrink-0 ml-auto ${c.non_lus > 0 ? "text-green-600 font-semibold" : "text-gray-400"}`}>
                          {dateCourte(c.dernier_message_at, maintenant)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <p className={`text-sm truncate ${c.non_lus > 0 ? "text-gray-900 font-medium" : "text-gray-500"}`}>
                          {c.dernier_message
                            ? `${c.dernier_message_a_moi ? "Vous : " : ""}${c.dernier_message}`
                            : c.est_donneur ? "Nouvelle personne intéressée" : "Nouvelle conversation"}
                        </p>
                        {etiquette && (
                          <span className={`shrink-0 ml-auto text-[11px] font-medium px-2 py-0.5 rounded-full ${etiquette.classe}`}>
                            {etiquette.texte}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                  {c.non_lus > 0 && (
                    <span className="shrink-0 bg-green-600 text-white text-xs font-bold rounded-full min-w-5 h-5 px-1.5 flex items-center justify-center">
                      {c.non_lus}
                    </span>
                  )}
                  <ConversationMenu
                    conversationId={c.id}
                    onDeleted={() => setConversations((prev) => prev.filter((x) => x.id !== c.id))}
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}

// useSearchParams impose une frontière Suspense
export default function Messages() {
  return (
    <Suspense fallback={null}>
      <ListeMessages />
    </Suspense>
  )
}
