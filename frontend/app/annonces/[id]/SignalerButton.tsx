"use client"

import { useState } from "react"
import { Flag, X, CheckCircle } from "lucide-react"
import { useAuth, useClerk } from "@clerk/nextjs"

export default function SignalerButton({ annonceId }: { annonceId: number }) {
  const { isSignedIn, getToken } = useAuth()
  const clerk = useClerk()
  const [ouvert, setOuvert] = useState(false)
  const [raison, setRaison] = useState("")
  const [etat, setEtat] = useState<"idle" | "envoi" | "succes" | "erreur">("idle")

  function ouvrir() {
    if (!isSignedIn) {
      clerk.openSignIn()
      return
    }
    setOuvert(true)
  }

  async function envoyer() {
    if (raison.trim().length < 3) return
    setEtat("envoi")
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${annonceId}/signaler`, {
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

  function fermer() {
    setOuvert(false)
    setRaison("")
    setEtat("idle")
  }

  return (
    <>
      <button
        onClick={ouvrir}
        className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-500 transition-colors"
      >
        <Flag className="w-3.5 h-3.5" aria-hidden="true" />
        Signaler cette annonce
      </button>

      {ouvert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={fermer}>
          <div className="bg-white rounded-3xl shadow-2xl ring-1 ring-gray-100 w-full max-w-md p-6 relative text-left" onClick={(e) => e.stopPropagation()}>
            <button onClick={fermer} className="absolute top-4 right-4 text-gray-400 hover:text-gray-700 transition-colors" aria-label="Fermer">
              <X className="w-5 h-5" />
            </button>

            {etat === "succes" ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Signalement envoyé</h2>
                <p className="text-gray-500 text-sm">Merci, l&apos;équipe va examiner cette annonce.</p>
                <button onClick={fermer} className="mt-6 bg-gray-900 hover:bg-gray-700 text-white px-6 py-2.5 rounded-full text-sm font-semibold transition-colors">
                  Fermer
                </button>
              </div>
            ) : (
              <>
                <h2 className="text-lg font-bold text-gray-900 mb-1">Signaler cette annonce</h2>
                <p className="text-sm text-gray-500 mb-4">Expliquez en quelques mots ce qui pose problème.</p>
                <textarea
                  value={raison}
                  onChange={(e) => setRaison(e.target.value)}
                  maxLength={500}
                  placeholder="Contenu inapproprié, arnaque, objet interdit..."
                  rows={4}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-red-400 focus:ring-2 focus:ring-red-100 resize-none"
                />
                {etat === "erreur" && <p className="text-sm text-red-600 mt-2">L&apos;envoi a échoué, réessayez.</p>}
                <div className="flex gap-3 mt-4">
                  <button onClick={fermer} className="flex-1 py-2.5 border border-gray-200 rounded-full text-sm font-medium text-gray-600 hover:border-gray-400 transition-colors">
                    Annuler
                  </button>
                  <button
                    onClick={envoyer}
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
