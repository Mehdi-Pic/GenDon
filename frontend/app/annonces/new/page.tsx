"use client"

import { useState } from "react"
import { Upload, X, CheckCircle } from "lucide-react"
import { useUser, useAuth, SignInButton } from "@clerk/nextjs"
import Link from "next/link"
import { CATEGORIES as categories, QUARTIERS as quartiers } from "../../lib/annonces"
import { useImageUpload } from "../../lib/useImageUpload"

type Errors = {
  titre?: string
  description?: string
  categorie?: string
  quartier?: string
}

export default function NewAnnonce() {
  const { user, isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const [titre, setTitre] = useState("")
  const [description, setDescription] = useState("")
  const [categorie, setCategorie] = useState("")
  const [quartier, setQuartier] = useState("")
  const { images: imageStates, setImages: setImageStates, ajouterImages, uploadEnCours, slotsRestants, erreur: erreurUpload } = useImageUpload()
  const [errors, setErrors] = useState<Errors>({})
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [erreurSubmit, setErreurSubmit] = useState("")

  if (!isLoaded) return null

  if (!isSignedIn) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Connectez-vous pour déposer un don</h1>
          <p className="text-gray-500 mb-8">La création d&apos;une annonce nécessite un compte — c&apos;est gratuit et rapide.</p>
          <SignInButton mode="modal">
            <button className="bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white px-8 py-3 rounded-full font-semibold transition-all">
              Se connecter
            </button>
          </SignInButton>
        </div>
      </main>
    )
  }

  function supprimerImage(index: number) {
    setImageStates((prev) => prev.filter((_, i) => i !== index))
  }

  function validate(): Errors {
    const e: Errors = {}
    if (!titre.trim()) e.titre = "Le titre est obligatoire"
    if (!description.trim()) e.description = "La description est obligatoire"
    if (!categorie) e.categorie = "Choisissez une catégorie"
    if (!quartier) e.quartier = "Choisissez un quartier"
    return e
  }

  async function handleSubmit(e: React.SyntheticEvent) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setLoading(true)
    setErreurSubmit("")
    try {
      const token = await getToken()
      const imageUrls = imageStates.map((img) => img.url).filter(Boolean) as string[]
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          titre,
          description,
          categorie,
          quartier,
          pseudo: user?.username || user?.firstName || "Anonyme",
          images: imageUrls,
          statut: "publiee",
        }),
      })
      if (!response.ok) throw new Error("La publication a échoué, réessayez")
      setSubmitted(true)
    } catch (error) {
      setErreurSubmit(error instanceof Error ? error.message : "Une erreur est survenue")
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <main>
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Don publié !</h1>
          <p className="text-gray-500 mb-8">Votre annonce est en ligne. Les habitants de Gennevilliers peuvent maintenant la voir.</p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-xl font-semibold transition-colors">
              Voir les annonces
            </Link>
            <button onClick={() => { setSubmitted(false); setTitre(""); setDescription(""); setCategorie(""); setQuartier(""); setImageStates([]) }} className="border border-gray-200 hover:border-gray-400 text-gray-700 px-6 py-3 rounded-xl font-semibold transition-colors">
              Déposer un autre don
            </button>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main>
      <div className="max-w-2xl mx-auto px-6 py-12">
        <Link href="/annonces" className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-900 text-sm mb-8 transition-colors font-medium">
          ← Retour aux annonces
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Déposer un don</h1>
        <p className="text-gray-500 text-sm mb-8">Les champs marqués <span className="text-red-500">*</span> sont obligatoires.</p>
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Titre <span className="text-red-500">*</span></label>
            <input type="text" value={titre} maxLength={100} onChange={(e) => { setTitre(e.target.value); setErrors((prev) => ({ ...prev, titre: undefined })) }} onBlur={() => { if (!titre.trim()) setErrors((prev) => ({ ...prev, titre: "Le titre est obligatoire" })) }} placeholder="Ex: Canapé 3 places" aria-invalid={!!errors.titre} className={`w-full bg-white border rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none transition-colors ${errors.titre ? "border-red-400 focus:border-red-400" : "border-gray-200 focus:border-green-500"}`} />
            {errors.titre && <p className="text-red-500 text-xs mt-1">{errors.titre}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Description <span className="text-red-500">*</span></label>
            <textarea value={description} maxLength={500} onChange={(e) => { setDescription(e.target.value); setErrors((prev) => ({ ...prev, description: undefined })) }} onBlur={() => { if (!description.trim()) setErrors((prev) => ({ ...prev, description: "La description est obligatoire" })) }} placeholder="Décrivez l'objet, son état, ses dimensions..." rows={4} aria-invalid={!!errors.description} className={`w-full bg-white border rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none transition-colors resize-none ${errors.description ? "border-red-400 focus:border-red-400" : "border-gray-200 focus:border-green-500"}`} />
            <p className="text-xs text-gray-400 mt-1">{description.length}/500 caractères</p>
            {errors.description && <p className="text-red-500 text-xs mt-1">{errors.description}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Photos</label>
            <div className="flex flex-wrap items-center gap-3">
              {imageStates.map((imgState, index) => (
                <div key={index} className="relative w-20 h-20">
                  <img src={imgState.preview} alt="preview" className="w-full h-full object-cover rounded-xl" />
                  {imgState.url === null && (
                    <div className="absolute inset-0 bg-black/50 rounded-xl flex flex-col items-center justify-center gap-1">
                      <span className="text-white text-xs font-medium">{imgState.progress}%</span>
                      <div className="w-12 bg-white/30 rounded-full h-1">
                        <div className="bg-white h-1 rounded-full transition-all duration-150" style={{ width: `${imgState.progress}%` }} />
                      </div>
                    </div>
                  )}
                  {imgState.url !== null && (
                    <button type="button" onClick={() => supprimerImage(index)} aria-label="Supprimer cette photo" className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-400 text-white rounded-full w-6 h-6 flex items-center justify-center transition-colors">
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
              {slotsRestants > 0 && (
                <label className="h-20 w-20 bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-green-400 hover:bg-green-50 transition-colors">
                  <Upload className="w-5 h-5 text-gray-400" />
                  <span className="text-xs text-gray-400 mt-1">Ajouter</span>
                  <input type="file" accept="image/*" multiple onChange={(e) => { const fichiers = Array.from(e.target.files ?? []); ajouterImages(fichiers) }} className="hidden" />
                </label>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-2">JPG, PNG acceptés. Max 5 photos.</p>
            {erreurUpload && <p className="text-red-500 text-xs mt-1">{erreurUpload}</p>}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Catégorie <span className="text-red-500">*</span></label>
              <select value={categorie} onChange={(e) => { setCategorie(e.target.value); setErrors((prev) => ({ ...prev, categorie: undefined })) }} aria-invalid={!!errors.categorie} className={`w-full bg-white border rounded-xl px-4 py-3 text-gray-900 focus:outline-none transition-colors ${errors.categorie ? "border-red-400" : "border-gray-200 focus:border-green-500"}`}>
                <option value="">Choisir...</option>
                {categories.map((cat) => (<option key={cat} value={cat}>{cat}</option>))}
              </select>
              {errors.categorie && <p className="text-red-500 text-xs mt-1">{errors.categorie}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Quartier <span className="text-red-500">*</span></label>
              <select value={quartier} onChange={(e) => { setQuartier(e.target.value); setErrors((prev) => ({ ...prev, quartier: undefined })) }} aria-invalid={!!errors.quartier} className={`w-full bg-white border rounded-xl px-4 py-3 text-gray-900 focus:outline-none transition-colors ${errors.quartier ? "border-red-400" : "border-gray-200 focus:border-green-500"}`}>
                <option value="">Choisir...</option>
                {quartiers.map((q) => (<option key={q} value={q}>{q}</option>))}
              </select>
              {errors.quartier && <p className="text-red-500 text-xs mt-1">{errors.quartier}</p>}
            </div>
          </div>
          {erreurSubmit && <p className="text-red-500 text-sm">{erreurSubmit}</p>}
          <button type="submit" disabled={loading || uploadEnCours} className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-2xl transition-colors text-base">
            {loading ? (
              <>
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Publication en cours...
              </>
            ) : uploadEnCours ? "Photos en cours de traitement..." : "Publier le don"}
          </button>
        </form>
      </div>
    </main>
  )
}