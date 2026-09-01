import { MapPin, Eye } from "lucide-react"
import Link from "next/link"
import { vignette, type Annonce } from "../lib/annonces"
import FavoriButton from "./FavoriButton"

export default function AnnonceCard({ annonce }: { annonce: Annonce }) {
  return (
    <Link href={`/annonces/${annonce.id}`} aria-label={`Voir l'annonce : ${annonce.titre}`} className="group block bg-white rounded-3xl overflow-hidden ring-1 ring-gray-100 hover:ring-gray-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer focus:outline-none focus:ring-2 focus:ring-green-300">
      <div className="relative overflow-hidden">
        {annonce.images && annonce.images.length > 0 ? (
          <img src={vignette(annonce.images[0])} alt={`Photo de ${annonce.titre}`} loading="lazy" className="w-full h-36 sm:h-52 object-cover group-hover:scale-105 transition-transform duration-300" />
        ) : (
          <div className="w-full h-36 sm:h-52 bg-gray-100 flex items-center justify-center">
            <span className="text-gray-400 text-sm">Pas de photo</span>
          </div>
        )}
        <span className="absolute top-2 left-2 sm:top-3 sm:left-3 max-w-[calc(100%-3.5rem)] truncate bg-white/90 backdrop-blur-sm text-gray-700 text-[11px] sm:text-xs font-semibold px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-full">
          {annonce.categorie}
        </span>
        <div className="absolute top-2 right-2 sm:top-3 sm:right-3">
          <FavoriButton annonceId={annonce.id} initial={annonce.est_favori ?? false} />
        </div>
        <span className="absolute bottom-2 left-2 sm:bottom-3 sm:left-3 flex items-center gap-1 bg-white/90 backdrop-blur-sm text-gray-700 text-[11px] sm:text-xs font-semibold px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-full">
          <Eye className="w-3 h-3" aria-hidden="true" />
          {annonce.vues ?? 0}
        </span>
      </div>
      <div className="p-2.5 sm:p-5 flex flex-col h-28 sm:h-40">
        <h2 className="text-gray-900 font-bold text-[13px] sm:text-base mb-0.5 sm:mb-1 leading-snug line-clamp-2 sm:line-clamp-1">{annonce.titre}</h2>
        <p className="text-gray-500 text-xs sm:text-sm mb-1.5 sm:mb-4 line-clamp-1 sm:line-clamp-2 leading-relaxed flex-1">{annonce.description}</p>
        <div className="flex items-center justify-between gap-2 mt-auto min-w-0">
          <div className="flex items-center gap-1 text-[11px] sm:text-xs text-gray-400 min-w-0">
            <MapPin className="w-3 h-3 shrink-0" aria-hidden="true" />
            <span className="truncate">{annonce.quartier}</span>
          </div>
          <span className="text-[11px] sm:text-xs text-gray-400 shrink-0">
            {new Date(annonce.created_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })}
          </span>
        </div>
      </div>
    </Link>
  )
}