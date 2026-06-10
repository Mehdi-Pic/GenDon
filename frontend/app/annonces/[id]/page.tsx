import { notFound } from "next/navigation"
import Link from "next/link"
import { MapPin, User, ArrowLeft } from "lucide-react"
import ImageCarousel from "../../components/ImageCarousel"
import ContactButton from "./ContactButton"
import type { Annonce } from "../../lib/annonces"

async function getAnnonce(id: string): Promise<Annonce | null> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/annonces/${id}`, { cache: "no-store" })
  if (!res.ok) return null
  return res.json()
}

export default async function AnnonceDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const annonce = await getAnnonce(id)

  if (!annonce) notFound()

  return (
    <main>
      <div className="max-w-3xl mx-auto px-6 py-10">
        <Link href="/annonces" className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-900 text-sm mb-8 transition-colors font-medium focus:outline-none focus:ring-2 focus:ring-green-300 rounded-lg">
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Retour aux annonces
        </Link>
        <ImageCarousel images={annonce.images ?? []} />
        <div className="flex items-center gap-3 mb-4">
          <span className="bg-gray-100 text-gray-700 text-xs font-semibold px-3 py-1.5 rounded-full">{annonce.categorie}</span>
          <span className="text-xs text-gray-400">{new Date(annonce.created_at).toLocaleDateString("fr-FR")}</span>
        </div>
        <h1 className="text-3xl font-black text-gray-900 mb-4 leading-tight">{annonce.titre}</h1>
        <p className="text-gray-600 leading-relaxed mb-8 text-base">{annonce.description}</p>
        <div className="flex items-center gap-6 py-5 border-t border-b border-gray-100 mb-8">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <MapPin className="w-4 h-4 text-gray-400" aria-hidden="true" />
            {annonce.quartier}
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <User className="w-4 h-4 text-gray-400" aria-hidden="true" />
            @{annonce.pseudo}
          </div>
        </div>
        <ContactButton annonceId={annonce.id} titreDon={annonce.titre} />
      </div>
    </main>
  )
}