"use client"

import { useEffect, useState } from "react"
import { useAuth, SignInButton } from "@clerk/nextjs"
import Link from "next/link"
import { Bell, BellRing } from "lucide-react"

type Criteres = { recherche?: string; categorie?: string; quartier?: string }
type Alerte = { recherche: string | null; categorie: string | null; quartier: string | null }

// Même règle que le serveur pour reconnaître une alerte déjà enregistrée
function normaliser(texte?: string | null): string {
  return (texte ?? "").split(/\s+/).filter(Boolean).join(" ").toLowerCase()
}

function correspond(a: Alerte, c: Criteres): boolean {
  return normaliser(a.recherche) === normaliser(c.recherche)
    && (a.categorie ?? "") === (c.categorie ?? "")
    && (a.quartier ?? "") === (c.quartier ?? "")
}

// Enregistre la recherche affichée : un email signalera les prochains dons qui y correspondent
export default function AlerteBouton({ recherche, categorie, quartier }: Criteres) {
  const { isSignedIn, getToken } = useAuth()
  const [etat, setEtat] = useState<"idle" | "envoi" | "creee" | "erreur">("idle")
  const [erreur, setErreur] = useState("")
  const aucunCritere = !recherche && !categorie && !quartier

  // Alerte déjà enregistrée pour cette recherche : le bouton l'indique dès l'affichage
  useEffect(() => {
    if (!isSignedIn || aucunCritere) return
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alertes`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) return
        const alertes: Alerte[] = await res.json()
        if (actif && alertes.some((a) => correspond(a, { recherche, categorie, quartier }))) setEtat("creee")
      } catch {}
    })()
    return () => { actif = false }
  }, [isSignedIn, getToken, aucunCritere, recherche, categorie, quartier])

  if (aucunCritere) return null

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
        Alerte active
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
