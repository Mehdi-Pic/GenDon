"use client"

import { useEffect, useState } from "react"
import { useAuth, useUser } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { MessageCircle } from "lucide-react"
import { vignette } from "../lib/annonces"
import ConversationMenu from "./ConversationMenu"

type Conversation = {
  id: number
  annonce_id: number
  annonce_titre: string
  annonce_image: string | null
  interlocuteur: string
  dernier_message: string | null
  dernier_message_at: string
  created_at: string
  non_lus: number
}

export default function Messages() {
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace("/")
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif) setConversations(Array.isArray(data) ? data : [])
      } catch {
        if (actif) setConversations([])
      } finally {
        if (actif) setLoading(false)
      }
    })()
    return () => { actif = false }
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

  return (
    <main>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="text-2xl font-black text-gray-900 mb-6">Messages</h1>
        {conversations.length === 0 ? (
          <div className="text-center py-24">
            <MessageCircle className="w-10 h-10 text-gray-200 mx-auto mb-4" />
            <p className="text-gray-400 mb-4">Aucune conversation pour le moment.</p>
            <Link href="/annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
              Parcourir les dons
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {conversations.map((c) => (
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
                      <span className="text-xs text-gray-300 shrink-0 ml-auto">{new Date(c.created_at).toLocaleDateString("fr-FR")}</span>
                    </div>
                    <p className={`text-sm truncate mt-0.5 ${c.non_lus > 0 ? "text-gray-900 font-medium" : "text-gray-500"}`}>
                      {c.dernier_message ?? "Nouvelle conversation"}
                    </p>
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
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
