import { ArrowLeft } from "lucide-react"

export default function NotFound() {
  return (
    <main>
      <div className="max-w-2xl mx-auto px-6 py-32 text-center">
        <p className="text-8xl font-black text-gray-100 mb-6 select-none">404</p>
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Cette page n'existe pas</h1>
        <p className="text-gray-500 mb-10">
          L'annonce que vous cherchez a peut-être été supprimée ou n'a jamais existé.
        </p>
        <a
          href="/annonces"
          className="inline-flex items-center gap-2 bg-gray-900 hover:bg-gray-700 text-white px-6 py-3 rounded-xl font-semibold transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Voir les annonces
        </a>
      </div>
    </main>
  )
}
