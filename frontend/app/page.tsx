import { ArrowRight, MapPin, Heart, Zap, HandHeart, Package } from "lucide-react"
import Link from "next/link"
import AnnonceCard from "./components/AnnonceCard"
import { QUARTIERS, type Annonce } from "./lib/annonces"

// Les chiffres et les dernieres annonces doivent refleter l'etat reel du site :
// on rend a chaque visite plutot que de figer un instantane au moment du build,
// qui restait faux jusqu'a la regeneration suivante.
export const dynamic = "force-dynamic"

type Accueil = { annonces: Annonce[]; disponibles: number; dons: number }

async function getAccueil(): Promise<Accueil> {
  const base = process.env.NEXT_PUBLIC_API_URL
  let annonces: Annonce[] = []
  let disponibles = 0
  let dons = 0

  // Les deux sources sont interrogees separement : la panne de l'une
  // ne doit pas vider l'autre.
  const [resListe, resStats] = await Promise.allSettled([
    fetch(`${base}/annonces`, { cache: "no-store" }),
    fetch(`${base}/stats`, { cache: "no-store" }),
  ])

  if (resListe.status === "fulfilled" && resListe.value.ok) {
    const liste = await resListe.value.json()
    annonces = (liste.annonces ?? []).slice(0, 6)
    disponibles = liste.total ?? 0 // repli si /stats est indisponible
  }
  if (resStats.status === "fulfilled" && resStats.value.ok) {
    const stats = await resStats.value.json()
    disponibles = stats.annonces ?? disponibles
    dons = stats.dons_realises ?? 0
  }

  return { annonces, disponibles, dons }
}

export default async function Home() {
  const { annonces, disponibles, dons } = await getAccueil()

  const chiffres = [
    { valeur: disponibles, label: disponibles > 1 ? "objets à donner" : "objet à donner", Icon: Package },
    { valeur: dons, label: dons > 1 ? "dons réalisés" : "don réalisé", Icon: HandHeart },
    { valeur: QUARTIERS.length, label: "quartiers couverts", Icon: MapPin },
  ]

  return (
    <main>
      <section className="relative overflow-hidden py-14 sm:py-24 text-center">
        <div
          className="absolute inset-0 bg-cover bg-center scale-105"
          style={{ backgroundImage: "url('/gennevilliers_ciel.jpg')", filter: "blur(4px)" }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/20 to-black/40" />
        <div className="relative z-10 max-w-6xl mx-auto px-5 sm:px-6">
          <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm text-white text-xs font-semibold px-3 py-1.5 rounded-full mb-4 sm:mb-6 border border-white/30">
            <MapPin className="w-3 h-3" />
            Gennevilliers 92230
          </div>
          <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white mb-3 sm:mb-4 leading-[1.1] drop-shadow-lg">
            Donnez une seconde vie<br />
            <span className="text-green-400">près de chez vous.</span>
          </h1>
          <p className="text-base sm:text-lg text-white/90 max-w-xl mx-auto mb-7 sm:mb-10 leading-relaxed drop-shadow">
            La plateforme de dons entre habitants de Gennevilliers. Zéro argent, zéro transaction, juste du lien local.
          </p>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4">
            <Link href="/annonces" className="group flex items-center justify-center gap-2 bg-white text-gray-900 hover:bg-gray-100 px-7 py-3.5 rounded-full font-semibold transition-all hover:shadow-xl">
              Voir les dons
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link href="/annonces/new" className="flex items-center justify-center gap-2 border border-white/50 hover:border-white hover:bg-white/10 backdrop-blur-sm text-white px-7 py-3.5 rounded-full font-semibold transition-colors">
              Déposer un don
            </Link>
          </div>
        </div>
      </section>

      <section className="border-b border-gray-100 bg-gray-50/60">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 grid grid-cols-3 gap-2 sm:gap-6">
          {chiffres.map(({ valeur, label, Icon }) => (
            <div key={label} className="flex flex-col items-center text-center">
              <Icon className="w-4 h-4 sm:w-5 sm:h-5 text-green-600 mb-1.5" aria-hidden="true" />
              <p className="text-2xl sm:text-4xl font-black text-gray-900 leading-none">{valeur}</p>
              <p className="text-[11px] sm:text-sm text-gray-500 mt-1 leading-tight">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {annonces.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-14">
          <div className="flex items-end justify-between gap-3 mb-4 sm:mb-6">
            <div>
              <h2 className="text-xl sm:text-3xl font-black text-gray-900">Les derniers dons</h2>
              <p className="text-sm text-gray-500 mt-0.5">Fraîchement déposés par vos voisins</p>
            </div>
            <Link href="/annonces" className="group flex items-center gap-1.5 text-sm font-semibold text-green-600 hover:text-green-500 shrink-0 whitespace-nowrap">
              Voir tout
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-6">
            {annonces.map((annonce) => (
              <AnnonceCard key={annonce.id} annonce={annonce} />
            ))}
          </div>
        </section>
      )}

      <section className="border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-16 grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-6">
          <div className="flex sm:flex-col items-center sm:text-center text-left gap-4 sm:gap-0 bg-gray-50 rounded-3xl p-5 sm:p-8 hover:bg-green-50/60 sm:hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 bg-white shadow-sm rounded-2xl flex items-center justify-center shrink-0 sm:mx-auto sm:mb-4">
              <Heart className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 mb-1 sm:mb-2">100% gratuit</h3>
              <p className="text-sm text-gray-500 leading-relaxed">Pas de frais, pas de commission. Les objets trouvent une nouvelle vie gratuitement.</p>
            </div>
          </div>
          <div className="flex sm:flex-col items-center sm:text-center text-left gap-4 sm:gap-0 bg-gray-50 rounded-3xl p-5 sm:p-8 hover:bg-green-50/60 sm:hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 bg-white shadow-sm rounded-2xl flex items-center justify-center shrink-0 sm:mx-auto sm:mb-4">
              <MapPin className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 mb-1 sm:mb-2">100% local</h3>
              <p className="text-sm text-gray-500 leading-relaxed">Uniquement à Gennevilliers. Vos voisins, votre quartier, votre ville.</p>
            </div>
          </div>
          <div className="flex sm:flex-col items-center sm:text-center text-left gap-4 sm:gap-0 bg-gray-50 rounded-3xl p-5 sm:p-8 hover:bg-green-50/60 sm:hover:-translate-y-1 transition-all duration-300">
            <div className="w-12 h-12 bg-white shadow-sm rounded-2xl flex items-center justify-center shrink-0 sm:mx-auto sm:mb-4">
              <Zap className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 mb-1 sm:mb-2">Simple &amp; rapide</h3>
              <p className="text-sm text-gray-500 leading-relaxed">Déposez une annonce en 2 minutes. Contactez le donneur directement.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
