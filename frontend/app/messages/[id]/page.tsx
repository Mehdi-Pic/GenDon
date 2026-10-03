"use client"

import { useEffect, useRef, useState, useCallback, use } from "react"
import { useAuth, useUser } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Send, HandHeart, Clock, Undo2, Info } from "lucide-react"
import { libelleJour, memeJour, vignette } from "../../lib/annonces"
import ConversationMenu from "../ConversationMenu"
import ServiceIndisponible from "../../components/ServiceIndisponible"

type Message = { id: number; contenu: string; created_at: string; a_moi: boolean; systeme?: boolean }
type Fil = {
  id: number
  annonce_id: number | null
  annonce_titre: string
  annonce_image: string | null
  annonce_statut: "disponible" | "reservee" | "donnee" | "retiree"
  reservee_ici: boolean
  est_donneur: boolean
  interlocuteur: string
  autre_present: boolean
  dernier_lu: boolean
  messages: Message[]
}

// Bandeau d'état de l'objet, vu par chacun des deux participants
function bandeau(fil: Fil): string | null {
  switch (fil.annonce_statut) {
    case "retiree":
      return "Cette annonce n'est plus en ligne. Vous pouvez encore échanger pour finaliser la remise."
    case "donnee":
      return fil.est_donneur ? "Vous avez indiqué que l'objet a été donné." : "L'objet a été donné."
    case "reservee":
      if (fil.est_donneur) return fil.reservee_ici ? `Objet réservé pour ${fil.interlocuteur}.` : "Objet réservé pour une autre personne."
      return fil.reservee_ici ? "L'objet vous est réservé. Convenez ensemble de la remise." : "Objet réservé pour une autre personne."
    default:
      return null
  }
}

export default function Conversation({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  const [fil, setFil] = useState<Fil | null>(null)
  const [chargement, setChargement] = useState(true)
  const [introuvable, setIntrouvable] = useState(false)
  const [indisponible, setIndisponible] = useState(false)
  const dejaCharge = useRef(false)
  const [texte, setTexte] = useState("")
  const [envoi, setEnvoi] = useState(false)
  const [action, setAction] = useState(false)
  const basRef = useRef<HTMLDivElement>(null)
  const zoneTexte = useRef<HTMLTextAreaElement>(null)
  const nbMessages = useRef(0)

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace("/")
  }, [isLoaded, isSignedIn, router])

  const charger = useCallback(async (marquerLu: boolean) => {
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${id}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403 || res.status === 404) {
        setIntrouvable(true)
        return
      }
      if (!res.ok) throw new Error("serveur")
      const data: Fil = await res.json()
      dejaCharge.current = true
      setIndisponible(false)
      setFil(data)
      if (marquerLu) {
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${id}/lu`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {})
      }
    } catch {
      // Déjà affichée : on garde la conversation, le prochain rafraîchissement réessaiera
      if (!dejaCharge.current) setIndisponible(true)
    } finally {
      setChargement(false)
    }
  }, [id, getToken])

  // Chargement initial + polling toutes les 5 s. Les messages ne sont marqués lus que si
  // l'onglet est visible : sinon un onglet oublié en arrière-plan empêcherait l'email de notification.
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    const visible = () => document.visibilityState === "visible"
    // Premier chargement lancé de façon asynchrone, comme les suivants (pas de setState synchrone)
    const premier = setTimeout(() => charger(visible()), 0)
    const intervalle = setInterval(() => charger(visible()), 5000)
    const auRetour = () => { if (visible()) charger(true) }
    document.addEventListener("visibilitychange", auRetour)
    return () => {
      clearTimeout(premier)
      clearInterval(intervalle)
      document.removeEventListener("visibilitychange", auRetour)
    }
  }, [isLoaded, isSignedIn, charger])

  // Défiler en bas quand de nouveaux messages arrivent
  useEffect(() => {
    if (fil && fil.messages.length !== nbMessages.current) {
      nbMessages.current = fil.messages.length
      basRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [fil])

  // Défile jusqu'au spinner quand l'envoi démarre
  useEffect(() => {
    if (envoi) basRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [envoi])

  // La zone de saisie s'agrandit avec le texte (jusqu'à max-h-32), puis défile
  useEffect(() => {
    const el = zoneTexte.current
    if (!el) return
    el.style.height = "auto"
    // scrollHeight exclut la bordure : sans elle, il manque 2 px et une barre de défilement apparaît
    el.style.height = `${el.scrollHeight + el.offsetHeight - el.clientHeight}px`
  }, [texte])

  // Actions du donneur sur l'objet : réserver pour cette personne, annuler, déclarer donné
  async function agir(chemin: "reserver" | "liberer" | "donne") {
    if (!fil?.annonce_id || action) return
    if (chemin === "donne" && !confirm("Confirmer que l'objet a été donné ? L'annonce sera retirée du site sous 3 jours.")) return
    setAction(true)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${fil.annonce_id}/${chemin}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: chemin === "reserver" ? JSON.stringify({ conversation_id: fil.id }) : undefined,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        alert(data.detail || "L'opération a échoué. Réessayez.")
        return
      }
      await charger(false)
    } catch {
      alert("L'opération a échoué. Réessayez.")
    } finally {
      setAction(false)
    }
  }

  async function envoyer(e: React.SyntheticEvent) {
    e.preventDefault()
    const contenu = texte.trim()
    if (!contenu || envoi) return
    setEnvoi(true)
    setTexte("")
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ contenu }),
      })
      if (res.ok) {
        // On recharge depuis le serveur : le message s'affiche une seule fois, pas de doublon
        await charger(false)
      } else {
        setTexte(contenu) // échec : on restaure le texte
      }
    } catch {
      setTexte(contenu)
    } finally {
      setEnvoi(false)
    }
  }

  if (!isLoaded || chargement) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-12">
          <p className="text-gray-400">Chargement...</p>
        </div>
      </main>
    )
  }

  if (indisponible && !fil) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-12">
          <ServiceIndisponible />
        </div>
      </main>
    )
  }

  if (introuvable || !fil) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Conversation introuvable</h1>
          <Link href="/messages" className="mt-4 inline-block bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
            Retour aux messages
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 flex flex-col" style={{ minHeight: "calc(100vh - 200px)" }}>
        <div className="flex items-center gap-3 pb-4 border-b border-gray-100">
          <Link href="/messages" className="text-gray-400 hover:text-gray-900 transition-colors shrink-0" aria-label="Retour">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Link href={fil.annonce_id ? `/annonces/${fil.annonce_id}` : "/messages"} className="flex items-center gap-3 min-w-0 group">
            {fil.annonce_image ? (
              <img src={vignette(fil.annonce_image, 200)} alt="" className="w-10 h-10 object-cover rounded-lg shrink-0" />
            ) : (
              <div className="w-10 h-10 bg-gray-100 rounded-lg shrink-0" />
            )}
            <div className="min-w-0">
              <p className="font-bold text-gray-900 text-sm truncate">{fil.interlocuteur}</p>
              <p className="text-xs text-gray-400 truncate group-hover:text-gray-600 transition-colors">{fil.annonce_titre}</p>
            </div>
          </Link>
          <div className="ml-auto">
            <ConversationMenu conversationId={fil.id} onDeleted={() => router.push("/messages")} />
          </div>
        </div>

        {(bandeau(fil) || (fil.est_donneur && fil.autre_present && (fil.annonce_statut === "disponible" || fil.annonce_statut === "reservee"))) && (
          <div className="flex flex-wrap items-center gap-2 py-3 border-b border-gray-100">
            {bandeau(fil) && (
              <p className={`flex items-start gap-2 text-sm flex-1 min-w-[12rem] ${fil.annonce_statut === "reservee" ? "text-amber-700" : "text-gray-500"}`}>
                <Info className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
                {bandeau(fil)}
              </p>
            )}
            {fil.est_donneur && fil.autre_present && (fil.annonce_statut === "disponible" || fil.annonce_statut === "reservee") && (
              <div className="flex flex-wrap gap-2 ml-auto">
                {fil.reservee_ici ? (
                  <button
                    onClick={() => agir("liberer")}
                    disabled={action}
                    className="flex items-center gap-1.5 border border-gray-200 hover:border-gray-400 disabled:opacity-60 text-gray-600 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
                  >
                    <Undo2 className="w-3.5 h-3.5" aria-hidden="true" />
                    Annuler la réservation
                  </button>
                ) : (
                  <button
                    onClick={() => agir("reserver")}
                    disabled={action}
                    title="Promettre l'objet à cette personne : les autres demandeurs sont prévenus"
                    className="flex items-center gap-1.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-60 text-white px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
                  >
                    <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                    Réserver pour {fil.interlocuteur}
                  </button>
                )}
                <button
                  onClick={() => agir("donne")}
                  disabled={action}
                  className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-60 text-white px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
                >
                  <HandHeart className="w-3.5 h-3.5" aria-hidden="true" />
                  Objet donné
                </button>
              </div>
            )}
          </div>
        )}

        <div className="flex-1 flex flex-col gap-2 py-4 overflow-y-auto">
          {fil.messages.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-8">
              Écrivez le premier message à {fil.interlocuteur}.
            </p>
          ) : (
            fil.messages.map((m, i) => {
              const precedent = fil.messages[i - 1]
              const separateur = !precedent || !memeJour(precedent.created_at, m.created_at) ? (
                <div className="flex items-center gap-3 my-2" aria-hidden="true">
                  <span className="flex-1 border-t border-gray-100" />
                  <span className="text-[11px] font-medium text-gray-400 first-letter:uppercase">{libelleJour(m.created_at)}</span>
                  <span className="flex-1 border-t border-gray-100" />
                </div>
              ) : null
              const dernierAMoi = m.a_moi && !fil.messages.slice(i + 1).some((x) => x.a_moi)
              const bulle = m.systeme ? (
                <div key={m.id} className="flex justify-center my-1">
                  <span className="text-xs text-gray-400 bg-gray-50 rounded-full px-3 py-1">{m.contenu}</span>
                </div>
              ) : (
                <div key={m.id} className={`flex ${m.a_moi ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed break-words ${
                      m.a_moi ? "bg-green-600 text-white rounded-br-md" : "bg-gray-100 text-gray-900 rounded-bl-md"
                    }`}
                  >
                    {m.contenu}
                    <span className={`block text-[10px] mt-1 ${m.a_moi ? "text-green-100" : "text-gray-400"}`}>
                      {new Date(m.created_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
                      {dernierAMoi && fil.dernier_lu ? " · Vu" : ""}
                    </span>
                  </div>
                </div>
              )
              return (
                <div key={m.id} className="flex flex-col gap-2">
                  {separateur}
                  {bulle}
                </div>
              )
            })
          )}
          {envoi && (
            <div className="flex justify-end">
              <div className="bg-green-600/70 text-white rounded-2xl rounded-br-md px-4 py-3 flex items-center">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" aria-label="Envoi en cours">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
              </div>
            </div>
          )}
          <div ref={basRef} />
        </div>

        {fil.autre_present ? (
          <form onSubmit={envoyer} className="flex items-end gap-2 pt-3 border-t border-gray-100 sticky bottom-0 bg-white">
            <textarea
              ref={zoneTexte}
              value={texte}
              onChange={(e) => setTexte(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) envoyer(e) }}
              maxLength={2000}
              rows={1}
              placeholder="Votre message..."
              className="flex-1 border border-gray-200 rounded-2xl px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500 resize-none max-h-32 overflow-y-auto"
            />
            <button
              type="submit"
              disabled={envoi || !texte.trim()}
              className="shrink-0 bg-green-600 hover:bg-green-500 disabled:bg-gray-300 text-white rounded-full w-11 h-11 flex items-center justify-center transition-colors"
              aria-label="Envoyer"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        ) : (
          <div className="pt-3 border-t border-gray-100 text-center text-sm text-gray-400 py-3">
            {fil.interlocuteur} a quitté la conversation. Vous ne pouvez plus envoyer de message.
          </div>
        )}
      </div>
    </main>
  )
}
