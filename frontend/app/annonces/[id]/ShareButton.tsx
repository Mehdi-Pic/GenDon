"use client"

import { useState, useEffect } from "react"
import { Share2, Copy, Check, MessageCircle, MoreHorizontal, X } from "lucide-react"

export default function ShareButton({ titre }: { titre: string }) {
  const [ouvert, setOuvert] = useState(false)
  const [copie, setCopie] = useState(false)
  const [natifDispo, setNatifDispo] = useState(false)

  useEffect(() => {
    setNatifDispo(typeof navigator !== "undefined" && !!navigator.share)
  }, [])

  const texte = `${titre} — à donner gratuitement sur GenDon`

  async function copierLien() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopie(true)
      setTimeout(() => setCopie(false), 2000)
    } catch {
      // navigateur sans clipboard API : on ne casse rien
    }
  }

  function partagerWhatsApp() {
    window.open(`https://wa.me/?text=${encodeURIComponent(`${texte}\n${window.location.href}`)}`, "_blank", "noopener")
  }

  function partageNatif() {
    navigator.share({ title: "GenDon", text: texte, url: window.location.href }).catch(() => {})
  }

  function fermer() {
    setOuvert(false)
    setCopie(false)
  }

  return (
    <>
      <button
        onClick={() => setOuvert(true)}
        className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-full px-4 py-2 transition-colors"
      >
        <Share2 className="w-4 h-4 text-green-600" aria-hidden="true" />
        Partager
      </button>

      {ouvert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={fermer}>
          <div className="bg-white rounded-3xl shadow-2xl ring-1 ring-gray-100 w-full max-w-sm p-6 relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={fermer}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-700 transition-colors"
              aria-label="Fermer"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-lg font-bold text-gray-900 mb-4">Partager cette annonce</h2>

            <div className="flex flex-col gap-1">
              <button
                onClick={copierLien}
                className="flex items-center gap-3 w-full px-4 py-3 rounded-2xl hover:bg-gray-50 transition-colors text-left"
              >
                {copie ? <Check className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5 text-gray-500" />}
                <span className="text-sm font-medium text-gray-700">{copie ? "Lien copié !" : "Copier le lien"}</span>
              </button>

              <button
                onClick={partagerWhatsApp}
                className="flex items-center gap-3 w-full px-4 py-3 rounded-2xl hover:bg-gray-50 transition-colors text-left"
              >
                <MessageCircle className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-gray-700">WhatsApp</span>
              </button>

              {natifDispo && (
                <button
                  onClick={partageNatif}
                  className="flex items-center gap-3 w-full px-4 py-3 rounded-2xl hover:bg-gray-50 transition-colors text-left"
                >
                  <MoreHorizontal className="w-5 h-5 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700">Plus d&apos;options…</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
