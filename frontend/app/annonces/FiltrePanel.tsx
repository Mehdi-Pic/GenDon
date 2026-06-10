"use client"

import { useState } from "react"
import { SlidersHorizontal } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
import { QUARTIERS as quartiers } from "../lib/annonces"

type Filtres = {
  tri: "recent" | "ancien"
  quartier: string
  photos: boolean
  periode: "" | "semaine" | "mois"
}

export default function FiltrePanel() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [ouvert, setOuvert] = useState(false)

  const [filtres, setFiltres] = useState<Filtres>({
    tri: (searchParams.get("tri") as "recent" | "ancien") || "recent",
    quartier: searchParams.get("quartier") || "",
    photos: searchParams.get("photos") === "1",
    periode: (searchParams.get("periode") as "" | "semaine" | "mois") || "",
  })

  const nbActifs = [
    filtres.tri !== "recent",
    !!filtres.quartier,
    filtres.photos,
    !!filtres.periode,
  ].filter(Boolean).length

  function appliquer() {
    const params = new URLSearchParams(searchParams.toString())
    if (filtres.tri === "recent") params.delete("tri")
    else params.set("tri", filtres.tri)
    if (filtres.quartier) params.set("quartier", filtres.quartier)
    else params.delete("quartier")
    if (filtres.photos) params.set("photos", "1")
    else params.delete("photos")
    if (filtres.periode) params.set("periode", filtres.periode)
    else params.delete("periode")
    params.delete("page")
    router.push(`/annonces?${params.toString()}`)
    setOuvert(false)
  }

  function reinitialiser() {
    const params = new URLSearchParams(searchParams.toString())
    params.delete("tri")
    params.delete("quartier")
    params.delete("photos")
    params.delete("periode")
    params.delete("page")
    setFiltres({ tri: "recent", quartier: "", photos: false, periode: "" })
    router.push(`/annonces?${params.toString()}`)
    setOuvert(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOuvert((v) => !v)}
        className={`flex items-center gap-2 border px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
          nbActifs > 0
            ? "border-green-500 bg-green-50 text-green-700"
            : "border-gray-200 text-gray-600 hover:border-gray-400"
        }`}
      >
        <SlidersHorizontal className="w-4 h-4" />
        Filtrer
        {nbActifs > 0 && (
          <span className="bg-green-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center leading-none">
            {nbActifs}
          </span>
        )}
      </button>

      {ouvert && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOuvert(false)} />
          <div className="absolute right-0 top-full mt-2 z-20 bg-white border border-gray-100 rounded-2xl shadow-xl p-5 w-72 flex flex-col gap-5">

            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Trier par</p>
              <div className="flex gap-2">
                {([
                  { val: "recent", label: "Plus récent" },
                  { val: "ancien", label: "Plus ancien" },
                ] as const).map(({ val, label }) => (
                  <button
                    key={val}
                    onClick={() => setFiltres((f) => ({ ...f, tri: val }))}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium border transition-colors ${
                      filtres.tri === val
                        ? "bg-gray-900 text-white border-gray-900"
                        : "border-gray-200 text-gray-600 hover:border-gray-400"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Quartier</p>
              <select
                value={filtres.quartier}
                onChange={(e) => setFiltres((f) => ({ ...f, quartier: e.target.value }))}
                className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:border-green-500 bg-white"
              >
                <option value="">Tous les quartiers</option>
                {quartiers.map((q) => (
                  <option key={q} value={q}>{q}</option>
                ))}
              </select>
            </div>

            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Déposé</p>
              <div className="flex gap-2">
                {([
                  { val: "", label: "Tout" },
                  { val: "semaine", label: "Cette semaine" },
                  { val: "mois", label: "Ce mois" },
                ] as const).map(({ val, label }) => (
                  <button
                    key={val}
                    onClick={() => setFiltres((f) => ({ ...f, periode: val }))}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium border transition-colors ${
                      filtres.periode === val
                        ? "bg-gray-900 text-white border-gray-900"
                        : "border-gray-200 text-gray-600 hover:border-gray-400"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Avec photos seulement</span>
              <button
                type="button"
                role="switch"
                aria-checked={filtres.photos}
                onClick={() => setFiltres((f) => ({ ...f, photos: !f.photos }))}
                className={`w-10 h-6 rounded-full transition-colors flex items-center px-1 ${
                  filtres.photos ? "bg-green-600" : "bg-gray-200"
                }`}
              >
                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${filtres.photos ? "translate-x-4" : "translate-x-0"}`} />
              </button>
            </div>

            <div className={`flex gap-2 pt-1 border-t border-gray-100 ${nbActifs > 0 ? "" : "justify-end"}`}>
              {nbActifs > 0 && (
                <button
                  onClick={reinitialiser}
                  className="flex-1 py-2.5 text-sm text-gray-500 hover:text-gray-900 transition-colors font-medium"
                >
                  Réinitialiser
                </button>
              )}
              <button
                onClick={appliquer}
                className="flex-1 bg-green-600 hover:bg-green-500 text-white py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Appliquer
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
