"use client"

import { useUser, useAuth } from "@clerk/nextjs"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { MapPin, Pencil, Trash2, Eye, Heart, RefreshCw, HandHeart, Mail } from "lucide-react"
import Link from "next/link"
import AnnonceCard from "../components/AnnonceCard"
import ServiceIndisponible from "../components/ServiceIndisponible"
import { vignette, type Annonce } from "../lib/annonces"

type Onglet = "annonces" | "favoris"

export default function Profil() {
  const { isLoaded } = useUser()
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()
  const [onglet, setOnglet] = useState<Onglet>("annonces")
  const [annonces, setAnnonces] = useState<Annonce[]>([])
  const [favoris, setFavoris] = useState<Annonce[]>([])
  const [loading, setLoading] = useState(true)
  const [indisponible, setIndisponible] = useState(false)
  // null tant que la préférence n'est pas connue : l'interrupteur reste masqué
  const [newsletter, setNewsletter] = useState<boolean | null>(null)
  const [erreurNewsletter, setErreurNewsletter] = useState("")
  const [renouvellement, setRenouvellement] = useState<number | null>(null)
  const [don, setDon] = useState<number | null>(null)
  // Heure de référence figée à l'ouverture de la page : le rendu reste stable
  const [maintenant] = useState(() => Date.now())

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace("/")
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const headers = { Authorization: `Bearer ${token}` }
        const [resAnnonces, resFavoris] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/me`, { headers }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/favoris`, { headers }),
        ])
        if (!resAnnonces.ok || !resFavoris.ok) throw new Error("serveur")
        const [dataAnnonces, dataFavoris] = await Promise.all([resAnnonces.json(), resFavoris.json()])
        if (actif) {
          setAnnonces(Array.isArray(dataAnnonces) ? dataAnnonces : [])
          setFavoris(Array.isArray(dataFavoris) ? dataFavoris : [])
        }
      } catch {
        // Sans ça, une panne affichait « aucune annonce » comme si le compte était vide
        if (actif) setIndisponible(true)
      } finally {
        if (actif) setLoading(false)
      }
    })()
    return () => { actif = false }
  }, [isLoaded, isSignedIn, getToken])

  // Préférence newsletter chargée à part : son échec ne doit pas bloquer le profil
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/newsletter/moi`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (actif && res.ok) setNewsletter((await res.json()).abonne)
      } catch {}
    })()
    return () => { actif = false }
  }, [isLoaded, isSignedIn, getToken])

  async function changerNewsletter(abonne: boolean) {
    setErreurNewsletter("")
    setNewsletter(abonne) // affichage immédiat, annulé si le serveur refuse
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/newsletter/moi`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ abonne }),
      })
      if (!res.ok) throw new Error()
    } catch {
      setNewsletter(!abonne)
      setErreurNewsletter("Le changement n'a pas pu être enregistré. Réessayez.")
    }
  }

  // Une annonce est supprimee automatiquement 30 jours apres sa (re)publication
  const DUREE_VIE_JOURS = 30
  const RENOUVELABLE_APRES_JOURS = 7

  function joursRestants(annonce: Annonce) {
    const age = (maintenant - new Date(annonce.created_at).getTime()) / 86400000
    return Math.max(0, Math.ceil(DUREE_VIE_JOURS - age))
  }

  function renouvelableDans(annonce: Annonce) {
    const age = Math.floor((maintenant - new Date(annonce.created_at).getTime()) / 86400000)
    return Math.max(0, RENOUVELABLE_APRES_JOURS - age)
  }

  async function renouvelerAnnonce(id: number) {
    setRenouvellement(id)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}/renouveler`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        alert(data.detail || "Le renouvellement a échoué. Réessayez.")
        return
      }
      const maj: Annonce = await res.json()
      setAnnonces((prev) => prev.map((a) => (a.id === id ? { ...a, created_at: maj.created_at } : a)))
    } finally {
      setRenouvellement(null)
    }
  }

  // Une annonce cloturee reste visible dans "Mes annonces" quelques jours avant d'etre retiree
  const DELAI_RETRAIT_DON_JOURS = 3

  function retraitDans(annonce: Annonce) {
    if (!annonce.donne_at) return 0
    const age = (maintenant - new Date(annonce.donne_at).getTime()) / 86400000
    return Math.max(0, Math.ceil(DELAI_RETRAIT_DON_JOURS - age))
  }

  async function declarerDon(id: number) {
    if (!confirm("Confirmer que l'objet a été donné ? Il sera comptabilisé dans les dons réalisés. Pour retirer l'annonce sans la compter comme un don, utilisez plutôt Supprimer.")) return
    setDon(id)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}/donne`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        alert(data.detail || "L'enregistrement a échoué. Réessayez.")
        return
      }
      const maj: Annonce = await res.json()
      setAnnonces((prev) => prev.map((a) => (a.id === id ? { ...a, donne_at: maj.donne_at } : a)))
    } finally {
      setDon(null)
    }
  }

  async function supprimerAnnonce(id: number) {
    if (!confirm("Supprimer cette annonce ?")) return
    const token = await getToken()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      alert("La suppression a échoué. Réessayez.")
      return
    }
    setAnnonces((prev) => prev.filter((a) => a.id !== id))
  }

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <main>
        <div className="max-w-4xl mx-auto px-6 py-12">
          <p className="text-gray-400">Chargement...</p>
        </div>
      </main>
    )
  }

  if (indisponible) {
    return (
      <main>
        <div className="max-w-4xl mx-auto px-6 py-12">
          <ServiceIndisponible />
        </div>
      </main>
    )
  }

  return (
    <main>
      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-black text-gray-900 mb-6">Mon profil</h1>

        <div className="flex items-center gap-2 mb-8">
          <button
            onClick={() => setOnglet("annonces")}
            className={`px-5 py-2.5 rounded-full text-sm font-semibold transition-colors ${
              onglet === "annonces" ? "bg-gray-900 text-white" : "bg-gray-50 text-gray-600 hover:bg-gray-100"
            }`}
          >
            Mes annonces ({annonces.length})
          </button>
          <button
            onClick={() => setOnglet("favoris")}
            className={`px-5 py-2.5 rounded-full text-sm font-semibold transition-colors ${
              onglet === "favoris" ? "bg-gray-900 text-white" : "bg-gray-50 text-gray-600 hover:bg-gray-100"
            }`}
          >
            Mes favoris ({favoris.length})
          </button>
        </div>

        {onglet === "annonces" && (
          annonces.length === 0 ? (
            <div className="text-center py-24">
              <p className="text-gray-400 mb-4">Vous n&apos;avez pas encore déposé d&apos;annonce.</p>
              <Link href="/annonces/new" className="bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white px-6 py-3 rounded-full font-semibold transition-all">
                Déposer un don
              </Link>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {annonces.map((annonce) => (
                <div
                  key={annonce.id}
                  className={`flex flex-wrap items-center gap-4 ring-1 rounded-3xl p-4 transition-all ${
                    annonce.donne_at
                      ? "bg-gray-50 ring-gray-100"
                      : "bg-white ring-gray-100 hover:ring-gray-200 hover:shadow-md"
                  }`}
                >
                  {annonce.images && annonce.images.length > 0 ? (
                    <img
                      src={vignette(annonce.images[0], 200)}
                      alt={annonce.titre}
                      className={`w-20 h-20 object-cover rounded-xl shrink-0 ${annonce.donne_at ? "grayscale opacity-60" : ""}`}
                    />
                  ) : (
                    <div className="w-20 h-20 bg-gray-100 rounded-xl shrink-0 flex items-center justify-center">
                      <span className="text-gray-400 text-xs">Pas de photo</span>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h2 className={`font-bold truncate ${annonce.donne_at ? "text-gray-400" : "text-gray-900"}`}>{annonce.titre}</h2>
                    <p className={`text-sm line-clamp-1 mt-0.5 ${annonce.donne_at ? "text-gray-400" : "text-gray-500"}`}>{annonce.description}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className="inline-block text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{annonce.categorie}</span>
                      {annonce.donne_at && (
                        <span className="inline-flex items-center gap-1 text-xs bg-green-50 text-green-700 font-medium px-2 py-0.5 rounded-full">
                          <HandHeart className="w-3 h-3" />
                          Objet donné
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="w-full flex flex-wrap items-center gap-x-3 gap-y-2">
                    <div className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
                      <MapPin className="w-3 h-3" />
                      {annonce.quartier}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
                      <Eye className="w-3 h-3" />
                      {annonce.vues ?? 0} vue{(annonce.vues ?? 0) > 1 ? "s" : ""}
                    </div>
                    <span className="text-xs text-gray-400 whitespace-nowrap">{new Date(annonce.created_at).toLocaleDateString("fr-FR")}</span>
                    {annonce.donne_at ? (
                      <span className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
                        <Trash2 className="w-3 h-3" />
                        Retirée dans {retraitDans(annonce)} j
                      </span>
                    ) : (
                      <span
                        className={`flex items-center gap-1 text-xs whitespace-nowrap ${
                          joursRestants(annonce) <= 5 ? "text-red-500 font-medium" : "text-gray-400"
                        }`}
                      >
                        <RefreshCw className="w-3 h-3" />
                        Expire dans {joursRestants(annonce)} j
                      </span>
                    )}
                    {/* Quatre actions ne tiennent pas sur une ligne de telephone :
                        grille 2x2 sur mobile, rangee unique alignee a droite ensuite. */}
                    <div className="w-full sm:w-auto sm:ml-auto grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
                      {!annonce.donne_at && (
                        <>
                          <button
                            onClick={() => renouvelerAnnonce(annonce.id)}
                            disabled={renouvellement === annonce.id || renouvelableDans(annonce) > 0}
                            title={
                              renouvelableDans(annonce) > 0
                                ? `Renouvelable dans ${renouvelableDans(annonce)} jour(s)`
                                : "Relancer 30 jours de visibilité"
                            }
                            className="flex items-center justify-center gap-1.5 border border-green-100 hover:border-green-400 text-green-600 disabled:text-gray-300 disabled:border-gray-100 disabled:cursor-not-allowed px-3 py-2 rounded-full text-sm font-medium transition-colors"
                          >
                            <RefreshCw className={`w-4 h-4 ${renouvellement === annonce.id ? "animate-spin" : ""}`} />
                            Renouveler
                          </button>
                          <Link href={`/mes-annonces/${annonce.id}/modifier`} className="flex items-center justify-center gap-1.5 border border-gray-200 hover:border-gray-400 text-gray-600 px-3 py-2 rounded-full text-sm font-medium transition-colors">
                            <Pencil className="w-4 h-4" />
                            Modifier
                          </Link>
                          <button
                            onClick={() => supprimerAnnonce(annonce.id)}
                            title="Retirer l'annonce sans la comptabiliser comme un don"
                            className="flex items-center justify-center gap-1.5 border border-red-100 hover:border-red-300 text-red-500 px-3 py-2 rounded-full text-sm font-medium transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                            Supprimer
                          </button>
                          <button
                            onClick={() => declarerDon(annonce.id)}
                            disabled={don === annonce.id}
                            title="L'objet a trouvé preneur : retirer l'annonce du site"
                            className="flex items-center justify-center gap-1.5 bg-green-600 hover:bg-green-500 disabled:bg-green-300 text-white px-3 py-2 rounded-full text-sm font-medium transition-colors"
                          >
                            <HandHeart className="w-4 h-4" />
                            Objet donné
                          </button>
                        </>
                      )}
                      {annonce.donne_at && (
                        <button
                          onClick={() => supprimerAnnonce(annonce.id)}
                          className="col-span-2 sm:col-span-1 flex items-center justify-center gap-1.5 border border-red-100 hover:border-red-300 text-red-500 px-3 py-2 rounded-full text-sm font-medium transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                          Supprimer
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {onglet === "favoris" && (
          favoris.length === 0 ? (
            <div className="text-center py-24">
              <Heart className="w-10 h-10 text-gray-200 mx-auto mb-4" />
              <p className="text-gray-400 mb-4">Aucun favori pour le moment. Touchez le cœur d&apos;une annonce pour la retrouver ici.</p>
              <Link href="/annonces" className="bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-full font-semibold transition-colors">
                Voir les annonces
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">
              {favoris.map((annonce) => (
                <AnnonceCard key={annonce.id} annonce={annonce} />
              ))}
            </div>
          )
        )}

        {newsletter !== null && (
          <section className="mt-12 pt-8 border-t border-gray-100">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Préférences</h2>
            <label className="flex items-start justify-between gap-4 bg-gray-50 rounded-2xl px-5 py-4 cursor-pointer">
              <span className="flex items-start gap-3">
                <Mail className="w-5 h-5 text-green-600 mt-0.5 shrink-0" aria-hidden="true" />
                <span>
                  <span className="block text-sm font-semibold text-gray-900">Lettre d&apos;information</span>
                  <span className="block text-sm text-gray-500">Recevoir chaque jeudi les derniers dons publiés à Gennevilliers.</span>
                </span>
              </span>
              <input
                type="checkbox"
                role="switch"
                checked={newsletter}
                onChange={(e) => changerNewsletter(e.target.checked)}
                className="sr-only peer"
              />
              <span
                aria-hidden="true"
                className="relative shrink-0 w-11 h-6 rounded-full bg-gray-300 peer-checked:bg-green-600 peer-focus-visible:ring-2 peer-focus-visible:ring-green-300 transition-colors after:absolute after:top-0.5 after:left-0.5 after:w-5 after:h-5 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-5"
              />
            </label>
            {erreurNewsletter && <p className="text-sm text-red-600 mt-2">{erreurNewsletter}</p>}
          </section>
        )}
      </div>
    </main>
  )
}
