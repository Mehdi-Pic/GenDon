import type { Metadata } from "next"
import { notFound } from "next/navigation"
import Link from "next/link"
import { MapPin, User, ArrowLeft, Pencil, Eye } from "lucide-react"
import { auth } from "@clerk/nextjs/server"
import ImageCarousel from "../../components/ImageCarousel"
import ContactButton from "./ContactButton"
import ShareButton from "./ShareButton"
import FavoriButton from "../../components/FavoriButton"
import VueTracker from "./VueTracker"
import { vignette, type Annonce } from "../../lib/annonces"

async function getAnnonce(id: string, token?: string | null): Promise<Annonce | null> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!res.ok) return null
  return res.json()
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params
  const annonce = await getAnnonce(id)
  if (!annonce) return { title: "Annonce introuvable" }
  const description = annonce.description.slice(0, 160)
  return {
    title: annonce.titre,
    description,
    openGraph: {
      title: `${annonce.titre} · Don gratuit à Gennevilliers`,
      description,
      type: "article",
      images: annonce.images?.length ? [vignette(annonce.images[0], 1200)] : [],
    },
    twitter: {
      card: annonce.images?.length ? "summary_large_image" : "summary",
      title: annonce.titre,
      description,
    },
  }
}

export default async function AnnonceDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const { userId, getToken } = await auth()
  const token = userId ? await getToken() : null
  const annonce = await getAnnonce(id, token)

  if (!annonce) notFound()

  return (
    <main>
      <VueTracker annonceId={annonce.id} />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <Link href="/annonces" className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-900 text-sm mb-8 transition-colors font-medium focus:outline-none focus:ring-2 focus:ring-green-300 rounded-lg">
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Retour aux annonces
        </Link>
        <ImageCarousel images={annonce.images ?? []} />
        <div className="flex items-center gap-3 mb-4">
          <span className="bg-gray-100 text-gray-700 text-xs font-semibold px-3 py-1.5 rounded-full">{annonce.categorie}</span>
          <span className="text-xs text-gray-400">{new Date(annonce.created_at).toLocaleDateString("fr-FR")}</span>
          <div className="ml-auto flex items-center gap-2">
            {!annonce.est_proprietaire && (
              <FavoriButton annonceId={annonce.id} initial={annonce.est_favori ?? false} />
            )}
            <ShareButton titre={annonce.titre} />
          </div>
        </div>
        <h1 className="text-3xl font-black text-gray-900 mb-4 leading-tight">{annonce.titre}</h1>
        <p className="text-gray-600 leading-relaxed mb-8 text-base">{annonce.description}</p>
        <div className="flex flex-wrap items-center gap-3 mb-8">
          <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-full px-4 py-2">
            <MapPin className="w-4 h-4 text-green-600" aria-hidden="true" />
            {annonce.quartier}
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-full px-4 py-2">
            <User className="w-4 h-4 text-green-600" aria-hidden="true" />
            @{annonce.pseudo}
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-full px-4 py-2">
            <Eye className="w-4 h-4 text-green-600" aria-hidden="true" />
            {annonce.vues ?? 0} vue{(annonce.vues ?? 0) > 1 ? "s" : ""}
          </div>
        </div>
        {annonce.est_proprietaire ? (
          <div className="flex items-center justify-between bg-gray-50 rounded-2xl px-5 py-4">
            <p className="text-sm font-medium text-gray-600">C&apos;est votre annonce.</p>
            <Link href={`/mes-annonces/${annonce.id}/modifier`} className="flex items-center gap-1.5 bg-gray-900 hover:bg-gray-700 text-white px-4 py-2 rounded-full text-sm font-semibold transition-colors">
              <Pencil className="w-4 h-4" aria-hidden="true" />
              Modifier
            </Link>
          </div>
        ) : (
          <ContactButton annonceId={annonce.id} titreDon={annonce.titre} />
        )}
      </div>
    </main>
  )
}