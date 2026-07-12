"use client"

import { useState } from "react"
import { useAuth, SignInButton } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import { Mail } from "lucide-react"

export default function ContactButton({ annonceId }: { annonceId: number; titreDon?: string }) {
  const { isSignedIn, getToken } = useAuth()
  const router = useRouter()
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState("")

  async function contacter() {
    setErreur("")
    setEnCours(true)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ annonce_id: annonceId }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || "Impossible de démarrer la conversation")
      }
      const data = await res.json()
      router.push(`/messages/${data.id}`)
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Une erreur est survenue")
      setEnCours(false)
    }
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
        onClick={contacter}
        disabled={enCours}
        className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 disabled:opacity-60 text-white py-3 rounded-full font-semibold transition-all text-base"
      >
        <Mail className="w-5 h-5" />
        {enCours ? "Ouverture…" : "Contacter le donneur"}
      </button>
      {erreur && <p className="text-sm text-red-600 mt-2 text-center">{erreur}</p>}
    </>
  )
}
