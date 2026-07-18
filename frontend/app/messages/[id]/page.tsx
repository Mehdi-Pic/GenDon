"use client"

import { useEffect, useRef, useState, useCallback, use } from "react"
import { useAuth, useUser } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Send } from "lucide-react"
import { vignette } from "../../lib/annonces"
import ConversationMenu from "../ConversationMenu"

type Message = { id: number; contenu: string; created_at: string; a_moi: boolean }
type Fil = {
  id: number
  annonce_id: number
  annonce_titre: string
  annonce_image: string | null
  interlocuteur: string
  messages: Message[]
}

export default function Conversation({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  const [fil, setFil] = useState<Fil | null>(null)
  const [chargement, setChargement] = useState(true)
  const [introuvable, setIntrouvable] = useState(false)
  const [texte, setTexte] = useState("")
  const [envoi, setEnvoi] = useState(false)
  const basRef = useRef<HTMLDivElement>(null)
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
      if (!res.ok) {
        setIntrouvable(true)
        return
      }
      const data: Fil = await res.json()
      setFil(data)
      if (marquerLu) {
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${id}/lu`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {})
      }
    } catch {
      setIntrouvable(true)
    } finally {
      setChargement(false)
    }
  }, [id, getToken])

  // Chargement initial + polling toutes les 5 s
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    charger(true)
    const intervalle = setInterval(() => charger(true), 5000)
    return () => clearInterval(intervalle)
  }, [isLoaded, isSignedIn, charger])

  // Défiler en bas quand de nouveaux messages arrivent
  useEffect(() => {
    if (fil && fil.messages.length !== nbMessages.current) {
      nbMessages.current = fil.messages.length
      basRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [fil])

  async function envoyer(e: React.SyntheticEvent) {
    e.preventDefault()
    const contenu = texte.trim()
    if (!contenu || envoi) return
    setEnvoi(true)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ contenu }),
      })
      if (res.ok) {
        const msg: Message = await res.json()
        setFil((prev) => (prev ? { ...prev, messages: [...prev.messages, msg] } : prev))
        setTexte("")
      }
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
          <Link href={`/annonces/${fil.annonce_id}`} className="flex items-center gap-3 min-w-0 group">
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

        <div className="flex-1 flex flex-col gap-2 py-4 overflow-y-auto">
          {fil.messages.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-8">
              Écrivez le premier message à {fil.interlocuteur}.
            </p>
          ) : (
            fil.messages.map((m) => (
              <div key={m.id} className={`flex ${m.a_moi ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed break-words ${
                    m.a_moi ? "bg-green-600 text-white rounded-br-md" : "bg-gray-100 text-gray-900 rounded-bl-md"
                  }`}
                >
                  {m.contenu}
                  <span className={`block text-[10px] mt-1 ${m.a_moi ? "text-green-100" : "text-gray-400"}`}>
                    {new Date(m.created_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
            ))
          )}
          <div ref={basRef} />
        </div>

        <form onSubmit={envoyer} className="flex items-end gap-2 pt-3 border-t border-gray-100 sticky bottom-0 bg-white">
          <textarea
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) envoyer(e) }}
            maxLength={2000}
            rows={1}
            placeholder="Votre message..."
            className="flex-1 border border-gray-200 rounded-2xl px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500 resize-none max-h-32"
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
      </div>
    </main>
  )
}
