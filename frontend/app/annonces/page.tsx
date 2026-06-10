export const dynamic = "force-dynamic"
import { Suspense } from "react"
import Link from "next/link"
import AnnonceCard from "../components/AnnonceCard"
import FiltrePanel from "./FiltrePanel"
import { auth } from "@clerk/nextjs/server"
import type { Annonce } from "../lib/annonces"

type SearchParams = {
  categorie?: string
  recherche?: string
  tri?: string
  quartier?: string
  photos?: string
  periode?: string
  page?: string
}

type ResultatPaginé = {
  annonces: Annonce[]
  total: number
  pages: number
  page: number
}

async function getAnnonces(p: SearchParams, excludeUserId?: string | null): Promise<ResultatPaginé> {
  const base = process.env.NEXT_PUBLIC_API_URL
  const params = new URLSearchParams()
  if (p.categorie) params.set("categorie", p.categorie)
  if (p.recherche) params.set("recherche", p.recherche)
  if (p.tri && p.tri !== "recent") params.set("tri", p.tri)
  if (p.quartier) params.set("quartier", p.quartier)
  if (p.photos === "1") params.set("photos", "1")
  if (p.periode) params.set("periode", p.periode)
  if (p.page && p.page !== "1") params.set("page", p.page)
  if (excludeUserId) params.set("exclude_user_id", excludeUserId)
  const qs = params.toString()
  const url = `${base}/annonces${qs ? `?${qs}` : ""}`
  const res = await fetch(url, { cache: "no-store" })
  if (!res.ok) return { annonces: [], total: 0, pages: 1, page: 1 }
  return res.json()
}

function urlPage(sp: SearchParams, page: number): string {
  const params = new URLSearchParams()
  if (sp.categorie) params.set("categorie", sp.categorie)
  if (sp.recherche) params.set("recherche", sp.recherche)
  if (sp.tri && sp.tri !== "recent") params.set("tri", sp.tri)
  if (sp.quartier) params.set("quartier", sp.quartier)
  if (sp.photos === "1") params.set("photos", "1")
  if (sp.periode) params.set("periode", sp.periode)
  if (page > 1) params.set("page", String(page))
  const qs = params.toString()
  return `/annonces${qs ? `?${qs}` : ""}`
}

function plagesPages(page: number, pages: number): (number | "…")[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
  if (page <= 4) return [1, 2, 3, 4, 5, "…", pages]
  if (page >= pages - 3) return [1, "…", pages - 4, pages - 3, pages - 2, pages - 1, pages]
  return [1, "…", page - 1, page, page + 1, "…", pages]
}

export default async function Annonces({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams
  const { categorie, recherche } = sp
  const page = Number(sp.page ?? 1)
  const { userId } = await auth()
  const data = await getAnnonces(sp, userId)
  const { annonces, total, pages } = data

  return (
    <main>
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black text-gray-900">
              {recherche ? `Résultats pour "${recherche}"` : categorie ? categorie : "Les dons disponibles"}
            </h1>
            <p className="text-sm text-gray-500 mt-1">{total} objet{total > 1 ? "s" : ""} à donner à Gennevilliers</p>
          </div>
          <div className="flex items-center gap-3">
            {(categorie || recherche) && (
              <Link href="/annonces" className="text-sm text-gray-500 hover:text-gray-900 border border-gray-200 hover:border-gray-400 px-4 py-2 rounded-xl transition-colors">
                Voir tout
              </Link>
            )}
            <Suspense fallback={null}>
              <FiltrePanel />
            </Suspense>
          </div>
        </div>

        {annonces.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-gray-400 text-lg">Aucun don disponible{recherche ? ` pour "${recherche}"` : categorie ? ` dans la catégorie "${categorie}"` : ""} pour le moment.</p>
            <Link href="/annonces/new" className="inline-block mt-4 bg-green-600 hover:bg-green-500 text-white px-6 py-3 rounded-xl font-semibold transition-colors">
              Déposer le premier don
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {annonces.map((annonce) => (
                <AnnonceCard key={annonce.id} annonce={annonce} />
              ))}
            </div>

            {pages > 1 && (
              <div className="flex items-center justify-center gap-1 mt-12">
                <Link
                  href={page > 1 ? urlPage(sp, page - 1) : "#"}
                  aria-disabled={page === 1}
                  className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${page === 1 ? "border-gray-100 text-gray-300 pointer-events-none" : "border-gray-200 text-gray-600 hover:border-gray-400"}`}
                >
                  ←
                </Link>
                {plagesPages(page, pages).map((p, i) =>
                  p === "…" ? (
                    <span key={`ellipsis-${i}`} className="px-2 text-gray-400 text-sm">…</span>
                  ) : (
                    <Link
                      key={p}
                      href={urlPage(sp, p)}
                      className={`w-10 h-10 flex items-center justify-center rounded-xl text-sm font-medium border transition-colors ${p === page ? "bg-gray-900 text-white border-gray-900" : "border-gray-200 text-gray-600 hover:border-gray-400"}`}
                    >
                      {p}
                    </Link>
                  )
                )}
                <Link
                  href={page < pages ? urlPage(sp, page + 1) : "#"}
                  aria-disabled={page === pages}
                  className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${page === pages ? "border-gray-100 text-gray-300 pointer-events-none" : "border-gray-200 text-gray-600 hover:border-gray-400"}`}
                >
                  →
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}
