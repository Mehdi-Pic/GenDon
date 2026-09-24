"use client"

import { CloudOff, RotateCw } from "lucide-react"

// Affiché quand le serveur ne répond pas : sans lui, une panne ressemblait à un site vide
// (« Aucun don disponible », « Annonce introuvable »).
export default function ServiceIndisponible({ compact = false }: { compact?: boolean }) {
  return (
    <div role="alert" className={`text-center ${compact ? "py-10" : "py-24"}`}>
      <CloudOff className="w-10 h-10 text-gray-300 mx-auto mb-4" aria-hidden="true" />
      <p className="text-lg font-bold text-gray-900">Service momentanément indisponible</p>
      <p className="text-gray-500 mt-1">Nos serveurs ne répondent pas. Réessayez dans quelques minutes.</p>
      <button
        onClick={() => window.location.reload()}
        className="inline-flex items-center gap-2 mt-6 bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors"
      >
        <RotateCw className="w-4 h-4" aria-hidden="true" />
        Réessayer
      </button>
    </div>
  )
}
