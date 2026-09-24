"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { CheckCircle, XCircle } from "lucide-react"

function Desabonnement() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const [etat, setEtat] = useState<"chargement" | "succes" | "erreur">("chargement")

  useEffect(() => {
    if (!token) return
    let actif = true
    ;(async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/newsletter/desabonnement`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        })
        if (actif) setEtat(res.ok ? "succes" : "erreur")
      } catch {
        if (actif) setEtat("erreur")
      }
    })()
    return () => { actif = false }
  }, [token])

  // Lien sans jeton : erreur d'emblée
  const etatAffiche = token ? etat : "erreur"

  if (etatAffiche === "chargement") {
    return <p className="text-gray-400">Désabonnement en cours...</p>
  }

  if (etatAffiche === "erreur") {
    return (
      <>
        <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <XCircle className="w-8 h-8 text-red-500" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Lien invalide</h1>
        <p className="text-gray-500 mb-8">
          Ce lien de désabonnement n&apos;est pas valide. Vous pouvez nous écrire si le problème persiste.
        </p>
        <Link href="/contact" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
          Nous contacter
        </Link>
      </>
    )
  }

  return (
    <>
      <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
        <CheckCircle className="w-8 h-8 text-green-600" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Vous êtes désabonné</h1>
      <p className="text-gray-500 mb-8">
        Vous ne recevrez plus l&apos;email hebdomadaire des derniers dons. Votre compte et vos annonces
        ne sont pas affectés. Vous pourrez vous réabonner à tout moment depuis Mon profil.
      </p>
      <Link href="/annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
        Voir les dons
      </Link>
    </>
  )
}

export default function PageDesabonnement() {
  return (
    <main>
      <div className="max-w-2xl mx-auto px-6 py-24 text-center">
        <Suspense fallback={<p className="text-gray-400">Chargement...</p>}>
          <Desabonnement />
        </Suspense>
      </div>
    </main>
  )
}
