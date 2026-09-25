"use client"

import { useState } from "react"
import { Copy, Check } from "lucide-react"

// Adresse de contact encodée (base64 de l'adresse écrite à l'envers) : elle n'apparaît en clair
// ni dans le HTML ni dans le code JavaScript servi, et n'est reconstituée qu'au clic d'un visiteur.
// Les robots qui aspirent les adresses e-mail ne la trouvent donc pas.
const ADRESSE_ENCODEE = "bW9jLmxpYW1nQGlkaGVtZHJhaGNpcA=="

function decoder(): string {
  return atob(ADRESSE_ENCODEE).split("").reverse().join("")
}

export default function AdresseProtegee() {
  const [adresse, setAdresse] = useState<string | null>(null)
  const [copiee, setCopiee] = useState(false)

  if (!adresse) {
    return (
      <button
        type="button"
        onClick={() => setAdresse(decoder())}
        className="text-green-600 hover:underline font-medium"
      >
        afficher l&apos;adresse e-mail
      </button>
    )
  }

  async function copier() {
    try {
      await navigator.clipboard.writeText(adresse!)
      setCopiee(true)
      setTimeout(() => setCopiee(false), 2000)
    } catch {
      // navigateur sans presse-papiers : l'adresse reste affichée et sélectionnable
    }
  }

  return (
    <span className="inline-flex items-center gap-2 flex-wrap">
      <a href={`mailto:${adresse}`} className="text-green-600 hover:underline">{adresse}</a>
      <button
        type="button"
        onClick={copier}
        aria-label="Copier l'adresse e-mail"
        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-900 border border-gray-200 rounded-full px-2 py-0.5"
      >
        {copiee ? <Check className="w-3 h-3" aria-hidden="true" /> : <Copy className="w-3 h-3" aria-hidden="true" />}
        {copiee ? "Copiée" : "Copier"}
      </button>
    </span>
  )
}
