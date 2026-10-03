"use client"

import { useState } from "react"
import { useAuth, SignInButton } from "@clerk/nextjs"
import Link from "next/link"
import { Bell, BellRing } from "lucide-react"

type Criteres = { recherche?: string; categorie?: string; quartier?: string }

// Enregistre la recherche affichée : un email signalera les prochains dons qui y correspondent
export default function AlerteBouton({ recherche, categorie, quartier }: Criteres) {
  const { isSignedIn, getToken } = useAuth()
  const [etat, setEtat] = useState<"idle" | "envoi" | "creee" | "erreur">("idle")
  const [erreur, setErreur] = useState("")

  if (!recherche && !categorie && !quartier) return null

  const classes =
    "flex items-center gap-1.5 text-sm border border-green-200 hover:border-green-500 text-green-700 px-4 py-2 rounded-full transition-colors disabled:opacity-60"

  if (!isSignedIn) {
    return (
      <SignInButton mode="modal">
        <button className={classes}>
          <Bell className="w-4 h-4" aria-hidden="true" />
          Créer une alerte
        </button>
      </SignInButton>
    )
  }

  if (etat === "creee") {
    return (
      <Link href="/profil" className="flex items-center gap-1.5 text-sm bg-green-50 text-green-700 px-4 py-2 rounded-full">
        <BellRing className="w-4 h-4" aria-hidden="true" />
        Alerte créée
      </Link>
    )
  }

  async function creer() {
    setEtat("envoi")
    setErreur("")
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alertes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ recherche: recherche || null, categorie: categorie || null, quartier: quartier || null }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(typeof data.detail === "string" ? data.detail : "La création a échoué")
      }
      setEtat("creee")
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "La création a échoué")
      setEtat("erreur")
    }
  }

  return (
    <div className="flex flex-col items-end">
      <button
        onClick={creer}
        disabled={etat === "envoi"}
        title="Recevoir un email quand un don correspondant est publié"
        className={classes}
      >
        <Bell className="w-4 h-4" aria-hidden="true" />
        Créer une alerte
      </button>
      {erreur && <p className="text-xs text-red-600 mt-1">{erreur}</p>}
    </div>
  )
}
