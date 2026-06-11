import { MapPin } from "lucide-react"
import Link from "next/link"
import { vignette, type Annonce } from "../lib/annonces"

export default function AnnonceCard({ annonce }: { annonce: Annonce }) {
  return (
    <Link href={`/annonces/${annonce.id}`} aria-label={`Voir l'annonce : ${annonce.titre}`} className="group block bg-white rounded-3xl overflow-hidden ring-1 ring-gray-100 hover:ring-gray-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer focus:outline-none focus:ring-2 focus:ring-green-300">
      <div className="relative overflow-hidden">
        {annonce.images && annonce.images.length > 0 ? (
          <img src={vignette(annonce.images[0])} alt={`Photo de ${annonce.titre}`} loading="lazy" className="w-full h-52 object-cover group-hover:scale-105 transition-transform duration-300" />
        ) : (
          <div className="w-full h-52 bg-gray-100 flex items-center justify-center">
            <span className="text-gray-400 text-sm">Pas de photo</span>
          </div>
        )}
        <span className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm text-gray-700 text-xs font-semibold px-2.5 py-1 rounded-full">
          {annonce.categorie}
        </span>
      </div>
      <div className="p-5 flex flex-col h-40">
        <h2 className="text-gray-900 font-bold text-base mb-1 leading-snug">{annonce.titre}</h2>
        <p className="text-gray-500 text-sm mb-4 line-clamp-2 leading-relaxed flex-1">{annonce.description}</p>
        <div className="flex items-center justify-between mt-auto">
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <MapPin className="w-3 h-3" aria-hidden="true" />
            {annonce.quartier}
          </div>
          <span className="text-xs text-gray-400">{new Date(annonce.created_at).toLocaleDateString("fr-FR")}</span>
        </div>
      </div>
    </Link>
  )
}