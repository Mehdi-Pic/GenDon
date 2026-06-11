"use client"

import { useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { SignInButton } from "@clerk/nextjs"
import { Mail, X } from "lucide-react"

export default function ContactButton({ annonceId, titreDon }: { annonceId: number; titreDon: string }) {
  const { isSignedIn, getToken } = useAuth()
  const [ouvert, setOuvert] = useState(false)
  const [message, setMessage] = useState("")
  const [etat, setEtat] = useState<"idle" | "envoi" | "succes" | "erreur">("idle")
  const [erreur, setErreur] = useState("")

  async function envoyer() {
    if (!message.trim()) return
    setEtat("envoi")
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${annonceId}/contact`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: message.trim() }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || "Erreur lors de l'envoi")
      }
      setEtat("succes")
    } catch (e: unknown) {
      setErreur(e instanceof Error ? e.message : "Erreur inconnue")
      setEtat("erreur")
    }
  }

  function fermer() {
    setOuvert(false)
    setMessage("")
    setEtat("idle")
    setErreur("")
  }

  if (!isSignedIn) {
    return (
      <SignInButton mode="modal">
        <button className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white py-3 rounded-full font-semibold transition-all text-base">
          <Mail className="w-5 h-5" />
          Contacter le donneur
        </button>
      </SignInButton>
    )
  }

  return (
    <>
      <button
        onClick={() => setOuvert(true)}
        className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white py-3 rounded-full font-semibold transition-all text-base"
      >
        <Mail className="w-5 h-5" />
        Contacter le donneur
      </button>

      {ouvert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-3xl shadow-2xl ring-1 ring-gray-100 w-full max-w-md p-6 relative">
            <button
              onClick={fermer}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-700 transition-colors"
              aria-label="Fermer"
            >
              <X className="w-5 h-5" />
            </button>

            {etat === "succes" ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Mail className="w-8 h-8 text-green-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Message envoyé !</h2>
                <p className="text-gray-500 text-sm">Le donneur a reçu votre message. Il pourra vous répondre directement par email.</p>
                <button
                  onClick={fermer}
                  className="mt-6 bg-gray-900 hover:bg-gray-700 text-white px-6 py-2.5 rounded-full text-sm font-semibold transition-colors"
                >
                  Fermer
                </button>
              </div>
            ) : (
              <>
                <h2 className="text-lg font-bold text-gray-900 mb-1">Contacter le donneur</h2>
                <p className="text-sm text-gray-500 mb-4">À propos de : <span className="font-medium text-gray-700">{titreDon}</span></p>

                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Bonjour, je suis intéressé(e) par votre don. Est-il toujours disponible ?"
                  rows={5}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 resize-none"
                />

                {etat === "erreur" && (
                  <p className="text-sm text-red-600 mt-2">{erreur}</p>
                )}

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={fermer}
                    className="flex-1 py-2.5 border border-gray-200 rounded-full text-sm font-medium text-gray-600 hover:border-gray-400 transition-colors"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={envoyer}
                    disabled={etat === "envoi" || !message.trim()}
                    className="flex-1 py-2.5 bg-green-600 hover:bg-green-500 disabled:bg-gray-300 text-white rounded-full text-sm font-semibold transition-colors"
                  >
                    {etat === "envoi" ? "Envoi…" : "Envoyer"}
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
