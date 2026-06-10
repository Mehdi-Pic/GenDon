"use client"

import { useState, useEffect, use } from "react"
import { useUser, useAuth } from "@clerk/nextjs"
import { CheckCircle, Upload, X } from "lucide-react"
import Link from "next/link"
import { CATEGORIES as categories, QUARTIERS as quartiers, vignette } from "../../../lib/annonces"
import { useImageUpload } from "../../../lib/useImageUpload"

export default function ModifierAnnonce({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { user } = useUser()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [titre, setTitre] = useState("")
  const [description, setDescription] = useState("")
  const [categorie, setCategorie] = useState("")
  const [quartier, setQuartier] = useState("")
  const [imagesExistantes, setImagesExistantes] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [chargement, setChargement] = useState(true)
  const [introuvable, setIntrouvable] = useState(false)
  const [erreurSubmit, setErreurSubmit] = useState("")

  const { images: nouvellesImages, setImages: setNouvellesImages, ajouterImages, uploadEnCours, slotsRestants, erreur: erreurUpload } = useImageUpload(imagesExistantes.length)
  const totalImages = imagesExistantes.length + nouvellesImages.length

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn) {
      window.location.replace("/")
      return
    }
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("introuvable")
        return res.json()
      })
      .then((data) => {
        setTitre(data.titre)
        setDescription(data.description)
        setCategorie(data.categorie)
        setQuartier(data.quartier)
        setImagesExistantes(data.images || [])
        setChargement(false)
      })
      .catch(() => {
        setIntrouvable(true)
        setChargement(false)
      })
  }, [id, isLoaded, isSignedIn])

  async function handleSubmit(e: React.SyntheticEvent) {
    e.preventDefault()
    setLoading(true)
    setErreurSubmit("")
    try {
      const token = await getToken()
      const urlsNouvellesImages = nouvellesImages.map((img) => img.url).filter(Boolean) as string[]
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          titre,
          description,
          categorie,
          quartier,
          pseudo: user?.username || user?.firstName || "Anonyme",
          images: [...imagesExistantes, ...urlsNouvellesImages],
          statut: "publiee",
        }),
      })
      if (!response.ok) throw new Error("Impossible d'enregistrer les modifications")
      setSubmitted(true)
    } catch (error) {
      setErreurSubmit(error instanceof Error ? error.message : "Une erreur est survenue")
    } finally {
      setLoading(false)
    }
  }

  if (!isLoaded || chargement) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-12">
          <p className="text-gray-400">Chargement...</p>
        </div>
      </main>
    )
  }

  if (!isSignedIn) return null

  if (introuvable) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Annonce introuvable</h1>
          <p className="text-gray-500 mb-8">Cette annonce n'existe plus ou a été supprimée.</p>
          <Link href="/mes-annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-xl font-semibold transition-colors">
            Retour à mes annonces
          </Link>
        </div>
      </main>
    )
  }

  if (submitted) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Annonce modifiée !</h1>
          <p className="text-gray-500 mb-8">Vos modifications ont bien été enregistrées.</p>
          <Link href="/mes-annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-xl font-semibold transition-colors">
            Retour à mes annonces
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main>
      <div className="max-w-2xl mx-auto px-6 py-12">
        <Link href="/mes-annonces" className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-900 text-sm mb-8 transition-colors font-medium">
          ← Retour à mes annonces
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mb-8">Modifier l'annonce</h1>

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Titre</label>
            <input type="text" value={titre} maxLength={100} onChange={(e) => setTitre(e.target.value)} className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:border-green-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
            <textarea value={description} maxLength={500} onChange={(e) => setDescription(e.target.value)} rows={4} className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:border-green-500 resize-none" />
            <p className="text-xs text-gray-400 mt-1">{description.length}/500 caractères</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Photos</label>
            <div className="flex flex-wrap items-center gap-3">
              {imagesExistantes.map((url, i) => (
                <div key={`existante-${i}`} className="relative w-20 h-20">
                  <img src={vignette(url, 200)} alt={`Photo ${i + 1}`} className="w-full h-full object-cover rounded-xl" />
                  <button
                    type="button"
                    onClick={() => setImagesExistantes((prev) => prev.filter((_, j) => j !== i))}
                    aria-label="Supprimer cette photo"
                    className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-400 text-white rounded-full w-6 h-6 flex items-center justify-center transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {nouvellesImages.map((imgState, i) => (
                <div key={`nouvelle-${i}`} className="relative w-20 h-20">
                  <img src={imgState.preview} alt="preview" className="w-full h-full object-cover rounded-xl" />
                  {imgState.url === null ? (
                    <div className="absolute inset-0 bg-black/50 rounded-xl flex flex-col items-center justify-center gap-1">
                      <span className="text-white text-xs font-medium">{imgState.progress}%</span>
                      <div className="w-12 bg-white/30 rounded-full h-1">
                        <div className="bg-white h-1 rounded-full transition-all duration-150" style={{ width: `${imgState.progress}%` }} />
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setNouvellesImages((prev) => prev.filter((_, j) => j !== i))}
                      aria-label="Supprimer cette photo"
                      className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-400 text-white rounded-full w-6 h-6 flex items-center justify-center transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}

              {slotsRestants > 0 && (
                <label className="h-20 w-20 bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-green-400 hover:bg-green-50 transition-colors">
                  <Upload className="w-5 h-5 text-gray-400" />
                  <span className="text-xs text-gray-400 mt-1">Ajouter</span>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={(e) => { const fichiers = Array.from(e.target.files ?? []); ajouterImages(fichiers) }}
                    className="hidden"
                  />
                </label>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              {totalImages}/5 photos · {slotsRestants > 0 ? `${slotsRestants} emplacement${slotsRestants > 1 ? "s" : ""} restant${slotsRestants > 1 ? "s" : ""}` : "Limite atteinte"}
            </p>
            {erreurUpload && <p className="text-red-500 text-xs mt-1">{erreurUpload}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Catégorie</label>
              <select value={categorie} onChange={(e) => setCategorie(e.target.value)} className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:border-green-500">
                {categories.map((cat) => (<option key={cat} value={cat}>{cat}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Quartier</label>
              <select value={quartier} onChange={(e) => setQuartier(e.target.value)} className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:border-green-500">
                {quartiers.map((q) => (<option key={q} value={q}>{q}</option>))}
              </select>
            </div>
          </div>

          {erreurSubmit && <p className="text-red-500 text-sm">{erreurSubmit}</p>}
          <button
            type="submit"
            disabled={loading || uploadEnCours}
            className="w-full bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-2xl transition-colors"
          >
            {loading ? "Enregistrement..." : uploadEnCours ? "Photos en cours de traitement..." : "Enregistrer les modifications"}
          </button>
        </form>
      </div>
    </main>
  )
}
