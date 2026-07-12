"use client"

import { Suspense, useState, useEffect } from "react"
import { Search, Plus, MessageCircle } from "lucide-react"
import { useSearchParams, useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import { SignInButton, Show, UserButton, useAuth } from "@clerk/nextjs"
import { CATEGORIES as categories } from "../lib/annonces"

function MessagesLink() {
  const { isSignedIn, getToken } = useAuth()
  const pathname = usePathname()
  const [nonLus, setNonLus] = useState(0)

  useEffect(() => {
    if (!isSignedIn) return
    let actif = true
    async function charger() {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/messages/non-lus`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (actif && res.ok) setNonLus(data.non_lus ?? 0)
      } catch {}
    }
    charger()
    const intervalle = setInterval(charger, 20000)
    return () => { actif = false; clearInterval(intervalle) }
  }, [isSignedIn, getToken, pathname])

  return (
    <Link href="/messages" aria-label="Messages" className="relative text-gray-600 hover:text-gray-900 transition-colors">
      <MessageCircle className="w-6 h-6" />
      {nonLus > 0 && (
        <span className="absolute -top-1.5 -right-1.5 bg-green-600 text-white text-[10px] font-bold rounded-full min-w-4 h-4 px-1 flex items-center justify-center">
          {nonLus > 9 ? "9+" : nonLus}
        </span>
      )}
    </Link>
  )
}

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
    <div className="relative w-full">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" aria-hidden="true" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Rechercher un don à Gennevilliers..."
        aria-label="Rechercher un don"
        className="w-full pl-11 pr-4 py-3 bg-gray-100 border border-transparent rounded-full text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-500 focus:bg-white transition-all focus:ring-2 focus:ring-green-100"
      />
    </div>
  )
}

function CategoryNav() {
  const searchParams = useSearchParams()
  const activeCat = searchParams.get("categorie")

  return (
    <ul className="flex items-center justify-start lg:justify-center gap-0 overflow-x-auto no-scrollbar">
      <li className="relative group flex items-center shrink-0">
        <Link href="/annonces" className={`block px-3 sm:px-5 py-3 sm:py-4 text-base sm:text-lg transition-colors whitespace-nowrap font-medium ${!activeCat ? "text-gray-900" : "text-gray-500 hover:text-gray-900"}`}>
          Tout
        </Link>
        <span className="text-gray-200 text-xs" aria-hidden="true">·</span>
        <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-gray-900 transition-all duration-300 ease-out ${!activeCat ? "w-full" : "w-0 group-hover:w-full"}`} />
      </li>
      {categories.map((cat, index) => {
        const isActive = activeCat === cat
        return (
          <li key={cat} className="relative group flex items-center shrink-0">
            <Link href={`/annonces?categorie=${encodeURIComponent(cat)}`} className={`block px-3 sm:px-5 py-3 sm:py-4 text-base sm:text-lg transition-colors whitespace-nowrap font-medium ${isActive ? "text-gray-900" : "text-gray-500 hover:text-gray-900"}`}>
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
    <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 sm:py-5 flex flex-wrap items-center gap-3 sm:gap-6">
        <Link href="/" aria-label="Accueil Gen Don" className="text-2xl sm:text-3xl font-black tracking-tight text-gray-900 shrink-0">
          Gen<span className="text-green-600">Don</span>
        </Link>
        <div className="order-3 w-full sm:order-0 sm:w-auto sm:flex-1">
          <Suspense fallback={<div className="h-12 bg-gray-100 rounded-full w-full" />}>
            <SearchBar />
          </Suspense>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 shrink-0 ml-auto">
          <Show when="signed-out">
            <SignInButton mode="modal">
              <button className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Se connecter
              </button>
            </SignInButton>
          </Show>
          <Show when="signed-in">
            <MessagesLink />
            <Link href="/profil" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
              Mon profil
            </Link>
            <UserButton />
          </Show>
          <Link href="/annonces/new" aria-label="Déposer un don" className="flex items-center gap-2 bg-green-600 hover:bg-green-500 hover:shadow-lg hover:shadow-green-200 text-white px-3.5 sm:px-6 py-3 rounded-full text-base font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-green-300">
            <Plus className="w-5 h-5" aria-hidden="true" />
            <span className="hidden sm:inline">Déposer un don</span>
          </Link>
        </div>
      </div>
      <div className="px-2 sm:px-6">
        <Suspense fallback={<div className="h-12" />}>
          <CategoryNav />
        </Suspense>
      </div>
    </header>
  )
}