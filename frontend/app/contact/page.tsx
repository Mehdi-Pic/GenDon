"use client"

import { useState } from "react"
import { useUser } from "@clerk/nextjs"
import { Mail, CheckCircle } from "lucide-react"

export default function Contact() {
  const { user, isLoaded } = useUser()
  const [nom, setNom] = useState("")
  const [email, setEmail] = useState("")
  const [sujet, setSujet] = useState("")
  const [message, setMessage] = useState("")
  const [etat, setEtat] = useState<"idle" | "envoi" | "succes">("idle")
  const [erreur, setErreur] = useState("")
  const [prerempli, setPrerempli] = useState(false)

  // Pré-remplit avec le compte connecté, une seule fois
  if (isLoaded && user && !prerempli) {
    setNom(user.username || user.firstName || "")
    setEmail(user.primaryEmailAddress?.emailAddress || "")
    setPrerempli(true)
  }

  async function envoyer(e: React.SyntheticEvent) {
    e.preventDefault()
    setErreur("")
    setEtat("envoi")
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nom, email, sujet, message }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(typeof data.detail === "string" ? data.detail : "L'envoi a échoué")
      }
      setEtat("succes")
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Une erreur est survenue")
      setEtat("idle")
    }
  }

  if (etat === "succes") {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Message envoyé</h1>
          <p className="text-gray-500">
            Merci, l&apos;équipe GenDon vous répondra à l&apos;adresse indiquée.
          </p>
        </div>
      </main>
    )
  }

  const valide = nom.trim() && email.trim() && sujet.trim().length >= 3 && message.trim().length >= 10

  return (
    <main>
      <div className="max-w-2xl mx-auto px-6 py-12">
        <div className="flex items-center gap-2 mb-2">
          <Mail className="w-5 h-5 text-green-600" />
          <h1 className="text-2xl font-black text-gray-900">Nous contacter</h1>
        </div>
        <p className="text-gray-500 text-sm mb-8">
          Une question, un problème, une suggestion ? Écrivez-nous, l&apos;équipe vous répondra par email.
        </p>

        <form onSubmit={envoyer} className="flex flex-col gap-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Votre nom</label>
              <input
                type="text"
                value={nom}
                maxLength={80}
                onChange={(e) => setNom(e.target.value)}
                className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:border-green-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Votre email</label>
              <input
                type="email"
                value={email}
                maxLength={120}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="pour vous répondre"
                className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Sujet</label>
            <input
              type="text"
              value={sujet}
              maxLength={120}
              onChange={(e) => setSujet(e.target.value)}
              placeholder="Ex : problème avec une annonce"
              className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
            <textarea
              value={message}
              maxLength={2000}
              rows={6}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Décrivez votre demande..."
              className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500 resize-none"
            />
            <p className="text-xs text-gray-400 mt-1">{message.length}/2000 caractères</p>
          </div>

          {erreur && <p className="text-red-500 text-sm">{erreur}</p>}

          <button
            type="submit"
            disabled={etat === "envoi" || !valide}
            className="w-full bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 disabled:bg-gray-300 disabled:shadow-none text-white font-semibold py-4 rounded-2xl transition-all"
          >
            {etat === "envoi" ? "Envoi en cours..." : "Envoyer le message"}
          </button>
        </form>
      </div>
    </main>
  )
}
