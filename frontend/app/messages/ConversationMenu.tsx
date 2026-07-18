"use client"

import { useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { MoreVertical, Flag, LogOut, X, CheckCircle } from "lucide-react"

export default function ConversationMenu({
  conversationId,
  onDeleted,
}: {
  conversationId: number
  onDeleted: () => void
}) {
  const { getToken } = useAuth()
  const [ouvert, setOuvert] = useState(false)
  const [modale, setModale] = useState<"signaler" | null>(null)
  const [raison, setRaison] = useState("")
  const [etat, setEtat] = useState<"idle" | "envoi" | "succes" | "erreur">("idle")

  function toggle(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    setOuvert((v) => !v)
  }

  async function supprimer(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    setOuvert(false)
    if (!confirm("Quitter cette conversation ? Elle disparaîtra de votre liste et votre interlocuteur en sera informé.")) return
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${conversationId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      onDeleted()
    } catch {
      alert("L'opération a échoué.")
    }
  }

  function ouvrirSignaler(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    setOuvert(false)
    setModale("signaler")
    setRaison("")
    setEtat("idle")
  }

  async function envoyerSignalement() {
    if (raison.trim().length < 3) return
    setEtat("envoi")
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations/${conversationId}/signaler`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ raison: raison.trim() }),
      })
      if (!res.ok) throw new Error()
      setEtat("succes")
    } catch {
      setEtat("erreur")
    }
  }

  return (
    <>
      <div className="relative shrink-0">
        <button
          onClick={toggle}
          aria-label="Options de la conversation"
          className="p-2 text-gray-400 hover:text-gray-900 rounded-full hover:bg-gray-100 transition-colors"
        >
          <MoreVertical className="w-5 h-5" />
        </button>

        {ouvert && (
          <>
            <div className="fixed inset-0 z-30" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOuvert(false) }} />
            <div className="absolute right-0 top-full mt-1 z-40 bg-white ring-1 ring-gray-100 rounded-2xl shadow-xl py-1.5 w-max overflow-hidden">
              <button
                onClick={ouvrirSignaler}
                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors text-left whitespace-nowrap"
              >
                <Flag className="w-4 h-4 text-gray-500 shrink-0" />
                <span>Signaler<span className="hidden sm:inline"> la conversation</span></span>
              </button>
              <button
                onClick={supprimer}
                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors text-left whitespace-nowrap"
              >
                <LogOut className="w-4 h-4 shrink-0" />
                <span>Quitter<span className="hidden sm:inline"> la conversation</span></span>
              </button>
            </div>
          </>
        )}
      </div>

      {modale === "signaler" && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setModale(null) }}
        >
          <div className="bg-white rounded-3xl shadow-2xl ring-1 ring-gray-100 w-full max-w-md p-6 relative text-left" onClick={(e) => { e.preventDefault(); e.stopPropagation() }}>
            <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setModale(null) }} className="absolute top-4 right-4 text-gray-400 hover:text-gray-700 transition-colors" aria-label="Fermer">
              <X className="w-5 h-5" />
            </button>

            {etat === "succes" ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Signalement envoyé</h2>
                <p className="text-gray-500 text-sm">Merci, l&apos;équipe va examiner cette conversation.</p>
                <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setModale(null) }} className="mt-6 bg-gray-900 hover:bg-gray-700 text-white px-6 py-2.5 rounded-full text-sm font-semibold transition-colors">
                  Fermer
                </button>
              </div>
            ) : (
              <>
                <h2 className="text-lg font-bold text-gray-900 mb-1">Signaler cette conversation</h2>
                <p className="text-sm text-gray-500 mb-4">Expliquez en quelques mots ce qui pose problème.</p>
                <textarea
                  value={raison}
                  onChange={(e) => setRaison(e.target.value)}
                  maxLength={500}
                  placeholder="Propos déplacés, arnaque, spam..."
                  rows={4}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-400 focus:ring-2 focus:ring-red-100 resize-none"
                />
                {etat === "erreur" && <p className="text-sm text-red-600 mt-2">L&apos;envoi a échoué, réessayez.</p>}
                <div className="flex gap-3 mt-4">
                  <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); setModale(null) }} className="flex-1 py-2.5 border border-gray-200 rounded-full text-sm font-medium text-gray-600 hover:border-gray-400 transition-colors">
                    Annuler
                  </button>
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); envoyerSignalement() }}
                    disabled={etat === "envoi" || raison.trim().length < 3}
                    className="flex-1 py-2.5 bg-red-500 hover:bg-red-400 disabled:bg-gray-300 text-white rounded-full text-sm font-semibold transition-colors"
                  >
                    {etat === "envoi" ? "Envoi…" : "Signaler"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
