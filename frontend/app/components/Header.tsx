"use client"

import { Suspense, useState } from "react"
import { Search, Plus } from "lucide-react"
import { useSearchParams, useRouter } from "next/navigation"
import Link from "next/link"
import { SignInButton, Show, UserButton } from "@clerk/nextjs"

const categories = [
  "Immobilier", "Vêtements", "Maison & Jardin",
  "Électronique", "Loisirs", "Sport", "Autres"
]

function SearchBar() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [query, setQuery] = useState(searchParams.get("recherche") ?? "")

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      const q = query.trim()
      if (q) router.push(`/annonces?recherche=${encodeURIComponent(q)}`)
      else router.push("/annonces")
    }
  }

  return (
    <div className="flex-1 relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" aria-hidden="true" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Rechercher un don à Gennevilliers..."
        aria-label="Rechercher un don"
        className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500 focus:bg-white transition-all focus:ring-2 focus:ring-green-100"
      />
    </div>
  )
}

function CategoryNav() {
  const searchParams = useSearchParams()
  const activeCat = searchParams.get("categorie")

  return (
    <ul className="flex items-center justify-center gap-0 overflow-x-hidden">
      <li className="relative group flex items-center shrink-0">
        <Link href="/annonces" className={`block px-5 py-4 text-lg transition-colors whitespace-nowrap font-medium ${!activeCat ? "text-gray-900" : "text-gray-500 hover:text-gray-900"}`}>
          Tout
        </Link>
        <span className="text-gray-200 text-xs" aria-hidden="true">·</span>
        <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-gray-900 transition-all duration-300 ease-out ${!activeCat ? "w-full" : "w-0 group-hover:w-full"}`} />
      </li>
      {categories.map((cat, index) => {
        const isActive = activeCat === cat
        return (
          <li key={cat} className="relative group flex items-center shrink-0">
            <Link href={`/annonces?categorie=${encodeURIComponent(cat)}`} className={`block px-5 py-4 text-lg transition-colors whitespace-nowrap font-medium ${isActive ? "text-gray-900" : "text-gray-500 hover:text-gray-900"}`}>
              {cat}
            </Link>
            {index < categories.length - 1 && (
              <span className="text-gray-200 text-xs" aria-hidden="true">·</span>
            )}
            <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-gray-900 transition-all duration-300 ease-out ${isActive ? "w-full" : "w-0 group-hover:w-full"}`} />
          </li>
        )
      })}
    </ul>
  )
}

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-center gap-6">
        <a href="/" aria-label="Accueil Gen Don" className="text-3xl font-black tracking-tight text-gray-900 shrink-0">
          Gen<span className="text-green-600">Don</span>
        </a>
        <Suspense fallback={<div className="flex-1 h-12 bg-gray-50 rounded-xl border border-gray-200" />}>
          <SearchBar />
        </Suspense>
        <div className="flex items-center gap-3 shrink-0">
          <Show when="signed-out">
            <SignInButton mode="modal">
              <button className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Se connecter
              </button>
            </SignInButton>
          </Show>
          <Show when="signed-in">
            <a href="/mes-annonces" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
              Mes annonces
            </a>
            <UserButton />
          </Show>
          <a href="/annonces/new" aria-label="Déposer un don" className="flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white px-6 py-3 rounded-xl text-base font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-green-300">
            <Plus className="w-5 h-5" aria-hidden="true" />
            Déposer un don
          </a>
        </div>
      </div>
      <div className="px-6">
        <Suspense fallback={<div className="h-12" />}>
          <CategoryNav />
        </Suspense>
      </div>
    </header>
  )
}