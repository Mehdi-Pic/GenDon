import { ArrowRight, MapPin, Heart, Zap } from "lucide-react"

export default function Home() {
  return (
    <main>
      <section className="relative overflow-hidden py-24 text-center">
        <div
          className="absolute inset-0 bg-cover bg-center scale-105"
          style={{ backgroundImage: "url('/gennevilliers_ciel.jpg')", filter: "blur(4px)" }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/20 to-black/40" />
        <div className="relative z-10 max-w-6xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm text-white text-xs font-semibold px-3 py-1.5 rounded-full mb-6 border border-white/30">
            <MapPin className="w-3 h-3" />
            Gennevilliers 92230
          </div>
          <h1 className="text-5xl font-black tracking-tight text-white mb-4 leading-tight drop-shadow-lg">
            Donnez une seconde vie<br />
            <span className="text-green-400">près de chez vous.</span>
          </h1>
          <p className="text-lg text-white/90 max-w-xl mx-auto mb-10 leading-relaxed drop-shadow">
            La plateforme de dons entre habitants de Gennevilliers. Zéro argent, zéro transaction — juste du lien local.
          </p>
          <div className="flex items-center justify-center gap-4">
            <a href="/annonces" className="flex items-center gap-2 bg-white text-gray-900 hover:bg-gray-100 px-6 py-3 rounded-xl font-semibold transition-colors">
              Voir les dons
              <ArrowRight className="w-4 h-4" />
            </a>
            <a href="/annonces/new" className="flex items-center gap-2 border border-white/50 hover:border-white hover:bg-white/10 text-white px-6 py-3 rounded-xl font-semibold transition-colors">
              Déposer un don
            </a>
          </div>
        </div>
      </section>

      <section className="border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 sm:grid-cols-3 gap-12">
          <div className="text-center">
            <div className="w-12 h-12 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Heart className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-bold text-gray-900 mb-2">100% gratuit</h3>
            <p className="text-sm text-gray-500 leading-relaxed">Pas de frais, pas de commission. Les objets trouvent une nouvelle vie gratuitement.</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <MapPin className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-bold text-gray-900 mb-2">100% local</h3>
            <p className="text-sm text-gray-500 leading-relaxed">Uniquement à Gennevilliers. Vos voisins, votre quartier, votre ville.</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Zap className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-bold text-gray-900 mb-2">Simple & rapide</h3>
            <p className="text-sm text-gray-500 leading-relaxed">Déposez une annonce en 2 minutes. Contactez le donneur directement.</p>
          </div>
        </div>
      </section>
    </main>
  )
}